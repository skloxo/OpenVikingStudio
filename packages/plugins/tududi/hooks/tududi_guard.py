#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tududi OKR-GTD 生产级双轨守卫与静默自愈消音器 (tududi_guard v1.1.7)
基于波斯泰尔法则（Postel's Law: 宽进严出）与第一性原理（查理·芒格 / 奥卡姆 / 马斯克 哲学）：
1. 物理致命错误硬拦截 (Fail-Fast Deny)：
   - Task id 与实体 uid 异构主键字段名混淆拦截（防止 404）；
   - delete_* 空主键高危操作物理拦截（防止误删）；
   - priority 字符串/数字枚举校验（防止 400 崩溃）；
   - status / horizon 异构状态枚举校验（防止非法状态入库）；
   - add_subtask 缺少 parent_id 拦截；
2. 格式瑕疵与脏数据静默自愈 (Silent Auto-Sanitize & Overwrite)：
   - 标题中括号前缀（如 [运维] / [开发]）自动剥离；
   - 标题软编号（如 (T04-0004) / (TASK-045)）自动提取并下沉迁移至 note【关联编号】；
   - 重复项目名前缀（如 网格化平台：）自动截修；
   - 脏标签（today / someday / 汇报 / priority / status）自动过滤剔除；
   - create_task 缺省 assigned_to 时静默注入默认用户 skloxo (07mah9uku662d6u)；
   - 通过 PreToolUse 的 overwrite 输出原生地图级修正，零阻断、零报错、心流零中断！
3. 遵循 OpenViking 插件中心四位一体：
   - 纯标准库隔离 (-X utf8 -E -s -S)，零第三方依赖，冷启动 <= 20ms；
   - sys.stdin.readline() 单行流式读取，sys.stdout.buffer 原生直写 UTF-8 字节；
   - 全流程 BaseException 捕获兜底，退出码恒为 0 (Fail-Open)。
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, Tuple

FORBIDDEN_TAGS = {
    "today", "someday", "汇报",
    "p0", "p1", "p2", "p3", "urgent", "high", "medium", "low",
    "紧急", "高优", "高优先级", "低优先级", "重要",
    "todo", "done", "in_progress", "待办", "进行中", "已完成", "未开始",
    "工作", "个人",
}

VALID_TASK_STATUS = {
    "not_started", "pending", "planned", "in_progress",
    "waiting", "done", "completed", "cancelled", "archived",
}
VALID_PROJECT_STATUS = {
    "not_started", "planned", "in_progress", "waiting", "done", "cancelled",
}
VALID_TASK_PRIORITY = {"none", "low", "medium", "high"}
VALID_PROJECT_PRIORITY = {0, 1, 2, "0", "1", "2"}
VALID_GOAL_STATUS = {"active", "achieved", "paused", "dropped"}
VALID_GOAL_HORIZON = {"season", "year"}

TASK_ID_TOOLS = {
    "get_task", "update_task", "complete_task", "delete_task",
    "skip_task_occurrence", "add_task_comment", "list_task_comments",
    "create_task_relation", "list_task_relations", "remove_task_relation",
}
ENTITY_UID_TOOLS = {
    "get_project", "update_project", "delete_project", "share_project",
    "get_area", "update_area", "delete_area",
    "get_goal", "update_goal", "delete_goal",
    "get_habit", "update_habit", "delete_habit", "log_habit_completion", "skip_habit_period", "get_habit_stats",
    "get_note", "update_note", "delete_note",
    "get_tag", "update_tag", "delete_tag",
    "get_view", "update_view", "delete_view",
    "get_person", "update_person", "delete_person",
    "get_inbox_item", "update_inbox_item", "process_inbox_item", "delete_inbox_item",
}
DELETE_UID_TOOLS = {
    "delete_project", "delete_area", "delete_goal", "delete_habit",
    "delete_note", "delete_person", "delete_tag", "delete_view", "delete_inbox_item",
}


def _safe_stdout(payload: Dict[str, Any]) -> None:
    try:
        raw_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sys.stdout.buffer.write(raw_bytes + b"\n")
        sys.stdout.buffer.flush()
    except Exception:
        pass


def _extract_tududi_call(tool_call: Dict[str, Any]) -> Tuple[str, Dict[str, Any], bool]:
    raw_name = str(tool_call.get("name", "") or "")
    raw_args = tool_call.get("arguments") or tool_call.get("args") or {}
    if not isinstance(raw_args, dict):
        raw_args = {}

    if raw_name == "call_mcp_tool":
        srv = str(raw_args.get("ServerName", "") or "").lower()
        if "tududi" in srv:
            inner_tool = str(raw_args.get("ToolName", "") or "")
            inner_args = raw_args.get("Arguments") or {}
            if not isinstance(inner_args, dict):
                inner_args = {}
            return inner_tool, inner_args, True
        return "", {}, False

    if "tududi" in raw_name.lower():
        for prefix in ("mcp_tududi_core_", "mcp_tududi-core_", "mcp_tududi_"):
            if raw_name.startswith(prefix):
                return raw_name[len(prefix):], raw_args, False
        return raw_name, raw_args, False

    return "", {}, False


def sanitize_task_args(tool_name: str, args: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """静默自愈清洗器：自动剥离中括号、搬运软编号入 note、切除项目名前缀、过滤脏标签并补齐默认指派人"""
    changed = False
    new_args = dict(args)

    if tool_name in {"create_task", "update_task", "add_subtask"}:
        name = str(new_args.get("name", "") or "")
        if name:
            orig_name = name
            # 1. 自动剥离中括号前缀 [运维] / [开发] 等
            name = re.sub(r"^\[(运维|规划|开发|缺陷|汇报|待办|测试|P[0-9]|TASK)\]\s*", "", name).strip()
            
            # 2. 自动提取软编号并迁移至 note
            codes = re.findall(r"[\(\[](T\d+-\d+|TASK-[A-Z0-9\-]+)[\)\]]", name, re.IGNORECASE)
            if codes:
                name = re.sub(r"\s*[\(\[](T\d+-\d+|TASK-[A-Z0-9\-]+)[\)\]]\s*", " ", name).strip()
                curr_note = str(new_args.get("note", "") or "")
                if "【关联编号】" not in curr_note:
                    code_str = f"\n\n【关联编号】\n{', '.join(codes)}"
                    new_args["note"] = (curr_note.strip() + code_str).strip()
                changed = True

            # 3. 自动修剪重复项目名前缀
            name = re.sub(r"^(O[1-4]-KR\d+|网格化管理平台|干部公寓|物业系统|智能门锁|AI监控|安防监控|滴滴企业打车|园区门户|仓储方案|Tududi)\s*[:：]\s*", "", name).strip()

            if name != orig_name:
                new_args["name"] = name
                changed = True

        # 4. 自动过滤脏标签 (today/someday/汇报等)
        tags = new_args.get("tags")
        if isinstance(tags, list):
            cleaned_tags = [t for t in tags if str(t).lstrip("#@").lower() not in FORBIDDEN_TAGS]
            if cleaned_tags != tags:
                new_args["tags"] = cleaned_tags
                changed = True

        # 5. 自动补全默认责任人 (skloxo)
        if tool_name == "create_task":
            if not new_args.get("assigned_to"):
                new_args["assigned_to"] = "07mah9uku662d6u"
                changed = True

    return new_args, changed


def main() -> None:
    try:
        raw_line = sys.stdin.readline()
        if not raw_line:
            _safe_stdout({"decision": "allow"})
            return

        payload = json.loads(raw_line.strip())
        tool_call = payload.get("toolCall", {})
        tool_name, args, is_mcp_wrapper = _extract_tududi_call(tool_call)
        if not tool_name:
            _safe_stdout({"decision": "allow"})
            return

        # ==========================================
        # 1. 物理致命级硬拦截 (Fail-Fast Physical Gates)
        # ==========================================

        # (1) Task (id) 与其余实体 (uid) 主键字段名混淆纠偏
        if tool_name in TASK_ID_TOOLS:
            if (args.get("id") is None or str(args.get("id", "")).strip() == "") and args.get("uid"):
                _safe_stdout({
                    "decision": "deny",
                    "reason": f"TududiGuard 主键纠偏：{tool_name} 的主键参数名为 'id'（而非 'uid'），请将 uid 的值传给参数 'id'。"
                })
                return
        elif tool_name in ENTITY_UID_TOOLS:
            if not str(args.get("uid", "") or "").strip() and args.get("id") is not None:
                _safe_stdout({
                    "decision": "deny",
                    "reason": f"TududiGuard 主键纠偏：{tool_name} 的主键参数名为 15 位字符串 'uid'（而非数字 'id'），请先调用 list_* 获取真实 uid。"
                })
                return
        elif tool_name == "add_subtask":
            if args.get("parent_id") is None or str(args.get("parent_id", "")).strip() == "":
                _safe_stdout({
                    "decision": "deny",
                    "reason": "TududiGuard 参数拦截：add_subtask 必须提供非空 'parent_id'（父任务的 ID 或 UID）。"
                })
                return

        # (2) 高危删除操作空主键校验
        if tool_name in DELETE_UID_TOOLS:
            if not str(args.get("uid", "") or "").strip():
                _safe_stdout({
                    "decision": "deny",
                    "reason": f"TududiGuard 物理拦截：{tool_name} 必须提供非空 15 位字符串参数 'uid'（请先调用 list_* 查询真实 uid）。"
                })
                return
        elif tool_name == "delete_task":
            if args.get("id") is None or str(args.get("id", "")).strip() == "":
                _safe_stdout({
                    "decision": "deny",
                    "reason": "TududiGuard 物理拦截：delete_task 必须提供非空参数 'id'（任务 ID 或 UID）。"
                })
                return

        # (3) 优先级枚举契约校验 (防止 400 崩溃)
        if tool_name in {"create_task", "update_task", "add_subtask", "create_habit", "update_habit"}:
            prio = args.get("priority")
            if prio is not None and str(prio) not in VALID_TASK_PRIORITY:
                _safe_stdout({
                    "decision": "deny",
                    "reason": f"TududiGuard 参数纠偏：{tool_name} 的 priority 仅支持字符串 'none' | 'low' | 'medium' | 'high'（不支持 '{prio}'，最高优请传 'high'）。"
                })
                return
        elif tool_name in {"create_project", "update_project"}:
            prio = args.get("priority")
            if prio is not None and prio not in VALID_PROJECT_PRIORITY:
                _safe_stdout({
                    "decision": "deny",
                    "reason": f"TududiGuard 参数纠偏：{tool_name} 的 priority 为数字枚举 0(低) | 1(中) | 2(高)，不支持 '{prio}'。"
                })
                return

        # (4) 状态与周期枚举契约校验
        if tool_name in {"update_task", "list_tasks"}:
            st = args.get("status")
            if st is not None and str(st) not in VALID_TASK_STATUS:
                _safe_stdout({
                    "decision": "deny",
                    "reason": f"TududiGuard 参数纠偏：{tool_name} 的 status 仅支持 'not_started' | 'planned' | 'in_progress' | 'waiting' | 'done' | 'cancelled'（不支持 '{st}'）。"
                })
                return
        elif tool_name in {"create_project", "update_project"}:
            st = args.get("status")
            if st is not None and str(st) not in VALID_PROJECT_STATUS:
                _safe_stdout({
                    "decision": "deny",
                    "reason": f"TududiGuard 参数纠偏：{tool_name} 的 status 仅支持 'not_started' | 'planned' | 'in_progress' | 'waiting' | 'done' | 'cancelled'（不支持 '{st}'）。"
                })
                return
        elif tool_name in {"create_goal", "update_goal"}:
            st = args.get("status")
            if st is not None and str(st) not in VALID_GOAL_STATUS:
                _safe_stdout({
                    "decision": "deny",
                    "reason": f"TududiGuard 参数纠偏：{tool_name} 的 status 仅支持 'active' | 'achieved' | 'paused' | 'dropped'（不支持 '{st}'）。"
                })
                return
            hz = args.get("horizon")
            if hz is not None and str(hz) not in VALID_GOAL_HORIZON:
                _safe_stdout({
                    "decision": "deny",
                    "reason": f"TududiGuard 参数纠偏：{tool_name} 的 horizon 仅支持 'season' | 'year'（不支持 '{hz}'）。"
                })
                return

        # ==========================================
        # 2. 格式瑕疵静默自愈 (Silent Auto-Sanitization)
        # ==========================================
        cleaned_args, is_changed = sanitize_task_args(tool_name, args)
        if is_changed:
            if is_mcp_wrapper:
                # 针对 call_mcp_tool，重写 Arguments
                _safe_stdout({
                    "decision": "allow",
                    "overwrite": {
                        "Arguments": cleaned_args
                    }
                })
            else:
                _safe_stdout({
                    "decision": "allow",
                    "overwrite": cleaned_args
                })
            return

        _safe_stdout({"decision": "allow"})

    except BaseException:
        _safe_stdout({"decision": "allow"})
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
