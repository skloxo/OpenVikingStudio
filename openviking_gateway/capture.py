"""Asynchronous Session Capture Engine for OpenViking Gateway 2.0.

Silently captures and structures conversation turns into VikingFS session ledger.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from openviking_gateway.config import GatewayConfig
from openviking_gateway.kernel import extract_user_query

logger = logging.getLogger("openviking_gateway.capture")


def dehydrate_conversation_turn(
    messages: List[Dict[str, Any]], final_reply: str, model: str
) -> Dict[str, Any]:
    """Extract clean user prompt and assistant reply from turn history."""
    user_prompt = extract_user_query(messages)
    return {
        "timestamp": int(time.time()),
        "model": model,
        "user_prompt": user_prompt,
        "assistant_reply": final_reply,
        "turn_length": len(messages),
    }


class SessionCaptureEngine:
    """Asynchronously records conversation turns into local VikingFS session ledger."""

    def __init__(self, config: GatewayConfig, client: Optional[httpx.AsyncClient] = None):
        self.config = config
        self._client = client
        self._owns_client = client is None
        self._local_ledger_dir = Path.home() / ".openviking" / "data" / "sessions"

    async def get_client(self) -> httpx.AsyncClient:
        """Retrieve or lazily initialize the shared HTTP client."""
        is_closed = getattr(self._client, "is_closed", False) is True
        if self._client is None or is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(2.0),
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            )
            self._owns_client = True
        return self._client

    async def aclose(self) -> None:
        """Close the internal HTTP client."""
        if self._owns_client and self._client and not self._client.is_closed:
            await self._client.aclose()

    def _fallback_save_local(self, turn_data: Dict[str, Any]) -> None:
        """Fallback local persistence to prevent data loss when core is unavailable."""
        try:
            self._local_ledger_dir.mkdir(parents=True, exist_ok=True)
            ledger_file = self._local_ledger_dir / "gateway_sessions.jsonl"
            with open(ledger_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(turn_data, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.debug("Failed writing to local session ledger fallback: %s", exc)

    async def capture_turn(
        self,
        messages: List[Dict[str, Any]],
        assistant_reply: str,
        model: str,
    ) -> None:
        """Asynchronously dispatch conversation turn into VikingFS session store."""
        if not self.config.enable_session_capture:
            return

        turn_data = dehydrate_conversation_turn(messages, assistant_reply, model=model)
        if not turn_data["user_prompt"] or not turn_data["assistant_reply"]:
            return

        core_url = self.config.viking_core_url.rstrip("/")
        headers = {"content-type": "application/json"}
        if self.config.viking_api_key:
            headers["authorization"] = f"Bearer {self.config.viking_api_key}"

        try:
            client = await self.get_client()
            resp = await client.post(
                f"{core_url}/api/v1/sessions/capture",
                json=turn_data,
                headers=headers,
            )
            if resp.status_code not in (200, 201):
                self._fallback_save_local(turn_data)
        except Exception:
            self._fallback_save_local(turn_data)
