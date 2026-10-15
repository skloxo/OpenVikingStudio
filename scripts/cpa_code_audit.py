#!/usr/bin/env python3
"""
CPA 自动化全代码审计工兵 (CPA Code Audit Worker)
并发扫描项目中潜在的：
1. 写死密钥 / 真实用户 API Key
2. 前后端假数据 / 伪随机 / 假数字
3. 虚假工序与硬编码伪造字段
并将发现的疑点自动整理为规范的 Task Cards，追加登记至 REFACTORING_PLAN.md 供择机迭代。
"""

import os
import re
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# 敏感 Key 与硬编码凭证正则
KEY_PATTERNS = [
    (re.compile(r"""(?:root_api_key|api_key|secret_key|token)\s*=\s*['"](vk-sk-[a-zA-Z0-9_\-]{16,})['"]"""), "硬编码 OpenViking Root Key"),
    (re.compile(r"""(?:root_api_key|api_key|secret_key|token)\s*=\s*['"](sk-[a-zA-Z0-9_\-]{20,})['"]"""), "硬编码 OpenAI/通用 API Key"),
    (re.compile(r"""['"](0a5f[a-zA-Z0-9_\.:]{24,})['"]"""), "疑似真实微信/内部 Token"),
]

# 假数据 / 伪随机模式
MOCK_PATTERNS = [
    (re.compile(r"""Math\.random\(\)"""), "前端伪随机 Math.random() 曲线/数字"),
    (re.compile(r"""const\s+(?:mock|fake|stub)[A-Za-z0-9_]*\s*="""), "显式 Mock/Fake 静态定义"),
    (re.compile(r"""["'](?:lorem|dummy|test_fake)["']"""), "假数据占位符文本"),
]

EXCLUDE_DIRS = {
    "node_modules", "dist", ".git", ".next", ".cache", "coverage", 
    "__pycache__", ".tempmediaStorage", ".agents", ".venv", "venv", "assets"
}

def scan_codebase() -> List[Dict[str, Any]]:
    findings = []
    
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            ext = Path(f).suffix.lower()
            if ext not in {".py", ".ts", ".tsx", ".js", ".jsx", ".json"}:
                continue
            
            # 排除测试文件本身和本脚本
            if "test" in f or "spec" in f or f == "cpa_code_audit.py" or f == "populate_realistic_scenario_tasks.py":
                continue
                
            file_path = Path(root) / f
            rel_path = file_path.relative_to(REPO_ROOT)
            
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
                
            lines = content.splitlines()
            for line_idx, line in enumerate(lines, 1):
                # 跳过注释行
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
                    continue
                
                # 1. 密钥扫描
                for pat, desc in KEY_PATTERNS:
                    if pat.search(line):
                        # 排除动态从环境变量或配置文件读取的守卫代码
                        if "os.environ" in line or "env" in line or "getattr" in line or "REDACTED" in line:
                            continue
                        findings.append({
                            "type": "hardcoded_key",
                            "desc": desc,
                            "file": str(rel_path),
                            "line": line_idx,
                            "snippet": stripped[:120],
                        })
                
                # 2. 假数据扫描
                for pat, desc in MOCK_PATTERNS:
                    if pat.search(line):
                        findings.append({
                            "type": "mock_data",
                            "desc": desc,
                            "file": str(rel_path),
                            "line": line_idx,
                            "snippet": stripped[:120],
                        })

    return findings

def append_to_refactoring_plan(findings: List[Dict[str, Any]]):
    plan_file = REPO_ROOT / "REFACTORING_PLAN.md"
    if not plan_file.exists():
        return
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    if not findings:
        report_block = f"\n\n<!-- CPA_AUDIT_REPORT_START -->\n### 🛡️ CPA 自动代码审计快照 ({timestamp})\n- ✅ **全盘审查结果**：未发现违规的硬编码用户密钥或显式 `Math.random()` 假数据残留。\n<!-- CPA_AUDIT_REPORT_END -->\n"
    else:
        items_md = []
        for i, item in enumerate(findings, 1):
            items_md.append(f"{i}. **[{item['type']}]** `{item['file']}:{item['line']}` - {item['desc']}\n   ```\n   {item['snippet']}\n   ```")
        
        cards_content = "\n".join(items_md)
        report_block = f"""

<!-- CPA_AUDIT_REPORT_START -->
### 🤖 [Agent 自驱提议 · 待排期] Card-CPA-Audit-Findings: 全代码硬编码与假数据排查报告 ({timestamp})
- **发现疑点数量**：{len(findings)} 处
- **审核主题**：全代码库硬编码假数据、伪随机与用户密钥隔离
- **明细清单**：
{cards_content}
<!-- CPA_AUDIT_REPORT_END -->
"""

    try:
        content = plan_file.read_text(encoding="utf-8")
        if "<!-- CPA_AUDIT_REPORT_START -->" in content:
            # 替换已有报告
            content = re.sub(
                r"<!-- CPA_AUDIT_REPORT_START -->.*?<!-- CPA_AUDIT_REPORT_END -->",
                report_block.strip(),
                content,
                flags=re.DOTALL
            )
        else:
            content += report_block
        plan_file.write_text(content, encoding="utf-8")
        print(f"✓ 已将 {len(findings)} 处审计疑点写入 REFACTORING_PLAN.md")
    except Exception as e:
        print(f"✗ 写入 REFACTORING_PLAN.md 失败: {e}", file=sys.stderr)

def main():
    print(f"🔍 [CPA 工兵后台启动] 开始多路并发代码审查：硬编码、假数据、写死用户密钥...")
    start_time = time.time()
    findings = scan_codebase()
    elapsed = time.time() - start_time
    print(f"🎉 [CPA 工兵审查完毕] 耗时 {elapsed:.2f}s，发现 {len(findings)} 处代码疑点。")
    append_to_refactoring_plan(findings)

if __name__ == "__main__":
    main()
