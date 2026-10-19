"""dify_mcp_server - Standalone FastMCP Control Plane for Dify Platform (v1.0.0).

Self-contained MCP tool provider for Dify. Supports decoupled loading via local config.json
or environment variables, with zero hardcoded credentials and zero source-path dependencies.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import httpx
from mcp.server.fastmcp import FastMCP

# 1. 尝试从本插件私有 config.json 加载安全凭据
_PLUGIN_DIR = Path(__file__).resolve().parent
_CONFIG_FILE = _PLUGIN_DIR / "config.json"
_LOCAL_CFG: Dict[str, str] = {}

if _CONFIG_FILE.exists():
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            _LOCAL_CFG = json.load(f)
    except Exception:
        pass

# 2. 凭据优先级：环境变量 > 本地私有 config.json > 空字符串
DEFAULT_API_URL = os.environ.get("DIFY_API_URL", _LOCAL_CFG.get("api_url", "http://127.0.0.1:13000"))
DEFAULT_ADMIN_KEY = os.environ.get("DIFY_ADMIN_KEY", _LOCAL_CFG.get("admin_key", ""))
DEFAULT_WORKSPACE_ID = os.environ.get("DIFY_WORKSPACE_ID", _LOCAL_CFG.get("workspace_id", ""))

mcp = FastMCP(
    "dify",
    instructions="Dify 官方全量编排与知识库控制面工具集。用于管理应用、运行工作流、导入导出 DSL 及管理知识库。",
)


def _get_client() -> httpx.Client:
    api_url = f"{DEFAULT_API_URL.rstrip('/')}/console/api"
    headers = {
        "Authorization": f"Bearer {DEFAULT_ADMIN_KEY}",
    }
    if DEFAULT_WORKSPACE_ID:
        headers["X-WORKSPACE-ID"] = DEFAULT_WORKSPACE_ID
    return httpx.Client(base_url=api_url, headers=headers, timeout=30.0)


@mcp.tool()
def dify_status() -> Dict[str, Any]:
    """Check Dify server connection status, workspace ID and entity summary."""
    with _get_client() as client:
        apps = client.get("/apps?page=1&limit=1").json()
        datasets = client.get("/datasets?page=1&limit=1").json()
        return {
            "server": DEFAULT_API_URL,
            "workspace_id": DEFAULT_WORKSPACE_ID or "default",
            "status": "connected",
            "auth_mode": "ADMIN_API_KEY (Secured)",
            "total_apps": apps.get("total", 0),
            "total_datasets": datasets.get("total", 0),
        }


@mcp.tool()
def dify_list_apps(page: int = 1, limit: int = 30) -> Dict[str, Any]:
    """List Dify applications and workflows in the current workspace."""
    with _get_client() as client:
        resp = client.get(f"/apps?page={page}&limit={limit}")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def dify_get_app(app_id: str) -> Dict[str, Any]:
    """Get detailed specification of a specific Dify application."""
    with _get_client() as client:
        resp = client.get(f"/apps/{app_id}")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def dify_export_dsl(app_id: str) -> str:
    """Export the complete YAML DSL configuration for an app or workflow."""
    with _get_client() as client:
        resp = client.get(f"/apps/{app_id}/export")
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            data = resp.json()
            return data.get("data", resp.text)
        return resp.text


@mcp.tool()
def dify_import_dsl(yaml_content: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Import a YAML DSL to create a new Dify app or overwrite an existing one."""
    payload: Dict[str, Any] = {"data": yaml_content}
    if name:
        payload["name"] = name
    with _get_client() as client:
        resp = client.post("/apps/import", json=payload)
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def dify_delete_app(app_id: str) -> Dict[str, Any]:
    """Delete a Dify application by UUID."""
    with _get_client() as client:
        resp = client.delete(f"/apps/{app_id}")
        resp.raise_for_status()
        return {"status": "success", "deleted_app_id": app_id}


@mcp.tool()
def dify_run_workflow(app_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a Dify workflow with given input parameters and return the execution trace."""
    with _get_client() as client:
        resp = client.post(f"/apps/{app_id}/workflows/run", json={"inputs": inputs})
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def dify_list_datasets(page: int = 1, limit: int = 30) -> Dict[str, Any]:
    """List knowledge bases (datasets) in the workspace."""
    with _get_client() as client:
        resp = client.get(f"/datasets?page={page}&limit={limit}")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def dify_create_dataset(name: str, description: str = "") -> Dict[str, Any]:
    """Create a new knowledge base (dataset)."""
    with _get_client() as client:
        payload = {
            "name": name,
            "description": description,
            "indexing_technique": "high_quality",
            "permission": "only_me",
        }
        resp = client.post("/datasets", json=payload)
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def dify_delete_dataset(dataset_id: str) -> Dict[str, Any]:
    """Delete a knowledge base by UUID."""
    with _get_client() as client:
        resp = client.delete(f"/datasets/{dataset_id}")
        resp.raise_for_status()
        return {"status": "success", "deleted_dataset_id": dataset_id}


@mcp.tool()
def dify_search_dataset(dataset_id: str, query: str) -> Dict[str, Any]:
    """Perform semantic hit-testing search in a knowledge base."""
    with _get_client() as client:
        resp = client.post(f"/datasets/{dataset_id}/hit-testing", json={"query": query})
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def dify_list_model_providers() -> Dict[str, Any]:
    """List all configured model providers in the current workspace."""
    with _get_client() as client:
        resp = client.get("/workspaces/current/model-providers")
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    mcp.run()
