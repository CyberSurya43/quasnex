"""Knowledge gateway: web search + page fetch.

Lets a small, potentially stale open-weight model pull current documentation
and information instead of relying solely on what it was trained on. No API
key required — search uses DuckDuckGo's HTML endpoint.
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
from langchain_core.tools import tool

_FETCH_TIMEOUT = 15.0
_MAX_CHARS = 6000


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for current information (docs, releases, APIs, error messages).

    Use this when you need up-to-date facts you might not know, e.g. a library's
    current API, a recent framework version, or how to fix an unfamiliar error.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:
        return f"Error: web search failed: {exc}"

    if not results:
        return "No results found"

    lines = []
    for r in results:
        title = r.get("title", "")
        href = r.get("href", "")
        body = r.get("body", "")
        lines.append(f"- {title}\n  {href}\n  {body}")
    return "\n".join(lines)


@tool
def fetch_url(url: str) -> str:
    """Fetch a web page and return its main text content, stripped of HTML.

    Use this after web_search to read the actual content of a promising result.
    """
    try:
        response = httpx.get(
            url,
            timeout=_FETCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "ai-orchestrator/0.1 (+knowledge-gateway)"},
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return f"Error: could not fetch {url}: {exc}"

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = " ".join(soup.get_text(separator=" ").split())
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS] + "... [truncated]"
    return text or "(no readable text content)"


def build_tools():
    return [web_search, fetch_url]
