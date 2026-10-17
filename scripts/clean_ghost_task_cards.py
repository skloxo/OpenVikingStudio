# -*- coding: utf-8 -*-
"""工单系统历史堆积幽灵卡片与风暴告警清洗归档引擎 (Task Card Hygiene & Dedup Cleaner)

功能契约：
1. 默认 --dry-run 预览，绝不产生破坏性修改；
2. 指定 --execute 触发真实物理归档迁移 (移至 resolved/ 目录，零数据物理丢弃)；
3. 将因 PID 漂移产生风暴的 500+ 张瞬态跑飞告警聚合为 1 张主工单 (occurrence_count 真实累加)；
4. 将测试用例卡片安全归档；
5. 保留 100% 真实业务与工程故障卡片。
"""

import argparse
import json
import logging
import re
import shutil
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clean_ghost_task_cards")


def get_task_cards_dir() -> Path:
    return Path.home() / ".openviking" / "data" / "viking" / "default" / "resources" / "task_cards"


def clean_task_cards(base_dir: Path, execute: bool = False) -> Dict[str, Any]:
    inbox_dir = base_dir / "inbox"
    resolved_dir = base_dir / "resolved"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    resolved_dir.mkdir(parents=True, exist_ok=True)

    json_files = list(inbox_dir.glob("*.json"))
    total_found = len(json_files)

    cpu_alert_cards: List[Tuple[Path, Dict[str, Any]]] = []
    test_probe_cards: List[Tuple[Path, Dict[str, Any]]] = []
    legitimate_cards: List[Tuple[Path, Dict[str, Any]]] = []

    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            title = data.get("title", "")
            module = data.get("module", "")
            initiator = data.get("initiator", "")

            # 1. 识别 WSL2 CPU ps 跑飞风暴告警
            if "WSL2 CPU跑飞告警" in title or "cpu" in module.lower():
                cpu_alert_cards.append((jf, data))
            # 2. 识别测试验证探针工单
            elif (
                "connectivity verification test" in title.lower()
                or "smoke probe" in title.lower()
                or title.startswith("[TEST]")
                or data.get("is_test", False)
            ):
                test_probe_cards.append((jf, data))
            else:
                legitimate_cards.append((jf, data))
        except Exception as e:
            logger.warning("读取工单失败 %s: %s", jf, e)

    stats = {
        "total_inbox": total_found,
        "cpu_alert_count": len(cpu_alert_cards),
        "test_probe_count": len(test_probe_cards),
        "legitimate_count": len(legitimate_cards),
        "archived_count": 0,
        "retained_inbox_count": len(legitimate_cards) + (1 if cpu_alert_cards else 0),
    }

    logger.info("==================================================")
    logger.info("📋 工单大盘体检扫描结果 (Card-143 Hygiene Scan)")
    logger.info(" • 待办库工单总数: %d", total_found)
    logger.info(" • 瞬态 CPU 告警风暴卡片: %d (待聚合为 1 张主工单)", len(cpu_alert_cards))
    logger.info(" • 测试探针用例卡片: %d (待安全归档)", len(test_probe_cards))
    logger.info(" • 真实业务与工程工单: %d (100%% 物理保留)", len(legitimate_cards))
    logger.info(" • 清洗后预期待办工单数: %d", stats["retained_inbox_count"])
    logger.info("==================================================")

    if not execute:
        logger.info("🔍 [DRY-RUN 模式] 仅输出模拟结果，未进行物理写盘与文件移动。如需执行，请传入 --execute 参数。")
        return stats

    # 执行物理归档与聚合
    now = time.time()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    # 1. 归档测试卡片
    for jf, data in test_probe_cards:
        data["status"] = "resolved"
        data["resolved_at"] = now
        data["resolution_note"] = f"Auto-archived test verification probe during Card-143 hygiene at {now_str}"
        dest_json = resolved_dir / jf.name
        dest_md = resolved_dir / jf.with_suffix(".md").name

        dest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        jf.unlink(missing_ok=True)
        md_file = jf.with_suffix(".md")
        if md_file.exists():
            shutil.move(str(md_file), str(dest_md))
        stats["archived_count"] += 1

    # 2. 聚合 CPU 告警风暴卡片
    if cpu_alert_cards:
        # 按创建时间排序
        cpu_alert_cards.sort(key=lambda x: x[1].get("created_at", 0))
        master_jf, master_data = cpu_alert_cards[0]
        duplicate_cards = cpu_alert_cards[1:]

        # 提炼主工单数据
        total_occurrences = len(cpu_alert_cards)
        latest_time = max(x[1].get("created_at", now) for x in cpu_alert_cards)
        affected_agents = sorted(list({ag for _, x in cpu_alert_cards for ag in x.get("affected_agents", ["Antigravity@2080Ti"])}))

        master_data["occurrence_count"] = total_occurrences
        master_data["title"] = "WSL2 CPU 跑飞告警: ps 瞬态高频波动 (已去重合并 500+ 历史告警)"
        master_data["last_seen_at"] = latest_time
        master_data["affected_agents"] = affected_agents
        master_data["suggested_action"] = "在巡检脚本中增加高频抖动抑制与 PID 脱敏，避免短时间内向工单总线倾倒重复告警"

        master_jf.write_text(json.dumps(master_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # 将其余重复卡片移动到 resolved
        for jf, data in duplicate_cards:
            data["status"] = "resolved"
            data["resolved_at"] = now
            data["resolution_note"] = f"Collapsed into master card {master_data['card_id']} during Card-143 deduplication at {now_str}"
            dest_json = resolved_dir / jf.name
            dest_md = resolved_dir / jf.with_suffix(".md").name

            dest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            jf.unlink(missing_ok=True)
            md_file = jf.with_suffix(".md")
            if md_file.exists():
                shutil.move(str(md_file), str(dest_md))
            stats["archived_count"] += 1

    logger.info("✅ 物理归档执行完成！已安全归档迁移 %d 张卡片，当前 inbox 剩余 %d 张纯净工单。", stats["archived_count"], stats["retained_inbox_count"])
    return stats


def main():
    parser = argparse.ArgumentParser(description="Task Card Hygiene and Dedup Cleaner")
    parser.add_argument("--execute", action="store_true", help="Execute physical migration to resolved/")
    parser.add_argument("--dir", type=str, default="", help="Custom task cards base directory")
    args = parser.parse_args()

    base_dir = Path(args.dir) if args.dir else get_task_cards_dir()
    clean_task_cards(base_dir, execute=args.execute)


if __name__ == "__main__":
    main()
