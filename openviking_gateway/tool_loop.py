"""Hidden Tool Loop Engine for OpenViking Gateway 2.0.

Provides autonomous on-premise execution for model-initiated Viking tool calls
without requiring tool configuration on the external client.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional
import httpx

from openviking_gateway.config import GatewayConfig

logger = logging.getLogger("openviking_gateway.tool_loop")

VIKING_HIDDEN_TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "openviking_read",
            "description": "Read file content, node overview or abstract from VikingFS URI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "uri": {
                        "type": "string",
                        "description": "VikingFS URI (e.g. viking://resources/docs/spec.md)",
                    }
                },
                "required": ["uri"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "openviking_find",
            "description": "Semantic search for memories, decisions, or code inside VikingFS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords or natural language search intention",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


def has_viking_tool_calls(choice: Dict[str, Any]) -> bool:
    """Check if model response choice contains openviking tool calls."""
    if not isinstance(choice, dict):
        return False
    msg = choice.get("message", {})
    tool_calls = msg.get("tool_calls") or []
    for tc in tool_calls:
        fn = tc.get("function", {})
        fn_name = fn.get("name", "")
        if fn_name.startswith("openviking_"):
            return True
    return False


class HiddenToolLoopExecutor:
    """Executes intercepted model tool calls and drives subsequent inference rounds."""

    def __init__(self, config: GatewayConfig, client: Optional[httpx.AsyncClient] = None):
        self.config = config
        self._client = client
        self._owns_client = client is None
        self.dispatch_tool: Optional[Callable[[str, Dict[str, Any]], Any]] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Retrieve or lazily initialize the shared HTTP client."""
        is_closed = getattr(self._client, "is_closed", False) is True
        if self._client is None or is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(5.0),
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            )
            self._owns_client = True
        return self._client

    async def aclose(self) -> None:
        """Close the internal HTTP client."""
        if self._owns_client and self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _default_dispatch_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Default dispatcher querying the local OpenViking core service."""
        client = await self.get_client()
        core_url = self.config.viking_core_url.rstrip("/")
        headers = {"content-type": "application/json"}
        if self.config.viking_api_key:
            headers["authorization"] = f"Bearer {self.config.viking_api_key}"

        try:
            if name == "openviking_read":
                uri = args.get("uri", "")
                resp = await client.post(
                    f"{core_url}/api/v1/resources/read",
                    json={"uri": uri},
                    headers=headers,
                )
                if resp.status_code == 200:
                    return resp.text
                return json.dumps({"error": f"Read failed with status {resp.status_code}", "uri": uri})

            if name == "openviking_find":
                query = args.get("query", "")
                resp = await client.post(
                    f"{core_url}/api/v1/search/find",
                    json={"query": query, "limit": 3},
                    headers=headers,
                )
                if resp.status_code == 200:
                    return resp.text
                return json.dumps({"error": f"Find failed with status {resp.status_code}", "query": query})

            return json.dumps({"error": f"Unsupported viking tool: {name}"})
        except Exception as exc:
            logger.error("Error executing hidden tool %s: %s", name, exc)
            return json.dumps({"error": str(exc), "tool": name})

    async def append_tool_execution(
        self,
        messages: List[Dict[str, Any]],
        assistant_message: Dict[str, Any],
        tool_call: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Append assistant tool_call and its execution output to message history."""
        new_messages = [dict(m) for m in messages]
        new_messages.append(assistant_message)

        fn = tool_call.get("function", {})
        fn_name = fn.get("name", "")
        raw_args = fn.get("arguments", "{}")
        try:
            parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except Exception:
            parsed_args = {}

        if self.dispatch_tool is not None:
            output = await self.dispatch_tool(fn_name, parsed_args)
        else:
            output = await self._default_dispatch_tool(fn_name, parsed_args)

        tool_msg = {
            "role": "tool",
            "tool_call_id": tool_call.get("id", "call_unknown"),
            "content": str(output),
        }
        new_messages.append(tool_msg)
        return new_messages

    async def run_loop_if_needed(
        self,
        client: httpx.AsyncClient,
        target_url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        first_resp_json: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Iteratively execute hidden tools until final text completion is reached."""
        if not self.config.enable_hidden_tool_loop:
            return first_resp_json

        current_resp = first_resp_json
        current_messages = list(payload.get("messages", []))
        iters = 0

        while iters < self.config.max_hidden_tool_iterations:
            choices = current_resp.get("choices", [])
            if not choices or not has_viking_tool_calls(choices[0]):
                break

            choice = choices[0]
            asst_msg = choice.get("message", {})
            tool_calls = asst_msg.get("tool_calls") or []

            # Execute all viking tool calls in this turn
            for tc in tool_calls:
                fn_name = tc.get("function", {}).get("name", "")
                if fn_name.startswith("openviking_"):
                    current_messages = await self.append_tool_execution(
                        current_messages, asst_msg, tc
                    )

            # Next iteration inference with updated messages
            iters += 1
            payload_copy = dict(payload)
            payload_copy["messages"] = current_messages
            payload_copy.pop("stream", None)  # Tool loops use non-stream intermediate turns

            logger.info("Executing hidden tool loop round %d...", iters)
            next_resp = await client.post(target_url, json=payload_copy, headers=headers)
            if next_resp.status_code >= 400:
                logger.warning("Upstream failed in tool loop round %d: %s", iters, next_resp.text)
                break
            current_resp = next_resp.json()

        return current_resp
