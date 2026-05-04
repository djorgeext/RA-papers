from __future__ import annotations

import argparse
import sys
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.upsert_chunks_to_chroma import (  # noqa: E402
    DEFAULT_CHROMA_HOST,
    DEFAULT_CHROMA_PORT,
    DEFAULT_COLLECTION_NAME,
    build_model,
    connect_client,
    create_collection,
    query_top_10,
)

DEFAULT_QUERY = "¿Qué metodologías se usan para procesar series de tiempo?"


@lru_cache(maxsize=1)
def get_model():
    return build_model()


def search_academic_papers(
    query_text: str,
    host: str = DEFAULT_CHROMA_HOST,
    port: int = DEFAULT_CHROMA_PORT,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> dict[str, object]:
    client = connect_client(host, port)
    collection = create_collection(client, collection_name)
    result = query_top_10(collection, get_model(), query_text)
    result["collection_name"] = collection_name
    return result


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def truncate_text(text: str, limit: int = 220) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def format_result_summary(result: dict[str, object]) -> str:
    collection_name = str(result.get("collection_name", DEFAULT_COLLECTION_NAME))
    lines: list[str] = [
        f"Query: {result['query']}",
        f"Collection: {collection_name}",
        f"Top-{result['top_k']} results: {len(result['results'])}",
    ]

    if not result["results"]:
        lines.append("No matches found.")
        return "\n".join(lines)

    lines.append("")
    for item in result["results"]:
        metadata = item.get("metadata") or {}
        snippet = truncate_text(str(item.get("text_chunk", "")))
        lines.append(f"{item['rank']}. {item['id']} | distance={float(item['distance']):.4f}")
        lines.append(
            f"   doc_id={metadata.get('doc_id', 'n/a')} | chunk_id={metadata.get('chunk_id', 'n/a')}"
        )
        if metadata.get("source_path"):
            lines.append(f"   source_path={metadata['source_path']}")
        if snippet:
            lines.append(f"   snippet={snippet}")
        lines.append("")

    return "\n".join(lines).rstrip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query the local ChromaDB academic papers collection.")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Natural language query to send to ChromaDB.")
    parser.add_argument("--host", default=DEFAULT_CHROMA_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_CHROMA_PORT)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION_NAME)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    query_text = args.query.strip() or DEFAULT_QUERY
    result = search_academic_papers(query_text, args.host, args.port, args.collection)
    print(format_result_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())