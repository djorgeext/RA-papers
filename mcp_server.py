from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from scripts.query_chroma import format_result_summary, search_academic_papers as run_search_academic_papers

server = FastMCP("ra-papers")


@server.tool()
def search_academic_papers(query: str) -> str:
    """Search the local academic papers collection and return the Top-10 matches."""
    return format_result_summary(run_search_academic_papers(query))


if __name__ == "__main__":
    server.run(transport="stdio")