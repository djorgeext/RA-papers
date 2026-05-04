from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import chromadb
import pandas as pd
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PARQUET_PATH = PROJECT_ROOT / "data" / "processed_chunks"
DEFAULT_COLLECTION_NAME = "academic_papers_collection"
DEFAULT_CHROMA_HOST = "localhost"
DEFAULT_CHROMA_PORT = 8000
DEFAULT_BATCH_SIZE = 100
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_TOP_K = 10


def derive_doc_id(source_path: str) -> str:
    normalized_source = str(source_path).strip()
    parsed = urlparse(normalized_source)
    candidate_path = parsed.path if parsed.scheme else normalized_source
    stem = Path(candidate_path).stem
    digest = hashlib.sha1(normalized_source.encode("utf-8")).hexdigest()[:8]
    return f"{stem}-{digest}" if stem else digest


def load_staging_frame(parquet_path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(parquet_path).copy()

    if "text_chunk" not in frame.columns:
        raise ValueError("Expected a text_chunk column in the parquet data.")

    if "doc_id" not in frame.columns:
        if "source_path" not in frame.columns:
            raise ValueError("Expected source_path or doc_id in the parquet data.")
        if frame["source_path"].isna().any():
            raise ValueError("source_path contains missing values, so doc_id cannot be derived.")
        frame["doc_id"] = frame["source_path"].astype(str).map(derive_doc_id)
    else:
        frame["doc_id"] = frame["doc_id"].astype(str)

    if "chunk_id" not in frame.columns:
        frame["chunk_id"] = frame.groupby("doc_id", sort=False).cumcount().add(1)
    else:
        frame["chunk_id"] = pd.to_numeric(frame["chunk_id"], errors="raise").astype(int)

    frame["text_chunk"] = frame["text_chunk"].fillna("").astype(str)
    return frame.reset_index(drop=True)


def get_batches(frame: pd.DataFrame, batch_size: int) -> Iterator[pd.DataFrame]:
    for start in range(0, len(frame), batch_size):
        yield frame.iloc[start : start + batch_size]


def connect_client(host: str, port: int) -> chromadb.HttpClient:
    try:
        client = chromadb.HttpClient(host=host, port=port, ssl=False)
        client.heartbeat()
        return client
    except Exception as exc:
        print(f"Failed to connect to ChromaDB at {host}:{port}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def create_collection(client: chromadb.HttpClient, collection_name: str):
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def build_model() -> SentenceTransformer:
    return SentenceTransformer(DEFAULT_MODEL_NAME, device="cpu")


def encode_texts(model: SentenceTransformer, texts: list[str]) -> list[list[float]]:
    embeddings = model.encode(
        texts,
        batch_size=min(32, len(texts)) if texts else 1,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()


def upsert_batch(collection, model: SentenceTransformer, batch: pd.DataFrame) -> None:
    ids = [f"{doc_id}:{chunk_id}" for doc_id, chunk_id in zip(batch["doc_id"], batch["chunk_id"], strict=True)]
    embeddings = encode_texts(model, batch["text_chunk"].tolist())
    documents = batch["text_chunk"].tolist()
    metadatas = []

    for row in batch.itertuples(index=False):
        metadata = {
            "doc_id": str(row.doc_id),
            "chunk_id": int(row.chunk_id),
        }
        if hasattr(row, "source_path"):
            metadata["source_path"] = str(row.source_path)
        metadatas.append(metadata)

    collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)


def query_top_10(collection, model: SentenceTransformer, query_text: str) -> dict[str, object]:
    query_embedding = encode_texts(model, [query_text])
    result = collection.query(
        query_embeddings=query_embedding,
        n_results=DEFAULT_TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    results: list[dict[str, object]] = []
    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for rank, (item_id, document, metadata, distance) in enumerate(zip(ids, documents, metadatas, distances, strict=True), start=1):
        results.append(
            {
                "rank": rank,
                "id": item_id,
                "distance": float(distance),
                "text_chunk": document,
                "metadata": metadata,
            }
        )

    return {"query": query_text, "top_k": DEFAULT_TOP_K, "results": results}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch upsert processed chunks into local ChromaDB.")
    parser.add_argument("--parquet-path", type=Path, default=DEFAULT_PARQUET_PATH)
    parser.add_argument("--host", default=DEFAULT_CHROMA_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_CHROMA_PORT)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION_NAME)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--query", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.batch_size <= 0:
        raise ValueError("batch-size must be greater than zero.")

    frame = load_staging_frame(args.parquet_path)
    if args.limit is not None:
        frame = frame.head(args.limit).reset_index(drop=True)

    total_rows = len(frame)
    total_batches = (total_rows + args.batch_size - 1) // args.batch_size if total_rows else 0

    print(f"Loaded {total_rows} rows from {args.parquet_path}")
    print(f"Connecting to ChromaDB at {args.host}:{args.port}")

    client = connect_client(args.host, args.port)
    collection = create_collection(client, args.collection)
    model = build_model()

    print(f"Upserting into collection {args.collection} in batches of {args.batch_size}")

    for batch_index, batch in enumerate(get_batches(frame, args.batch_size), start=1):
        start_row = (batch_index - 1) * args.batch_size + 1
        end_row = start_row + len(batch) - 1
        print(f"Batch {batch_index}/{total_batches}: rows {start_row}-{end_row}")
        upsert_batch(collection, model, batch)
        print(f"Batch {batch_index}/{total_batches}: complete")

    print(f"Collection {args.collection} now contains {collection.count()} records")

    if args.query:
        print(json.dumps(query_top_10(collection, model, args.query), indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())