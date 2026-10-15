# -*- coding: utf-8 -*-
"""Card-143 单元测试套件：工单系统历史堆积幽灵卡片大扫除与防风暴治理巡检闭环

核心断言规约：
1. 增强指纹脱敏：不同 PID、不同百分比与动态端口算出的 fingerprint 完全恒等；
2. 清洗归档引擎：--dry-run 零写盘，--execute 物理安全归档至 resolved/，业务工单 100% 保留；
3. 内存索引重建：清洗归档后，TaskCardManager 能够正确构建 O(1) 索引且不含已归档卡片。
"""

import json
import pytest
from pathlib import Path
from openviking.service.task_card_manager import TaskCardManager
from scripts.clean_ghost_task_cards import clean_task_cards


def test_compute_fingerprint_denoising():
    """验证 PID 脱敏与浮点百分比脱敏能够阻止卡片风暴。"""
    mgr = TaskCardManager.get_instance()

    module = "2080Ti-WSL/cpu"
    sym1 = "WSL2 CPU跑飞告警: ps (PID 2842579) 达 100.0%"
    sym2 = "WSL2 CPU跑飞告警: ps (PID 852679) 达 98.7%"
    sym3 = "WSL2 CPU跑飞告警: ps (PID 10398) 达 100.0%"

    fp1 = mgr._compute_fingerprint(module, sym1)
    fp2 = mgr._compute_fingerprint(module, sym2)
    fp3 = mgr._compute_fingerprint(module, sym3)

    # 3 个不同 PID 和百分比算出的指纹必须完全一致
    assert fp1 == fp2 == fp3
    assert len(fp1) == 12


def test_clean_ghost_task_cards_dry_run_and_execute(tmp_path: Path):
    """验证清洗引擎在沙箱环境下的 dry-run 与 execute 行为。"""
    inbox = tmp_path / "inbox"
    resolved = tmp_path / "resolved"
    inbox.mkdir(parents=True)
    resolved.mkdir(parents=True)

    # 1. 模拟生成 5 张 CPU 告警风暴卡片
    for i in range(5):
        card = {
            "card_id": f"Card-Issue-cpu-{i}",
            "fingerprint": f"fp_cpu_{i}",
            "title": f"WSL2 CPU跑飞告警: ps (PID {1000 + i})",
            "module": "2080Ti-WSL/cpu",
            "symptom": f"ps PID {1000 + i} 100%",
            "status": "pending",
            "created_at": 1000 + i,
        }
        (inbox / f"card_cpu_{i}.json").write_text(json.dumps(card), encoding="utf-8")

    # 2. 模拟生成 2 张测试用例卡片
    for i in range(2):
        card = {
            "card_id": f"Card-Issue-test-{i}",
            "fingerprint": f"fp_test_{i}",
            "title": f"connectivity verification test {i}",
            "module": "openviking",
            "symptom": "smoke test probe",
            "status": "pending",
            "created_at": 2000 + i,
        }
        (inbox / f"card_test_{i}.json").write_text(json.dumps(card), encoding="utf-8")

    # 3. 模拟生成 2 张真实业务工单
    for i in range(2):
        card = {
            "card_id": f"Card-Issue-biz-{i}",
            "fingerprint": f"fp_biz_{i}",
            "title": f"核心业务工单故障 {i}",
            "module": "gateway",
            "symptom": f"真实服务抛出 500 异常 {i}",
            "status": "pending",
            "created_at": 3000 + i,
        }
        (inbox / f"card_biz_{i}.json").write_text(json.dumps(card), encoding="utf-8")

    # 验证 Dry-run
    stats_dry = clean_task_cards(tmp_path, execute=False)
    assert stats_dry["total_inbox"] == 9
    assert stats_dry["cpu_alert_count"] == 5
    assert stats_dry["test_probe_count"] == 2
    assert stats_dry["legitimate_count"] == 2
    assert stats_dry["retained_inbox_count"] == 3
    # 物理文件未被改动
    assert len(list(inbox.glob("*.json"))) == 9
    assert len(list(resolved.glob("*.json"))) == 0

    # 验证 Execute
    stats_exec = clean_task_cards(tmp_path, execute=True)
    assert stats_exec["archived_count"] == 6  # 2 test + 4 duplicate cpu
    # inbox 中保留 2 张业务 + 1 张主 cpu = 3 张
    assert len(list(inbox.glob("*.json"))) == 3
    # resolved 中归档 6 张
    assert len(list(resolved.glob("*.json"))) == 6

    # 验证主 CPU 卡片聚合了 occurrence_count
    master_cpu = json.loads((inbox / "card_cpu_0.json").read_text(encoding="utf-8"))
    assert master_cpu["occurrence_count"] == 5
    assert "已去重合并" in master_cpu["title"]


def test_task_card_manager_rebuild_index(tmp_path: Path):
    """验证 TaskCardManager 构建索引时能够正确忽略已归档卡片。"""
    mgr = TaskCardManager(base_dir=tmp_path)
    inbox = tmp_path / "inbox"

    card1 = {"card_id": "c1", "fingerprint": "fp1", "status": "pending"}
    card2 = {"card_id": "c2", "fingerprint": "fp2", "status": "resolved"}
    (inbox / "c1.json").write_text(json.dumps(card1), encoding="utf-8")
    (inbox / "c2.json").write_text(json.dumps(card2), encoding="utf-8")

    mgr._build_inbox_index()
    assert "fp1" in mgr._pending_fingerprint_index
    assert "fp2" not in mgr._pending_fingerprint_index
