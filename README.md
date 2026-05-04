# RA-papers: Scalable Semantic Search Pipeline for Academic Papers

## Project Overview
This project implements a robust, scalable data pipeline and semantic search engine designed to ingest, process, and query collections of academic papers. Built with a "walk before you run" engineering philosophy, this current phase focuses entirely on **Information Retrieval (IR)** and data pipeline efficiency, acting as the foundational layer for a future Retrieval-Augmented Generation (RAG) system. 

By deliberately excluding generative Large Language Models (LLMs) in this stage, the architecture ensures that the underlying data processing, chunking strategies, and semantic vectorization are highly accurate and performant. The system takes a natural language query and strictly returns the Top-10 most semantically relevant text chunks from the ingested corpus.

## System Architecture & Tech Stack
The project is built emphasizing local processing, distributed data handling, and modern orchestration protocols:

*   **ETL & Distributed Processing:** **PySpark** handles the ingestion, cleaning, and chunking of raw PDF documents, ensuring the system can scale from a few papers to massive datasets.
*   **Local Embeddings:** Text chunks are vectorized using **HuggingFace's `sentence-transformers`** (e.g., `all-MiniLM-L6-v2`) directly within the Spark nodes, completely bypassing external API costs and rate limits.
*   **Vector Database:** **ChromaDB** (deployed in Client/Server mode via Docker) serves as the core storage and retrieval engine for the generated embeddings.
*   **Workflow Orchestration:** **n8n** is utilized as a visual backend to automate routing, handle HTTP triggers, and format the retrieved JSON responses without boilerplate API code.
*   **Agentic Integration:** Implements a **Model Context Protocol (MCP)** server, securely exposing the local vector database so that external MCP-compatible AI clients (like Cursor or Claude) can autonomously query the system's knowledge base.

## Current Scope (Phase 3)
- [x] Distributed document ingestion and text chunking.
- [x] Local embedding generation.
- [x] Top-K (Top-10) semantic similarity retrieval.
- [x] Phase 2: Local ChromaDB ingestion, normalized chunk staging, and Top-10 retrieval from the processed parquet chunks.
- [ ] Phase 3: Local query CLI, stdio MCP server, and client config for Top-10 retrieval from `academic_papers_collection`.