---
name: chromadb-vector-manager
description: Handles the creation of embedding scripts and interactions with the ChromaDB Client/Server Docker instance.
---
Execution Instructions:

    Context: The system performs Semantic Search (Top-10 retrieval) relying solely on local vectorization, explicitly forbidding the use of generative LLMs (like OpenAI or Groq) for text synthesis.

    Libraries: Strictly utilize sentence-transformers (e.g., all-MiniLM-L6-v2) for generating vector embeddings locally, and the official chromadb Python client.

    Database Operations: Provide code to initialize the ChromaDB client connecting to localhost:8000. Provide methods to batch-upsert the PySpark DataFrame outputs into Chroma collections.

    Retrieval Logic: Implement the query function to take a raw string input, encode it using the identical sentence-transformers model, and return a strictly structured JSON containing the Top 10 matching text_chunks and their similarity distances.