from __future__ import annotations

import asyncio
import os

import mcp.types as types
from mcp.server import Server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from scripts.upsert_chunks_to_chroma import (
    DEFAULT_CHROMA_HOST,
    DEFAULT_CHROMA_PORT,
    DEFAULT_COLLECTION_NAME,
    build_model,
    connect_client,
    create_collection,
    query_top_10,
)

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

server = Server("academic-papers-server")

CHROMA_CLIENT = connect_client(DEFAULT_CHROMA_HOST, DEFAULT_CHROMA_PORT)
CHROMA_COLLECTION = create_collection(CHROMA_CLIENT, DEFAULT_COLLECTION_NAME)
MODEL = build_model()


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def truncate_text(text: str, limit: int = 220) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def search_academic_papers(query_text: str) -> dict[str, object]:
    result = query_top_10(CHROMA_COLLECTION, MODEL, query_text)
    result["collection_name"] = DEFAULT_COLLECTION_NAME
    return result


def format_tool_content(result: dict[str, object]) -> list[types.TextContent]:
    collection_name = str(result.get("collection_name", DEFAULT_COLLECTION_NAME))
    blocks: list[types.TextContent] = [
        types.TextContent(
            type="text",
            text=(
                f"Query: {result['query']}\n"
                f"Collection: {collection_name}\n"
                f"Top-{result['top_k']} results: {len(result['results'])}"
            ),
        )
    ]

    if not result["results"]:
        blocks.append(types.TextContent(type="text", text="No matches found."))
        return blocks

    for item in result["results"]:
        metadata = item.get("metadata") or {}
        snippet = truncate_text(str(item.get("text_chunk", "")))
        lines = [
            f"{item['rank']}. {item['id']} | distance={float(item['distance']):.4f}",
            f"doc_id={metadata.get('doc_id', 'n/a')} | chunk_id={metadata.get('chunk_id', 'n/a')}",
        ]
        if metadata.get("source_path"):
            lines.append(f"source_path={metadata['source_path']}")
        if snippet:
            lines.append(f"snippet={snippet}")
        blocks.append(types.TextContent(type="text", text="\n".join(lines)))

    return blocks


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_academic_papers",
            description="Search the local academic papers collection and return the Top-10 matches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language question to search in the academic papers collection.",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, object] | None):
    if name != "search_academic_papers":
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True,
        )

    query_text = str((arguments or {}).get("query", "")).strip()
    if not query_text:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="Missing query argument.")],
            isError=True,
        )

    return format_tool_content(search_academic_papers(query_text))


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="academic-papers-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
            stateless=True,
        )


if __name__ == "__main__":
    asyncio.run(main())