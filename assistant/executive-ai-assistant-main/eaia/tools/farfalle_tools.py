"""
Farfalle Research Tool — bridges Farfalle RAG into the enrichment pipeline.

Calls the Farfalle /chat SSE endpoint for deep web research when
standard tools (Tavily, Apollo, BrightData) return thin results.

Sprint 11: Farfalle → EAIA Bridge
"""

import os
import json
import logging
import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

FARFALLE_URL = os.getenv("FARFALLE_URL", "http://localhost:8000")


@tool
async def farfalle_deep_research(query: str) -> str:
    """Deep web research via Farfalle RAG pipeline (SearxNG + LLM synthesis).

    Use this when standard web_search returns thin results and you need
    deeper, multi-source research. Returns synthesized research findings.

    Args:
        query: Research question (e.g., "What is Company X's AUM and investment thesis?")
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{FARFALLE_URL}/chat",
                json={
                    "query": query,
                    "model": "gpt-4o-mini",
                    "history": [],
                },
                timeout=30.0,
            )

            if resp.status_code != 200:
                return f"Farfalle error: HTTP {resp.status_code}"

            # Parse SSE response — collect all text chunks
            text_chunks = []
            for line in resp.text.split("\n"):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if "text" in data:
                            text_chunks.append(data["text"])
                        elif "answer" in data:
                            text_chunks.append(data["answer"])
                    except json.JSONDecodeError:
                        text_chunks.append(line[6:])

            result = "".join(text_chunks)
            if not result.strip():
                return "Farfalle returned empty results for this query."

            logger.info(f"🔍 Farfalle research: {len(result)} chars for '{query[:50]}'")
            return result[:5000]

    except httpx.TimeoutException:
        return "Farfalle research timed out (30s). Try a more specific query."
    except httpx.ConnectError:
        return f"Cannot connect to Farfalle at {FARFALLE_URL}. Is it running?"
    except Exception as e:
        logger.error(f"Farfalle error: {e}")
        return f"Farfalle research failed: {str(e)}"
