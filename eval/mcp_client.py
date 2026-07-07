"""Thin async client for the ContextAI MCP server (contextai-mcp).

Speaks MCP over stdio to the installed `contextai-mcp` server exactly like an
LLM client (Cursor/Claude) would, so the tool outputs we measure are the real
ones an agent would receive. We launch it as `python -m contextai_mcp` because
that form is PATH-independent (the console script lands in ~/.local/bin, which
is not always on PATH).
"""

from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@asynccontextmanager
async def graph_session():
    env = dict(os.environ)
    env["PATH"] = "/home/ubuntu/.local/bin:" + env.get("PATH", "")
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "contextai_mcp"], env=env
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield ContextAIClient(session)


class ContextAIClient:
    def __init__(self, session: ClientSession):
        self._session = session

    async def _call(self, name: str, args: dict):
        result = await self._session.call_tool(name, args)
        text = result.content[0].text if result.content else "{}"
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"_raw": text}

    async def build_graph(self, project_root: str, output: str) -> dict:
        return await self._call(
            "build_graph", {"project_root": project_root, "output": output}
        )

    async def get_context(
        self,
        graph_path: str,
        node_id: str,
        depth: int = 1,
        direction: str = "both",
        include_code: bool = False,
    ) -> dict:
        return await self._call(
            "get_context",
            {
                "graph_path": graph_path,
                "node_id": node_id,
                "depth": depth,
                "direction": direction,
                "include_code": include_code,
            },
        )

    async def find_node(self, graph_path: str, query: str) -> dict:
        return await self._call("find_node", {"graph_path": graph_path, "query": query})
