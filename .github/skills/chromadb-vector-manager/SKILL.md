---
name: chromadb-vector-manager
description: Handles the creation of embedding scripts and interactions with the ChromaDB Client/Server Docker instance.
---
Execution Instructions:

    Agent Alignment:
        Planner: Provide plan/spec only. No code or scripts.
        Reviewer: Review scope, risks, and test evidence only.
        Executer: Code is allowed. Follow PLAN.md and README.
        Delivery Orchestrator: Route work only. Ask for missing context.

    Context: The system performs Semantic Search (Top-10 retrieval) relying solely on local vectorization, explicitly forbidding the use of generative LLMs (like OpenAI or Groq) for text synthesis.

    Libraries: Strictly utilize sentence-transformers (e.g., all-MiniLM-L6-v2) for generating vector embeddings locally, and the official chromadb Python client.

    Database Operations: For implementation tasks, initialize the ChromaDB client connecting to localhost:8000 and batch-upsert PySpark DataFrame outputs into Chroma collections.

    Retrieval Logic: For implementation tasks, implement a query function that takes a raw string input, encodes it using the identical sentence-transformers model, and returns a strictly structured JSON containing the Top 10 matching text_chunks and their similarity distances.