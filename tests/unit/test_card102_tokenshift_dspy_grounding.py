# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit Tests for Card-102 TokenShift & DSPy Grounding and Physical Persistence."""

from __future__ import annotations

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from openviking.server.app import create_app
from openviking.service.tokenshift_apply import (
    ApplyTokenShiftRequest,
    TokenShiftApplyService,
)
from openviking.service.dspy_apply import (
    ApplyDSPyRequest,
    DSPyApplyService,
)


@pytest.fixture
def temp_project(tmp_path: Path):
    """Create a temporary project structure with code files and prompt templates."""
    proj_dir = tmp_path / "test_project"
    proj_dir.mkdir(parents=True)

    # Code files
    code_dir = proj_dir / "src" / "sample"
    code_dir.mkdir(parents=True)
    py_file = code_dir / "demo.py"
    py_file.write_text("def hello():\n    # greeting\n    return 'world'\n", encoding="utf-8")

    ts_file = code_dir / "widget.tsx"
    ts_file.write_text("export const Widget = () => <div>Test</div>;\n", encoding="utf-8")

    # Prompt templates
    prompts_dir = proj_dir / "openviking" / "prompts" / "templates" / "test_cat"
    prompts_dir.mkdir(parents=True)
    tpl_file = prompts_dir / "greet.yaml"
    tpl_file.write_text(
        """metadata:
  id: "test_cat.greet"
  name: "Greeting Template"
  description: "Greet users politely"
  version: "1.0.0"
  category: "test_cat"
variables:
  - name: "username"
    type: "string"
template: |
  Hello, {{ username }}! Welcome aboard.
""",
        encoding="utf-8",
    )

    backup_dir = tmp_path / "quarantine"
    backup_dir.mkdir(parents=True)

    return {
        "root": proj_dir,
        "backup": backup_dir,
        "py_file": py_file,
        "ts_file": ts_file,
        "tpl_file": tpl_file,
        "prompts_dir": proj_dir / "openviking" / "prompts" / "templates",
        "compiled_dir": proj_dir / "openviking" / "prompts" / "compiled",
    }


def test_tokenshift_list_and_read_files(temp_project):
    service = TokenShiftApplyService(
        project_root=temp_project["root"],
        backup_root=temp_project["backup"] / "tokenshift",
    )

    # List all code files
    files = service.list_code_files()
    assert len(files) >= 2
    paths = [f.rel_path for f in files]
    assert "src/sample/demo.py" in paths
    assert "src/sample/widget.tsx" in paths

    # Filter by language
    py_only = service.list_code_files(language="python")
    assert any(f.rel_path == "src/sample/demo.py" for f in py_only)
    assert not any(f.rel_path == "src/sample/widget.tsx" for f in py_only)

    # Read file
    content_data = service.read_code_file("src/sample/demo.py")
    assert content_data["language"] == "python"
    assert "def hello():" in content_data["content"]

    # Security check: path traversal
    with pytest.raises(ValueError, match="Path traversal detected"):
        service.read_code_file("../../../etc/passwd")


def test_tokenshift_apply_skeleton_and_inplace(temp_project):
    service = TokenShiftApplyService(
        project_root=temp_project["root"],
        backup_root=temp_project["backup"] / "tokenshift",
    )

    compressed_py = "def hello():\n    return 'world'\n"

    # 1. Skeleton file mode
    req_skel = ApplyTokenShiftRequest(
        rel_path="src/sample/demo.py",
        compressed_code=compressed_py,
        mode="skeleton_file",
    )
    res_skel = service.apply_compression(req_skel)
    assert res_skel.success is True
    assert res_skel.syntax_valid is True
    assert "demo.skeleton.py" in res_skel.target_path
    assert Path(res_skel.snapshot_path).exists()

    skel_file = temp_project["root"] / "src" / "sample" / "demo.skeleton.py"
    assert skel_file.exists()
    assert skel_file.read_text(encoding="utf-8") == compressed_py

    # 2. In-place overwrite mode
    req_inplace = ApplyTokenShiftRequest(
        rel_path="src/sample/demo.py",
        compressed_code="def hello(): pass\n",
        mode="in_place",
    )
    res_inplace = service.apply_compression(req_inplace)
    assert res_inplace.success is True
    assert res_inplace.target_path == "src/sample/demo.py"
    assert (temp_project["root"] / "src" / "sample" / "demo.py").read_text() == "def hello(): pass\n"

    # 3. AST Syntax error rejection gate
    req_bad_syntax = ApplyTokenShiftRequest(
        rel_path="src/sample/demo.py",
        compressed_code="def hello(:\n",
        mode="in_place",
    )
    with pytest.raises(ValueError, match="AST Syntax Gate Rejected"):
        service.apply_compression(req_bad_syntax)


def test_dspy_list_and_read_templates(temp_project):
    service = DSPyApplyService(
        templates_dir=temp_project["prompts_dir"],
        compiled_dir=temp_project["compiled_dir"],
        backup_root=temp_project["backup"] / "dspy",
    )

    templates = service.list_prompt_templates()
    assert len(templates) >= 1
    assert templates[0].id == "test_cat.greet"
    assert templates[0].category == "test_cat"

    # Read template
    data = service.read_prompt_template("test_cat/greet.yaml")
    assert data["name"] == "Greeting Template"
    assert "Hello, {{ username }}!" in data["template"]

    # Security check: path traversal
    with pytest.raises(ValueError, match="Path traversal detected"):
        service.read_prompt_template("../../../etc/shadow")


def test_dspy_apply_compiled_and_inplace(temp_project):
    service = DSPyApplyService(
        templates_dir=temp_project["prompts_dir"],
        compiled_dir=temp_project["compiled_dir"],
        backup_root=temp_project["backup"] / "dspy",
    )

    compiled_text = "[MIPO STRICT SCHEMA]\nINPUT: username (string)\nOUTPUT: greeting (string)\nRULE: zero hallucination"

    # 1. Compiled file mode
    req_compiled = ApplyDSPyRequest(
        rel_path="test_cat/greet.yaml",
        compiled_prompt=compiled_text,
        signature_name="GreetSignature",
        mode="compiled_file",
    )
    res_compiled = service.apply_compiled_prompt(req_compiled)
    assert res_compiled.success is True
    assert "greet.compiled.yaml" in res_compiled.target_path
    assert Path(res_compiled.snapshot_path).exists()
    assert Path(res_compiled.target_path).exists()

    # 2. In-place overwrite mode
    req_inplace = ApplyDSPyRequest(
        rel_path="test_cat/greet.yaml",
        compiled_prompt="Updated template in place",
        mode="in_place",
    )
    res_inplace = service.apply_compiled_prompt(req_inplace)
    assert res_inplace.success is True
    updated_yaml = temp_project["tpl_file"].read_text(encoding="utf-8")
    assert "Updated template in place" in updated_yaml


def test_card102_api_endpoints_live():
    """Verify live API routes registered with FastAPI."""
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, Role, UserIdentifier

    app = create_app()
    dummy_ctx = RequestContext(
        user=UserIdentifier(user_id="test_user", account_id="default"),
        role=Role.ADMIN,
    )
    app.dependency_overrides[get_request_context] = lambda: dummy_ctx

    client = TestClient(app)

    # 1. TokenShift files catalog
    res_ts = client.get("/api/v1/tokenshift/files?limit=10")
    assert res_ts.status_code == 200
    files = res_ts.json()
    assert isinstance(files, list)
    assert len(files) > 0
    assert "rel_path" in files[0]

    # 2. TokenShift read file
    first_path = files[0]["rel_path"]
    res_read = client.get(f"/api/v1/tokenshift/file?path={first_path}")
    assert res_read.status_code == 200
    assert "content" in res_read.json()

    # 3. DSPy templates catalog
    res_dspy = client.get("/api/v1/dspy/templates?limit=10")
    assert res_dspy.status_code == 200
    templates = res_dspy.json()
    assert isinstance(templates, list)
    assert len(templates) > 0
    assert "id" in templates[0]

    # 4. DSPy read template
    first_tpl_path = templates[0]["rel_path"]
    res_tpl_read = client.get(f"/api/v1/dspy/template?path={first_tpl_path}")
    assert res_tpl_read.status_code == 200
    assert "template" in res_tpl_read.json()

