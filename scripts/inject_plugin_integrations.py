"""
scripts/inject_plugin_integrations.py
为尚未配置 integration.channels 的插件母本规范化注入四位一体多渠道接入契约 (SSOT)。
遵循单向无状态插值与纯数据驱动原则。
"""

from pathlib import Path
import json

PLUGINS_META = [
    {
        'id': 'keepass-vault',
        'name': 'KeePass 凭据中枢',
        'desc': 'KeePass 凭据保险箱扩展，免明文索要与写前 .bak 快照守护',
        'dsh_pkg': 'dsh-plugin-keepass-vault',
        'mcp_url': '{{ENDPOINT_URL}}/mcp?plugin_id=keepass-vault'
    },
    {
        'id': 'openviking-ops',
        'name': 'OpenViking 系统运维治理',
        'desc': '体外大脑中枢运维特权插件 (17 项运维管理算子 + 2 项生命周期守卫)',
        'dsh_pkg': 'dsh-plugin-openviking-ops',
        'mcp_url': '{{ENDPOINT_URL}}/mcp?plugin_id=openviking-ops'
    },
    {
        'id': 'agent-circuit-breaker',
        'name': '智能体熔断断路器',
        'desc': '死循环防爆与连续报错自动熔断护栏 (force_ask 零误杀与自省心流)',
        'dsh_pkg': None,
        'mcp_url': '{{ENDPOINT_URL}}/mcp?plugin_id=agent-circuit-breaker'
    },
    {
        'id': 'cpa-squad',
        'name': 'CPA 算力聚合与分摊',
        'desc': '多模型聚合路由与多租户 Token 消耗阶梯分摊算子',
        'dsh_pkg': 'dsh-plugin-cpa',
        'mcp_url': '{{ENDPOINT_URL}}/mcp?plugin_id=cpa-squad'
    },
    {
        'id': 'dify',
        'name': 'Dify 工作流编排对接',
        'desc': 'Dify 复杂 DSL 任务流编排触发与异步轮询检索算子',
        'dsh_pkg': 'dsh-plugin-dify',
        'mcp_url': '{{ENDPOINT_URL}}/mcp?plugin_id=dify'
    },
    {
        'id': 'fleet-mesh',
        'name': '卫星集群组网与节点同频',
        'desc': '跨节点 (3070/2080Ti/甲骨文云) 状态探针与分布式节点同频算子',
        'dsh_pkg': 'dsh-plugin-openviking-fleet',
        'mcp_url': '{{ENDPOINT_URL}}/mcp?plugin_id=fleet-mesh'
    }
]

def main():
    root = Path(__file__).resolve().parent.parent
    base_dir = root / 'integrations' / 'antigravity'
    
    for p in PLUGINS_META:
        pid = p['id']
        pname = p['name']
        manifest_file = base_dir / pid / 'plugin.json'
        if not manifest_file.is_file():
            print(f'⚠️ Skipping missing {manifest_file}')
            continue
            
        data = json.loads(manifest_file.read_text(encoding='utf-8'))
        if 'integration' in data and data['integration'].get('channels'):
            print(f'ℹ️ {pid} already has integration.channels, skipping')
            continue
            
        channels = [
            {
                'id': 'antigravity',
                'name': 'Google 反重力',
                'install_cmd': f"powershell -ExecutionPolicy Bypass -Command \"iwr -Uri '{{{{ENDPOINT_URL}}}}/studio/{pid}-{{{{PLUGIN_VER}}}}.tgz' -OutFile '$env:TEMP\\{pid}.tgz'; New-Item -ItemType Directory -Force -Path \\\"$env:USERPROFILE\\.gemini\\config\\plugins\\{pid}\\\" | Out-Null; tar -xzf '$env:TEMP\\{pid}.tgz' -C \\\"$env:USERPROFILE\\.gemini\\config\\plugins\\{pid}\\\"; python \\\"$env:USERPROFILE\\.gemini\\config\\plugins\\{pid}\\setup.py\\\" --install --api {{{{ENDPOINT_URL}}}} --key {{{{USER_KEY}}}}\"",
                'agent_prompt': f"请帮我将当前反重力客户端 (Antigravity IDE / Desktop) 接入 {pname} ({pid}) 插件：\n1. 分发包直链：{{{{ENDPOINT_URL}}}}/studio/{pid}-{{{{PLUGIN_VER}}}}.tgz\n2. 挂载目录：$env:USERPROFILE\\.gemini\\config\\plugins\\{pid}\n3. 执行：python setup.py --install --api {{{{ENDPOINT_URL}}}} --key {{{{USER_KEY}}}} 完成自举安装与 FastMCP 挂载。",
                'config_snippet': f"{{\n  \"plugins\": {{\n    \"{pid}\": {{\n      \"installedFrom\": {{\n        \"id\": \"antigravity/plugin/{pid}\",\n        \"marketplace\": \"openviking-studio\",\n        \"version\": \"{{{{PLUGIN_VER}}}}\"\n      }}\n    }}\n  }}\n}}",
                'docs_markdown': '在 Windows PowerShell 中运行安装命令，自动完成下载解压、宿主注册与 FastMCP 双轨服务配置。亦可复制认主提示词直接在反重力对话框中一键启用。'
            }
        ]
        
        if p['dsh_pkg']:
            dsh_pkg = p['dsh_pkg']
            channels.append({
                'id': 'dsh',
                'name': 'DeepSeek Harness (DSH)',
                'install_cmd': f"npm install {{{{PACKAGE_URL}}}}",
                'config_snippet': f"{pid}:\n  endpointUrl: \"{{{{ENDPOINT_URL}}}}\"\n  userKey: \"{{{{USER_KEY}}}}\"\n  enableMcp: true",
                'docs_markdown': f'在 DSH 客户端插件市场安装，或在 profiles/desktop/node_modules 下解压加载。'
            })
            
        channels.append({
            'id': 'universal-mcp',
            'name': '通用 MCP 智能体',
            'install_cmd': 'npx -y @openviking/mcp-gateway',
            'config_snippet': f"{{\n  \"mcpServers\": {{\n    \"{pid}\": {{\n      \"url\": \"{p['mcp_url']}\",\n      \"headers\": {{\n        \"Authorization\": \"Bearer {{{{USER_KEY}}}}\"\n      }}\n    }}\n  }}\n}}",
            'docs_markdown': '兼容 Claude Desktop, Cursor, Windsurf, OpenClaw 等遵循标准 MCP 协议的智能体客户端。'
        })
        
        data['integration'] = {'channels': channels}
        manifest_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f'✔ Injected integration into {pid}/plugin.json')

if __name__ == '__main__':
    main()
