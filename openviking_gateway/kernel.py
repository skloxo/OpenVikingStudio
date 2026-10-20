"""Gateway Kernel for OpenViking Gateway 2.0.

Provides pre-flight user intent sniffing, asynchronous memory retrieval,
and fail-open contextual injection into System Prompt.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import httpx

from openviking_gateway.config import GatewayConfig
from openviking_gateway.protocols import auxiliary, clean_dsh_noise, is_dsh_noise

logger = logging.getLogger("openviking_gateway.kernel")


def extract_user_query(messages: List[Dict[str, Any]]) -> str:
    """Extract and clean text from the latest user message in history."""
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content")
            raw_text = ""
            if isinstance(content, str):
                raw_text = content.strip()
            elif isinstance(content, list):
                parts = []
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        parts.append(str(b.get("text", "")))
                raw_text = "\n".join(parts).strip()

            cleaned = clean_dsh_noise(raw_text)
            if cleaned and not is_dsh_noise(cleaned):
                return cleaned
    return ""


def inject_memory_context(
    messages: List[Dict[str, Any]], context_text: str
) -> List[Dict[str, Any]]:
    """Inject retrieved context into the System message in standard openviking tags."""
    if not context_text.strip():
        return messages

    tag_content = (
        f"\n\n<openviking_context>\n"
        f"<!-- Verified long-term memories retrieved from VikingFS -->\n"
        f"{context_text.strip()}\n"
        f"</openviking_context>\n"
    )

    new_messages: List[Dict[str, Any]] = [dict(m) for m in messages]

    # Search for an existing system message
    for i, m in enumerate(new_messages):
        if m.get("role") == "system":
            existing = m.get("content", "")
            new_messages[i] = {
                "role": "system",
                "content": f"{existing}{tag_content}".strip(),
            }
            return new_messages

    # Prepend new system message if none exists
    new_messages.insert(0, {"role": "system", "content": tag_content.strip()})
    return new_messages


class GatewayKernel:
    """Asynchronous intent detector and memory injection kernel."""

    def __init__(self, config: GatewayConfig, client: Optional[httpx.AsyncClient] = None):
        self.config = config
        self._client = client
        self._owns_client = client is None
        self._sessions_with_client_tools: Set[str] = set()
        self.last_classified_kind: str = "user"

    def register_client_tools(self, session_id: str) -> None:
        """Register that a session has actively sent client tools."""
        if session_id:
            self._sessions_with_client_tools.add(session_id)

    def classify_request(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """Classify request intent into ('user' | 'continuation' | 'auxiliary', should_recall).

        DSH or Claude Code sending side requests (e.g. title generation, page summary)
        in a session that has previously registered client tools must be treated as
        'auxiliary' to bypass memory recall and avoid generating ghost sessions.
        """
        if tools and session_id:
            self._sessions_with_client_tools.add(session_id)

        query = extract_user_query(messages)

        # 1. Matches explicit auxiliary patterns (e.g. 'Generate the session title from', 'summarize')
        if query and auxiliary(query):
            return "auxiliary", False

        # 2. Tool-less side requests inside a session that previously used client tools
        has_tools = bool(tools)
        has_replies = any(m.get("role") == "assistant" for m in messages)
        if (
            not has_tools
            and session_id
            and session_id in self._sessions_with_client_tools
            and not has_replies
        ):
            # A fresh side exchange without tools and without earlier assistant turns
            return "auxiliary", False

        # 3. Continuation turn (following previous assistant reply)
        if has_replies:
            return "continuation", False

        return "user", True

    async def get_client(self) -> httpx.AsyncClient:
        """Retrieve or lazily initialize the shared HTTP client."""
        is_closed = getattr(self._client, "is_closed", False) is True
        if self._client is None or is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(1.0),
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            )
            self._owns_client = True
        return self._client

    async def aclose(self) -> None:
        """Clean up HTTP client."""
        if self._owns_client and self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch_memories(self, query: str) -> List[Dict[str, Any]]:
        """Fetch relevant memories from local OpenViking core service with Fail-Open."""
        if not query or not self.config.enable_auto_memory_injection:
            return []

        endpoint = f"{self.config.viking_core_url.rstrip('/')}/api/v1/search/find"
        headers = {"content-type": "application/json"}
        if self.config.viking_api_key:
            headers["authorization"] = f"Bearer {self.config.viking_api_key}"

        payload = {
            "query": query,
            "target": "resources",
            "limit": self.config.memory_injection_top_k,
        }

        try:
            client = await self.get_client()
            resp = await client.post(endpoint, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results") or data.get("data") or []
                return results if isinstance(results, list) else []
            return []
        except Exception as exc:
            logger.debug("Fail-Open: Skipping memory injection due to core timeout/error: %s", exc)
            return []

    async def pre_flight_inject(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Pre-flight hook: sniff query, classify intent, and inject context if appropriate."""
        if not self.config.enable_auto_memory_injection:
            self.last_classified_kind = "user"
            return messages

        kind, should_recall = self.classify_request(messages, tools=tools, session_id=session_id)
        self.last_classified_kind = kind

        if not should_recall:
            logger.debug("Bypassing memory recall for %s request (session=%s)", kind, session_id)
            return messages

        query = extract_user_query(messages)
        if not query:
            return messages

        memories = await self.fetch_memories(query)
        if not memories:
            return messages

        context_lines: List[str] = []
        for mem in memories:
            if isinstance(mem, dict):
                text = mem.get("text") or mem.get("content") or mem.get("abstract") or ""
                uri = mem.get("uri") or mem.get("path") or ""
                if text:
                    prefix = f"[{uri}] " if uri else ""
                    context_lines.append(f"- {prefix}{text}")

        if not context_lines:
            return messages

        combined_context = "\n".join(context_lines)
        return inject_memory_context(messages, combined_context)
