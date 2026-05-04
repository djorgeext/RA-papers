from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
os.environ.setdefault("SPARK_LOCAL_HOSTNAME", "localhost")

import fitz
import pandas as pd
from pyspark.sql import SparkSession, functions as F, types as T
from pyspark.sql.functions import pandas_udf, udf


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "pdfs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed_chunks"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNK_STEP = CHUNK_SIZE - CHUNK_OVERLAP


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("ra_papers_pdf_ingestion")
        .master("local[*]")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.pyspark.python", sys.executable)
        .config("spark.pyspark.driver.python", sys.executable)
        .getOrCreate()
    )


@pandas_udf(T.StringType())
def extract_text_from_pdf(content: pd.Series) -> pd.Series:
    extracted_texts: List[str] = []

    for value in content:
        if value is None:
            extracted_texts.append("")
            continue

        try:
            with fitz.open(stream=bytes(value), filetype="pdf") as document:
                page_text = [page.get_text("text") for page in document]
            extracted_texts.append("\n".join(page_text))
        except Exception:
            extracted_texts.append("")

    return pd.Series(extracted_texts)


def sliding_window_chunks(text: str) -> List[str]:
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    chunks: List[str] = []
    start = 0

    while start < len(words):
        end = start + CHUNK_SIZE
        chunk_words = words[start:end]
        if not chunk_words:
            break

        chunks.append(" ".join(chunk_words))

        if end >= len(words):
            break

        start += CHUNK_STEP

    return chunks


chunk_udf = udf(sliding_window_chunks, T.ArrayType(T.StringType()))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    try:
        pdfs_df = (
            spark.read.format("binaryFile")
            .option("pathGlobFilter", "*.pdf")
            .load(str(INPUT_DIR))
            .select("path", "content")
        )

        processed_df = (
            pdfs_df.withColumn("raw_text", extract_text_from_pdf(F.col("content")))
            .withColumn("clean_text", F.trim(F.regexp_replace(F.col("raw_text"), r"\s+", " ")))
            .withColumn("chunks", chunk_udf(F.col("clean_text")))
        )

        final_df = processed_df.select(
            F.col("path").alias("source_path"),
            F.explode(F.col("chunks")).alias("text_chunk"),
        )

        final_df.write.mode("overwrite").parquet(str(OUTPUT_DIR))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()