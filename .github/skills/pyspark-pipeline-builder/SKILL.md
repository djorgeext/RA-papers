---
name: pyspark-pipeline-builder
description: Generate, optimize, and debug PySpark jobs for local PDF ingestion, text extraction, and text chunking without external APIs.
---

# PySpark Pipeline Builder Skill

Use this skill when the task involves building, refactoring, optimizing, or debugging PySpark jobs for local document ingestion, PDF text extraction, and chunking pipelines.

## Core requirements

- Process PDF documents locally.
- Do not use external APIs, remote OCR services, or cloud document services.
- Prefer native PySpark and Spark SQL constructs for transformations, joins, filtering, grouping, and chunk assembly.
- Use Python PDF libraries such as PyMuPDF (`fitz`) or `pdfplumber` only inside Spark UDFs, mapPartitions logic, or other Spark-compatible worker-side code when extraction is required.
- Do not introduce LangChain, LlamaIndex, or other heavy orchestration abstractions in the PySpark phase.
- Always include robust error handling for corrupted, unreadable, encrypted, or partially damaged PDF files.

## Implementation guidance

### 1) PDF ingestion
- Read document inputs from local filesystem paths or from an existing Spark DataFrame.
- Preserve a stable `document_id` for every file.
- If a PDF cannot be parsed, catch the exception and continue processing other files.
- Record failure details in metadata when possible instead of failing the entire job.

### 2) Text extraction
- Extract text on Spark worker nodes, not on the driver, when processing at scale.
- Prefer a worker-safe function that:
  - opens one PDF at a time,
  - extracts page text,
  - returns structured output,
  - closes file handles immediately.
- If page-level extraction fails, return an empty string for that page or document and attach error metadata.

### 3) Chunking
- Implement sliding-window chunking in PySpark.
- Prefer native Spark SQL / DataFrame transformations for chunk generation once text has been extracted.
- Chunking must be deterministic and reproducible.
- Support configurable chunk size and overlap.
- Preserve reading order when building chunks.

### 4) Output schema
The final DataFrame must include at least these columns:

- `document_id`
- `chunk_id`
- `text_chunk`
- `metadata`

Optional helpful fields:
- `page_number`
- `source_path`
- `chunk_start`
- `chunk_end`
- `error_message`

### 5) Metadata
Include useful metadata such as:
- source file path
- page count
- extraction method
- chunk size
- chunk overlap
- parsing errors
- corruption or encryption flags

### 6) Performance rules
- Keep logic distributed and stateless where possible.
- Avoid collecting large text payloads to the driver.
- Use Spark-native operations for filtering, ordering, repartitioning, and output writing.
- Minimize Python-side work inside UDFs.
- When a UDF is necessary, keep it focused on text extraction only.

## Preferred coding pattern

When generating code, prefer this structure:

1. Load local PDF paths into a Spark DataFrame.
2. Extract text per document or per page on workers.
3. Normalize text in Spark.
4. Build sliding-window chunks.
5. Emit a final DataFrame with the required schema.
6. Write results to Parquet, Delta, or another Spark-friendly format.

## Error handling expectations

- Catch and handle:
  - `FileNotFoundError`
  - corrupted PDF parse errors
  - encryption/password issues
  - empty-document cases
  - worker-side runtime exceptions
- Do not stop the pipeline for a single broken file unless explicitly requested.
- Emit structured metadata that makes failures easy to debug.

## Code generation rules

- Use PySpark code first.
- Use Python PDF libraries only where Spark needs them for extraction.
- Keep the solution local-first.
- Do not add unnecessary dependencies.
- Do not add LangChain or LlamaIndex unless explicitly requested for a later non-PySpark stage.
- Prefer clear, production-oriented code with explicit schemas and readable transformations.

## Debugging rules

When debugging a PySpark pipeline for this use case:
- inspect schema and nullability first,
- verify file paths and permissions,
- isolate extraction errors from chunking errors,
- validate output columns and row counts,
- test a corrupted PDF path separately,
- confirm partitioning and executor-side behavior.

## Output expectations

When asked to produce code, the answer should be ready to run or very close to it, and should include:
- imports
- Spark session assumptions if needed
- explicit schema or output columns
- extraction logic
- chunking logic
- error handling
- a small usage example when helpful