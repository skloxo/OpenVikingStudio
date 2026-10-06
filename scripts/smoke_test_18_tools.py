import asyncio
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 18 个工具的标准冒烟测试参数
TARGET_DOC = "viking://" + "resources/master_memory/public_ports_summary.md"
TARGET_DIR = "viking://" + "resources/master_memory/"
PROBE_DOC = "viking://" + "resources/smoke_test_probe.md"

TEST_CASES = {
    'openviking_ping': {},
    'openviking_health': {},
    'openviking_find': {'query': 'node', 'limit': 1},
    'openviking_search': {'query': 'node', 'limit': 1},
    'openviking_smart_read': {'query': 'node', 'limit': 1},
    'openviking_read': {'target_uri': TARGET_DOC, 'level': '0'},
    'openviking_store': {'content': ''},
    'openviking_write': {'target_uri': PROBE_DOC, 'content': 'smoke test probe', 'mode': 'replace'},
    'openviking_code_search': {'query': 'def', 'limit': 1},
    'openviking_code_outline': {'target_uri': TARGET_DOC},
    'openviking_code_expand': {'target_uri': TARGET_DOC, 'symbol': 'SSOT'},
    'openviking_grep': {'pattern': 'SSOT', 'limit': 1},
    'openviking_record_evolution_lesson': {'skill_name': 'diagnosing-bugs', 'lesson_title': 'Smoke Probe Test', 'lesson': 'Smoke test executed'},
    'openviking_tree': {'target_uri': TARGET_DIR},
    'openviking_skills': {'limit': 1},
    'openviking_get_relations': {'uri': TARGET_DOC},
    'openviking_file_task_card': {'title': 'Smoke Probe Card', 'module': 'smoke', 'symptom': 'ok', 'hypothesis': 'ok', 'reproduce_steps': 'ok'},
    'openviking_list_pending_cards': {'limit': 1}
}

async def run_smoke():
    params = StdioServerParameters(
        command='python3',
        args=['/home/skloxo/aho/openclaw/project/OpenVikingStudio/mcp-openviking/satellite_mcp_server.py']
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_res = await session.list_tools()
            available = {t.name: t for t in tools_res.tools}
            print(f'=== 开始对 FastMCP 的 18 个工具执行真实链路冒烟体检 ===')
            
            passed = []
            failed = []
            for name, tool in available.items():
                args = TEST_CASES.get(name, {})
                try:
                    res = await session.call_tool(name, args)
                    text = res.content[0].text if res.content else ''
                    if '"status": "error"' in text or 'Traceback' in text:
                        print(f'❌ [FAIL] {name}: {text[:100]}...')
                        failed.append((name, text))
                    else:
                        print(f'✅ [PASS] {name}')
                        passed.append(name)
                except Exception as e:
                    print(f'❌ [EXC] {name}: {e}')
                    failed.append((name, str(e)))
            
            print(f'\n=== 体检汇总: {len(passed)} / {len(available)} 工具可用 ===')
            if failed:
                print('异常工具列表及原因:')
                for n, err in failed:
                    print(f' - {n}: {err[:120]}')
            else:
                print('🎉 全部 18 个工具均通过冒烟测试，真实链路 100% 畅通！')

if __name__ == '__main__':
    asyncio.run(run_smoke())
