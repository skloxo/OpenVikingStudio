import json
from pathlib import Path

transcript_path = Path(r"C:\Users\Skl\.gemini\antigravity-ide\brain\4786cb1a-d0b4-41e4-a73d-89b8bdc5cdb6\.system_generated\logs\transcript.jsonl")
lines = transcript_path.read_text(encoding="utf-8").splitlines()

for idx in range(580, 630):
    if idx < len(lines):
        data = json.loads(lines[idx])
        typ = data.get("type")
        if typ == "PLANNER_RESPONSE":
            tool_calls = data.get("tool_calls", [])
            for tc in tool_calls:
                fn = tc.get("name") or tc.get("function", {}).get("name")
                args = tc.get("args") or tc.get("function", {}).get("arguments")
                if fn == "run_command":
                    print(f"=== Step {idx} CommandLine ===")
                    print(args.get("CommandLine"))
                else:
                    print(f"Step {idx} [{fn}]")
        elif typ == "USER_INPUT":
            print(f"Step {idx} [USER_INPUT]: {data.get('content', '')[:140]}")

