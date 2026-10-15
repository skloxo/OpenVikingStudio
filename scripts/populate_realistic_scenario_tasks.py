#!/usr/bin/env python3
"""
向 OpenViking 1933 本地服务注入全部 10 大任务类型的真实工况场景任务记录。
用于真实列表展示核验、适配走查与人肉验收。
密钥自动从 ~/.openviking/ov.conf 动态读取，严禁硬编码。
"""

import json
import os
from pathlib import Path
import httpx

BASE_URL = "http://127.0.0.1:1933/api/v1"

def get_root_api_key() -> str:
    env_key = os.environ.get("OPENVIKING_API_KEY")
    if env_key:
        return env_key
    conf_path = Path.home() / ".openviking" / "ov.conf"
    if conf_path.exists():
        try:
            with open(conf_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                server_cfg = data.get("server", {})
                key = server_cfg.get("root_api_key")
                if key:
                    return key
        except Exception:
            pass
    return ""

SCENARIOS = [
    # 1. 原子入库 (已完成 · ADD 新增)
    {
        "task_id": "biz_valet_arch_rfc",
        "task_type": "valet_parking",
        "human_title": "2026-09-11_BM25混合检索设计RFC.md",
        "initiator": "Agent (Gemini Flash)",
        "status": "completed",
        "resource_id": "viking://resources/staging/BM25混合检索设计RFC.md",
        "stage": "completed",
        "deliverable": {
            "uri": "viking://resources/master_memory/BM25混合检索设计RFC.md",
            "label": "成果物直达",
        },
        "result": {
            "action": "add",
            "similarity": 0.1824,
            "parked_nodes": 1,
            "saved_bytes": 0,
            "progress": {"completed": 1, "total": 1, "unit": "个节点"},
        },
        "meta_extra": {
            "source_name": "BM25混合检索设计RFC.md",
            "file_size": 18450,
            "action": "add",
            "similarity": 0.1824,
        },
    },
    # 2. 原子入库 (进行中 · 向量相似度探针)
    {
        "task_id": "biz_valet_running_probe",
        "task_type": "valet_parking",
        "human_title": "system_telemetry_patch.py",
        "initiator": "Agent (Claude 3.7)",
        "status": "running",
        "resource_id": "viking://resources/staging/system_telemetry_patch.py",
        "stage": "probe",
        "progress": {"completed": 0, "total": 1, "unit": "个节点"},
        "meta_extra": {
            "source_name": "system_telemetry_patch.py",
            "file_size": 4210,
            "progress_pct": 35,
        },
    },
    # 3. 资源处理 (已完成 · 多切片与实体织网)
    {
        "task_id": "biz_res_fastapi_guide",
        "task_type": "add_resource",
        "human_title": "FastAPI_Production_Architect.pdf",
        "initiator": "User (Admin)",
        "status": "completed",
        "resource_id": "viking://resources/docs/FastAPI_Production_Architect.pdf",
        "stage": "completed",
        "deliverable": {
            "uri": "viking://resources/docs/FastAPI_Production_Architect.pdf",
            "label": "成果物直达",
        },
        "result": {
            "file_count": 1,
            "processed_chunks": 48,
            "total_links": 12,
        },
        "meta_extra": {
            "source_name": "FastAPI_Production_Architect.pdf",
            "file_size": 1048576,
            "file_count": 1,
        },
    },
    # 4. 资源处理 (进行中 · 切片重构与向量化)
    {
        "task_id": "biz_res_running_embed",
        "task_type": "add_resource",
        "human_title": "Kubernetes_Operator_DeepDive.epub",
        "initiator": "Agent (Gemini Flash)",
        "status": "running",
        "resource_id": "viking://resources/books/Kubernetes_Operator_DeepDive.epub",
        "stage": "embedding",
        "progress": {"completed": 36, "total": 80, "unit": "切片"},
        "meta_extra": {
            "source_name": "Kubernetes_Operator_DeepDive.epub",
            "file_size": 5242880,
            "processed_chunks": 36,
            "total_chunks": 80,
            "progress_pct": 45,
        },
    },
    # 5. 会话提交 (已完成 · 提纯不可变事实)
    {
        "task_id": "biz_sess_refactor_commit",
        "task_type": "session_commit",
        "human_title": "任务中心高密度重构与双轨闭环研讨",
        "initiator": "Agent (Antigravity)",
        "status": "completed",
        "resource_id": "viking://sessions/89d09337-0a9c-4e17-b599-8011f587afa6",
        "stage": "completed",
        "deliverable": {
            "uri": "viking://resources/master_memory/evolution_lessons/20260911_tasks_center_refactor.md",
            "label": "成果物直达",
        },
        "result": {
            "turns_processed": 18,
            "lessons_extracted": 2,
            "facts_stored": 4,
        },
        "meta_extra": {
            "source_name": "会话 89d09337 (18 轮对话)",
            "turns_count": 18,
        },
    },
    # 6. 技能导入 (已完成 · 规范审计与注册)
    {
        "task_id": "biz_skill_bm25_import",
        "task_type": "add_skill",
        "human_title": "bm25-hybrid-retrieval",
        "initiator": "User (Admin)",
        "status": "completed",
        "resource_id": "viking://skills/bm25-hybrid-retrieval/SKILL.md",
        "stage": "completed",
        "deliverable": {
            "uri": "viking://skills/bm25-hybrid-retrieval/SKILL.md",
            "label": "成果物直达",
        },
        "result": {
            "valid_skills": 1,
            "scanned_skills": 1,
            "skills_indexed": 1,
        },
        "meta_extra": {
            "source_name": "SKILL.md",
            "skill_name": "bm25-hybrid-retrieval",
        },
    },
    # 7. 连接器导入 (已完成 · 飞书知识库同步)
    {
        "task_id": "biz_conn_feishu_wiki",
        "task_type": "connector_import",
        "human_title": "飞书知识库「量化风控投研规约」",
        "initiator": "Agent (Scheduler)",
        "status": "completed",
        "resource_id": "https://open.feishu.cn/wiki/wikcnAbCdEf123456",
        "stage": "completed",
        "deliverable": {
            "uri": "viking://resources/feishu/wikcnAbCdEf123456.md",
            "label": "成果物直达",
        },
        "result": {
            "fetched_docs": 12,
            "processed_chunks": 156,
        },
        "meta_extra": {
            "source_name": "飞书知识库 (12 篇文档)",
            "connector_id": "feishu-wiki",
        },
    },
    # 8. 全局索引重建 (已完成 · 扫描与重构)
    {
        "task_id": "biz_reindex_master_memory",
        "task_type": "admin_reindex",
        "human_title": "master_memory",
        "initiator": "User (Admin)",
        "status": "completed",
        "resource_id": "viking://resources/master_memory",
        "stage": "completed",
        "result": {
            "scanned_records": 1010,
            "rebuilt_records": 1112,
            "elapsed_seconds": 12,
        },
        "meta_extra": {
            "mode": "semantic_and_vectors",
            "scanned_records": 1010,
            "rebuilt_records": 1112,
        },
    },
    # 9. 快照恢复索引 (已完成 · Inode 节点还原)
    {
        "task_id": "biz_restore_v1495",
        "task_type": "snapshot_restore_reindex",
        "human_title": "snap_v1.4.95_release",
        "initiator": "User (Admin)",
        "status": "completed",
        "resource_id": "viking://snapshots/snap_v1.4.95_release",
        "stage": "completed",
        "result": {
            "restored_inodes": 45,
            "reindexed_items": 45,
        },
        "meta_extra": {
            "restored_inodes": 45,
        },
    },
    # 10. 旧数据迁移 (已完成 · 历史格式转换)
    {
        "task_id": "biz_mig_clawhub_v1",
        "task_type": "legacy_migration",
        "human_title": "clawhub_v1_legacy_store",
        "initiator": "Agent (System Migrator)",
        "status": "completed",
        "resource_id": "viking://system/legacy/clawhub_v1",
        "stage": "completed",
        "result": {
            "migrated_records": 88,
        },
        "meta_extra": {
            "migrated_records": 88,
        },
    },
    # 11. 旧数据清理 (已完成 · 孤儿引用回收)
    {
        "task_id": "biz_clean_temp_scratch",
        "task_type": "legacy_cleanup",
        "human_title": "staging_scratch_purging",
        "initiator": "Agent (Cron Purger)",
        "status": "completed",
        "resource_id": "viking://staging/temp",
        "stage": "completed",
        "result": {
            "cleaned_items": 32,
        },
        "meta_extra": {
            "cleaned_items": 32,
        },
    },
    # 12. 用户空间注销 (已完成 · 软注销与物理擦除)
    {
        "task_id": "biz_del_sandbox_test_user",
        "task_type": "user_delete",
        "human_title": "sandbox_test_user",
        "initiator": "User (Admin)",
        "status": "completed",
        "resource_id": "viking://user/sandbox_test_user",
        "stage": "completed",
        "result": {
            "vectors_dropped": 120,
            "files_unlinked": 15,
        },
        "meta_extra": {
            "user_id": "sandbox_test_user",
            "vectors_dropped": 120,
            "files_unlinked": 15,
        },
    },
]

def main():
    root_key = get_root_api_key()
    headers = {
        "Authorization": f"Bearer {root_key}",
        "Content-Type": "application/json",
    }
    print(f"🚀 开始向 {BASE_URL}/tasks/business 注入 12 条真实场景任务记录...")
    client = httpx.Client(timeout=10.0)
    success_count = 0

    for s in SCENARIOS:
        try:
            resp = client.post(f"{BASE_URL}/tasks/business", headers=headers, json=s)
            if resp.status_code == 200:
                print(f"  ✓ [{s['task_type']}] {s['human_title']} (tid={s['task_id']}, status={s['status']})")
                success_count += 1
            else:
                print(f"  ✗ [{s['task_type']}] Failed with HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"  ✗ [{s['task_type']}] Exception: {e}")

    print(f"\n🎉 注入完成：成功 {success_count} / {len(SCENARIOS)} 条真实场景任务记录！")

if __name__ == "__main__":
    main()
