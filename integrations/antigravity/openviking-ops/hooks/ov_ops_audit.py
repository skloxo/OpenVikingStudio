#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenViking Ops Privilege Audit Hook (PreToolUse)."""
import json
import sys

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        data = json.loads(raw)
        # 针对危险的停止服务操作做防御性日志
        args = data.get("tool_args", {})
        action = args.get("action", "")
        if action == "stop":
            sys.stderr.write("[OpenViking-Ops Guard] 收到停机特权操作指令，已审计记录并放行。\n")
    except Exception:
        pass
    sys.exit(0)

if __name__ == "__main__":
    main()
