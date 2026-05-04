---
name: mcp-server-architect
description: Scaffolds and configures a Model Context Protocol (MCP) server to expose the local ChromaDB to external AI clients.
---

Execution Instructions:

    Agent Alignment:
        Planner: Provide plan/spec only. No code or scripts.
        Reviewer: Review scope, risks, and test evidence only.
        Executer: Code is allowed. Follow PLAN.md and README.
        Delivery Orchestrator: Route work only. Ask for missing context.

    Context: The vector database must be accessible to MCP-compatible clients (like Cursor or Claude Desktop) to allow them to natively query the academic papers.

    Libraries: Utilize the official @modelcontextprotocol/sdk (if using TypeScript/Node.js) or the official Python MCP SDK.

    Implementation: For implementation tasks, define a standard MCP Tool (e.g., search_academic_papers) that accepts a query parameter and wire its execution directly to the chromadb_vector_manager retrieval logic.

    Constraints: Ensure the server is stateless and handles connection lifecycle events properly via standard input/output (stdio) streams as required by the MCP specification. Output a comprehensive mcp.json configuration file showing how to attach this custom server to an external client.