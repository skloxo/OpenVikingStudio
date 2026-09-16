import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ensure mcp-openviking is on sys.path
mcp_path = str(Path(__file__).resolve().parent.parent.parent / "mcp-openviking")
if mcp_path not in sys.path:
    sys.path.insert(0, mcp_path)

from tools.cpa import is_teacher_model, register_cpa_tools
from tools.observability import HARNESS_METRICS


def test_is_teacher_model_classification():
    # Teacher models
    assert is_teacher_model("claude-opus-5") is True
    assert is_teacher_model("claude-3-opus-20240229") is True
    assert is_teacher_model("gpt-5.6") is True
    assert is_teacher_model("gpt-4o") is True
    assert is_teacher_model("chatgpt-4o-latest") is True
    assert is_teacher_model("o1-preview") is True
    assert is_teacher_model("o3-mini") is True

    # Worker models (free to use, bulk fanout)
    assert is_teacher_model("qwen3.8-flash-next") is False
    assert is_teacher_model("glm-5.3-flash") is False
    assert is_teacher_model("mimo-v2.5-pro") is False
    assert is_teacher_model("deepseek-v4-flash") is False
    assert is_teacher_model("doubao-pro-32k") is False


def test_cpa_consult_teacher_guard_interception():
    mock_mcp = MagicMock()
    mock_tool = lambda *args, **kwargs: (lambda f: f)
    tools = register_cpa_tools(mock_mcp, mock_tool)
    consult = tools["openviking_cpa_consult"]

    # 1. Adversarial mode with claude-opus-5 -> Intercepted
    res = consult(topic="测试对抗挑刺", mode="adversarial", model="claude-opus-5")
    assert "🚫 【CPA 教师模型守卫拦截 (Teacher Model Guard)】" in res
    assert "严禁使用 GPT/Claude 教师模型" in res

    # 2. Worker mode with gpt-5.6 -> Intercepted
    res = consult(topic="测试数据脱水", mode="worker", model="gpt-5.6")
    assert "🚫 【CPA 教师模型守卫拦截 (Teacher Model Guard)】" in res

    # 3. Worker model with adversarial -> Permitted
    with patch("tools.cpa._call_cpa_raw", return_value="红队找茬完成，发现3处隐患") as mock_raw:
        res = consult(topic="测试代码安全性", mode="adversarial", model="qwen3.8-flash-next")
        assert "红队找茬完成" in res
        assert mock_raw.called


def test_cpa_fanout_teacher_guard_interception():
    mock_mcp = MagicMock()
    mock_tool = lambda *args, **kwargs: (lambda f: f)
    tools = register_cpa_tools(mock_mcp, mock_tool)
    fanout = tools["openviking_cpa_fanout"]

    # 1. Fanout with teacher model -> Intercepted
    res = fanout(
        prompt="批量检查死锁",
        items=["item1.py", "item2.py"],
        worker_model="claude-opus-5"
    )
    assert "🚫 【CPA 教师模型守卫拦截 (Teacher Model Guard)】" in res
    assert "工兵多路并发严禁混入任何昂贵教师模型" in res

    # 2. Fanout with gpt-4o -> Intercepted
    res = fanout(
        prompt="批量提纯",
        items=["file1.txt"],
        worker_model="gpt-4o"
    )
    assert "🚫 【CPA 教师模型守卫拦截 (Teacher Model Guard)】" in res

    # 3. Fanout with worker model -> Permitted
    with patch("tools.cpa._call_cpa_raw", return_value="脱水完毕: 核心逻辑正常") as mock_raw:
        res = fanout(
            prompt="批量提纯",
            items=["item_test_1"],
            worker_model="qwen3.8-flash-next"
        )
        assert "CPA 工兵并发脱水报告" in res
        assert "item_test_1" in res
