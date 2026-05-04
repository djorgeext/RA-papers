# PLAN

Phase 2 scope: keep the pipeline local, containerize only what is needed for ChromaDB at localhost:8000, and define the vectorization and insertion path without adding LLM generation.

- [ ] Normalize the existing Phase 1 parquet rows from source_path and text_chunk into a Phase 2 staging view with doc_id, chunk_id, and text_chunk by deriving doc_id from source_path and assigning a deterministic per-document chunk sequence; keep the Phase 1 parquet output unchanged. DoD: reading data/processed_chunks and projecting the staging view yields stable doc_id values for the same source_path, contiguous chunk_id values within each document, and the same total row count as the source parquet.
- [ ] Add a minimal Docker setup for the ChromaDB client/server workflow only, exposing the ChromaDB server on localhost:8000 and avoiding extra services that are not required for batch upsert. DoD: the container starts cleanly, the server is reachable on localhost:8000, and a host-side client can create or list the target collection.
- [ ] Define the local SentenceTransformer embedding step for the normalized chunks so vectorization happens entirely offline and can be run in small batches. DoD: a test run on a small sample produces embeddings with the expected dimensionality, completes without external network calls, and preserves the row-to-vector alignment.
- [ ] Define the ChromaDB batch upsert step against localhost:8000 using the normalized ids, embeddings, and minimal metadata needed for retrieval. DoD: inserting a sample batch increases the target collection count by the expected amount, the stored metadata matches the staged input, and rerunning the same batch does not create duplicate drift for the same ids.
- [ ] Add one end-to-end smoke check for the Phase 2 path from parquet read to ChromaDB insertion and Top-10 retrieval. DoD: the smoke check runs against localhost:8000 on the current local dataset or a small sample, returns 10 ranked results from the collection, and completes with no LLM step.

## Phase 3

- [ ] Phase 3 is in progress: add a local-only query CLI, a stdio MCP server, and a client config that all reuse the Phase 2 ChromaDB plus SentenceTransformer search path. DoD: both the CLI and MCP tool return the same Top-10 semantic results from `academic_papers_collection` with no LLM generation.