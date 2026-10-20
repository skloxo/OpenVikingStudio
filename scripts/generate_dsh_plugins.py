#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/generate_dsh_plugins.py
生成与维护全系解耦 DSH 独立桥接器源码文件 (package.json, cordis.patch.yml, README.md, client.js, index.js)。
涵盖：
1. dsh-plugin-openviking-memory (2.0.13, 34 战地武器 + 3 Hook)
2. dsh-plugin-openviking-ops (1.0.1, 17 运维特权 + 2 Hook)
3. dsh-plugin-openviking-fleet (1.0.1, 2 集群工具 + 1 Hook)
4. dsh-plugin-openviking (2.0.13, 兼容别名包)
5. dsh-plugin-keepass-vault (1.0.2, 本地私有凭据保险箱，补齐 bundle patch 与 slots GUI)
6. dsh-plugin-dify (1.0.1, Dify 智能体与工作流中枢独立桥接器)
7. dsh-plugin-cpa (1.0.1, CPA 跨模型算力协同独立桥接器)
"""

import json
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
STUDIO_DIR = ROOT_DIR if (ROOT_DIR / "integrations").exists() else ROOT_DIR / "OpenVikingStudio"
BASE_DIR = STUDIO_DIR / "integrations" / "deepseek-harness"

# =========================================================================
# 1. 原生插件族定义 (Memory, Ops, Fleet)
# =========================================================================
NATIVE_PLUGINS = {
    "dsh-plugin-openviking-memory": {
        "id": "openviking-memory",
        "pkg_name": "dsh-plugin-openviking-memory",
        "version": "2.0.16",
        "title": "OpenViking 核心长程记忆与代码战地",
        "icon": "🧠",
        "desc": "体外大脑长程记忆语义检索、代码感知、上下文路由与经验沉淀完全体 (34 项战地工具 + 3 项 Hook 物理守卫)",
        "default_agent": "deepseek-harness@satellite",
        "default_endpoint": "https://vk.tide.red/mcp",
        "default_base": "https://vk.tide.red",
        "tools_count": 34,
        "hooks_count": 3,
        "has_memory_hook": True,
    },
    "dsh-plugin-openviking-ops": {
        "id": "openviking-ops",
        "pkg_name": "dsh-plugin-openviking-ops",
        "version": "1.0.3",
        "title": "OpenViking 系统运维治理插件",
        "icon": "🛡️",
        "desc": "后台专属运维治理、死信自愈、知识索引重建与哨兵巡检 (17 项运维特权工具 + 2 项 Hook 守卫)",
        "default_agent": "openviking-ops@sentinel",
        "default_endpoint": "https://vk.tide.red/mcp",
        "default_base": "https://vk.tide.red",
        "tools_count": 17,
        "hooks_count": 2,
        "has_memory_hook": False,
    },
    "dsh-plugin-openviking-fleet": {
        "id": "fleet-mesh",
        "pkg_name": "dsh-plugin-openviking-fleet",
        "version": "1.0.3",
        "title": "卫星集群同频运维插件",
        "icon": "🌐",
        "desc": "跨物理机节点同频健康体检、代码与配置一键同频同步 (2 项跨机工具 + 1 项 Hook 守卫)",
        "default_agent": "fleet-mesh@coordinator",
        "default_endpoint": "https://vk.tide.red/mcp",
        "default_base": "https://vk.tide.red",
        "tools_count": 2,
        "hooks_count": 1,
        "has_memory_hook": False,
    },
}


def build_native_client_js(info: dict) -> str:
    plugin_id = info["id"]
    pkg_name = info["pkg_name"]
    version = info.get("version", "2.0.13")
    title = info["title"]
    icon = info["icon"]
    tools_count = info["tools_count"]
    hooks_count = info["hooks_count"]
    default_base = info["default_base"]
    default_agent = info["default_agent"]
    panel_name = f"{pkg_name.replace('-', '_').title().replace('_', '')}Panel"

    return f"""/**
 * client.js - {title} DSH Client Cockpit Plugin
 * 纯原生 React (由 DSH 宿主环境提供注入)，零外部打包依赖。
 * 遵循 Cockpit UI 规范：NO GREEN EVER 🚫 (#0891b2, #e11d48), 字号 >= 12px, 6px 微圆角。
 */

window.__ModuleLoader__.load({{
  id: '{pkg_name}',
  factory(require) {{
    const React = require('react');
    const h = React.createElement;
    const {{ useState, useEffect, useCallback }} = React;

    const STORAGE_KEY = '{pkg_name.replace("-", "_")}_config';
    const CAPS_STORAGE_KEY = '{pkg_name.replace("-", "_")}_capabilities';

    function loadSavedConfig() {{
      try {{
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      }} catch (_) {{}}
      return {{
        endpointUrl: '',
        userKey: '',
        disabledTools: [],
        disabledHooks: [],
      }};
    }}

    function loadSavedCaps() {{
      try {{
        const raw = localStorage.getItem(CAPS_STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      }} catch (_) {{}}
      return null;
    }}

    function saveConfig(cfg) {{
      try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg)); }} catch (_) {{}}
    }}

    function saveCaps(caps) {{
      try {{ localStorage.setItem(CAPS_STORAGE_KEY, JSON.stringify(caps)); }} catch (_) {{}}
    }}

    function {panel_name}(props) {{
      const [config, setConfig] = useState(loadSavedConfig);
      const [caps, setCaps] = useState(loadSavedCaps);
      const [showKey, setShowKey] = useState(false);
      const [probeReport, setProbeReport] = useState(null);
      const [testing, setTesting] = useState(false);
      const [saving, setSaving] = useState(false);
      const [saveToast, setSaveToast] = useState(null);
      const [showToolsList, setShowToolsList] = useState(false);

      const handleChange = (field, value) => {{
        setConfig((prev) => ({{ ...prev, [field]: value }}));
      }};

      const toggleTool = (toolId) => {{
        setConfig((prev) => {{
          const list = prev.disabledTools || [];
          const next = list.includes(toolId) ? list.filter((t) => t !== toolId) : [...list, toolId];
          return {{ ...prev, disabledTools: next }};
        }});
      }};

      const getBaseUrl = (url) => {{
        let base = (url || '').trim();
        base = base.replace(/\\/mcp\\/?$/i, '').replace(/\\/+$/, '');
        return base;
      }};

      const handleTest = async () => {{
        setTesting(true);
        setProbeReport(null);
        const base = getBaseUrl(config.endpointUrl);
        if (!base) {{
          setProbeReport({{
            ok: false,
            totalLatency: 0,
            error: '请先填写 OpenViking 服务端接口地址',
          }});
          setTesting(false);
          return;
        }}
        const start = Date.now();
        const fetchFn = typeof window !== 'undefined' && window.fetch ? window.fetch.bind(window) : fetch;

        const headers = {{ 'Content-Type': 'application/json' }};
        if (config.userKey) headers['Authorization'] = `Bearer ${{config.userKey}}`;

        try {{
          const res = await fetchFn(`${{base}}/api/v1/system/client-capabilities?plugin_id={plugin_id}&probe=full`, {{
            headers,
            signal: AbortSignal.timeout(6000),
          }});
          const totalLatency = Date.now() - start;

          if (res.ok) {{
            const data = await res.json();
            setCaps(data);
            saveCaps(data);
            setProbeReport({{
              ok: true,
              totalLatency,
              version: data.version || '{version}',
              toolsCount: data.total_authorized_tools || data.plugins?.[0]?.tools?.length || {tools_count},
              hooksCount: data.hooks?.length || {hooks_count},
              role: data.role || 'user',
              probes: data.probes || {{}},
            }});
          }} else {{
            setProbeReport({{
              ok: false,
              totalLatency,
              status: res.status,
              error: `HTTP ${{res.status}} 鉴权或服务拒绝 (${{res.statusText || 'Error'}})`,
            }});
          }}
        }} catch (err) {{
          setProbeReport({{
            ok: false,
            totalLatency: Date.now() - start,
            error: err.message || '网络连接超时或地址不可达',
          }});
        }} finally {{
          setTesting(false);
        }}
      }};

      const handleSave = () => {{
        setSaving(true);
        saveConfig(config);
        setTimeout(() => {{
          setSaving(false);
          setSaveToast({{ ok: true, msg: '配置已持久化保存，将在下次会话原子生效' }});
          setTimeout(() => setSaveToast(null), 3500);
        }}, 300);
      }};

      const toolsList = caps?.plugins?.[0]?.tools || [];

      return h('div', {{
        style: {{
          padding: '16px',
          background: 'var(--dsw-alias-bg-l1, #ffffff)',
          color: 'var(--dsw-alias-text-primary, #0f1115)',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          fontSize: '12px',
          borderRadius: '8px',
          border: '1px solid var(--dsw-alias-border-l1, rgba(0,0,0,0.08))',
          margin: '8px 0',
        }}
      }},
        // 头部
        h('div', {{ style: {{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--dsw-alias-border-l1, rgba(0,0,0,0.08))', paddingBottom: '10px' }} }},
          h('div', {{ style: {{ display: 'flex', alignItems: 'center', gap: '8px' }} }},
            h('span', {{ style: {{ fontSize: '18px' }} }}, '{icon}'),
            h('div', null,
              h('div', {{ style: {{ fontWeight: '600', fontSize: '13px' }} }}, '{title}'),
              h('div', {{ style: {{ fontSize: '11px', color: '#64748b' }} }}, '{pkg_name} · 专属解耦通信桥梁')
            )
          ),
          h('button', {{
            type: 'button',
            onClick: handleTest,
            disabled: testing,
            style: {{
              background: '#0891b2',
              color: '#ffffff',
              border: 'none',
              padding: '4px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: '500',
              cursor: testing ? 'not-allowed' : 'pointer',
            }},
          }}, testing ? '探测中...' : '⚡ 连通性测试')
        ),
        // 探针报告条
        probeReport
          ? h('div', {{
              style: {{
                margin: '10px 0',
                padding: '8px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                background: probeReport.ok ? 'rgba(6, 182, 212, 0.08)' : 'rgba(244, 63, 94, 0.08)',
                border: `1px solid ${{probeReport.ok ? '#0891b2' : '#e11d48'}}`,
                color: probeReport.ok ? '#0891b2' : '#e11d48',
              }},
            }},
            probeReport.ok
              ? `✅ 连接成功 · 延迟 ${{probeReport.totalLatency}}ms · 服务端版本 v${{probeReport.version}} · 鉴权身份: ${{probeReport.role}} (就绪 ${{probeReport.toolsCount}} 项工具 / ${{probeReport.hooksCount}} 项 Hook)`
              : `❌ 连接失败 · ${{probeReport.error}}`
            )
          : null,
        // 表单字段组
        h('div', {{ style: {{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }} }},
          // 接口地址
          h('div', null,
            h('div', {{ style: {{ marginBottom: '4px' }} }},
              h('label', {{ style: {{ fontWeight: '500' }} }}, 'OpenViking 服务端接口地址:')
            ),
            h('input', {{
              type: 'text',
              value: config.endpointUrl,
              onChange: (e) => handleChange('endpointUrl', e.target.value),
              placeholder: '例如 https://vk.tide.red 或 http://127.0.0.1:1933',
              style: {{ width: '100%', boxSizing: 'border-box', padding: '6px 8px', fontSize: '12px', fontFamily: 'monospace', borderRadius: '6px', border: '1px solid var(--dsw-alias-border-l2, rgba(0,0,0,0.15))', background: 'rgba(0,0,0,0.02)' }},
            }})
          ),
          // User API Key
          h('div', null,
            h('label', {{ style: {{ display: 'block', marginBottom: '4px', fontWeight: '500' }} }}, '用户专属 API 密钥 (User Key):'),
            h('div', {{ style: {{ display: 'flex', gap: '6px' }} }},
              h('input', {{
                type: showKey ? 'text' : 'password',
                value: config.userKey,
                onChange: (e) => handleChange('userKey', e.target.value),
                placeholder: '在 Web Studio 用户管理复制您的专属 User Key',
                style: {{ flex: 1, boxSizing: 'border-box', padding: '6px 8px', fontSize: '12px', fontFamily: 'monospace', borderRadius: '6px', border: '1px solid var(--dsw-alias-border-l2, rgba(0,0,0,0.15))', background: 'rgba(0,0,0,0.02)' }},
              }}),
              h('button', {{
                type: 'button',
                onClick: () => setShowKey(!showKey),
                style: {{ padding: '0 10px', borderRadius: '6px', border: '1px solid var(--dsw-alias-border-l2, rgba(0,0,0,0.15))', background: 'rgba(0,0,0,0.04)', fontSize: '12px', cursor: 'pointer' }},
              }}, showKey ? '隐藏' : '显示')
            )
          )
        ),
        // 专属能力清单呈现
        h('div', {{ style: {{ marginTop: '12px', padding: '8px 10px', background: 'rgba(6, 182, 212, 0.03)', border: '1px solid rgba(6, 182, 212, 0.18)', borderRadius: '6px' }} }},
          h('div', {{ style: {{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }} }},
            h('span', {{ style: {{ fontWeight: '600', color: '#0891b2' }} }}, `专属能力: ${{toolsList.length || {tools_count}}} 工具 · ${{caps?.hooks?.length || {hooks_count}}} Hooks`),
            h('button', {{
              type: 'button',
              onClick: () => setShowToolsList(!showToolsList),
              style: {{ background: 'transparent', border: 'none', color: '#0891b2', cursor: 'pointer', fontSize: '12px' }},
            }}, showToolsList ? '收起清单 ▲' : '查看工具清单 ▼')
          ),
          showToolsList && toolsList.length > 0
            ? h('div', {{ style: {{ marginTop: '8px', maxHeight: '180px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }} }},
                toolsList.map(t => h('div', {{ key: t.id, style: {{ fontSize: '12px', color: '#64748b', display: 'flex', justifyContent: 'space-between' }} }},
                  h('span', {{ style: {{ fontFamily: 'monospace', color: '#0f1115' }} }}, t.name || t.id),
                  h('span', null, t.description)
                ))
              )
            : null
        ),
        // 保存按钮
        h('div', {{ style: {{ marginTop: '14px', display: 'flex', justifyContent: 'flex-end', gap: '8px' }} }},
          h('button', {{
            type: 'button',
            onClick: handleSave,
            disabled: saving,
            style: {{
              background: '#0891b2',
              color: '#ffffff',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              fontWeight: '600',
              fontSize: '12px',
              cursor: saving ? 'not-allowed' : 'pointer',
            }},
          }}, saving ? '保存校验中...' : '💾 保存配置')
        ),
        // 保存反馈 Toast
        saveToast
          ? h('div', {{
              style: {{
                marginTop: '10px',
                padding: '8px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                background: saveToast.ok ? 'rgba(6, 182, 212, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                border: `1px solid ${{saveToast.ok ? '#0891b2' : '#e11d48'}}`,
                color: saveToast.ok ? '#0891b2' : '#e11d48',
              }},
            }}, saveToast.msg)
          : null
      );
    }}

    function apply(ctx) {{
      ctx.slots.inject('plugins.bundle.config', () =>
        ctx.slots.register(
            {{
              name: 'plugins.bundle.config',
              key: '{pkg_name}',
            }},
            {panel_name}
        )
      );
      if ('{pkg_name}' === 'dsh-plugin-openviking-memory') {{
        ctx.slots.inject('plugins.bundle.config', () =>
          ctx.slots.register(
              {{
                name: 'plugins.bundle.config',
                key: 'dsh-plugin-openviking',
              }},
              {panel_name}
          )
        );
      }}
    }}

    return {{
      inject: ['slots'],
      apply,
    }};
  }},
}});
"""


def build_native_index_js(info: dict) -> str:
    pkg_name = info["pkg_name"]
    plugin_id = info["id"]
    title = info["title"]
    has_mem_hook = info["has_memory_hook"]

    return f"""/**
 * {pkg_name}
 * {title} - DeepSeek Harness (DSH) 独立 Cordis RPC 桥接器与 Hook 套件。
 * 遵循官方 DSH Schemastery & Cordis 规范，单包自治，解耦独立。
 */

import {{ appendFileSync, statSync, renameSync, existsSync, readFileSync }} from 'node:fs'
import {{ resolve }} from 'node:path'
import {{ fileURLToPath }} from 'node:url'

export const name = '{pkg_name}'
export const inject = ['agents', 'sessions', 'tools', 'systemPrompt']

import Schema from './schema.js'

function v(s) {{
  return typeof s?.volatile === 'function' ? s.volatile() : s
}}

export const Config = Schema ? Schema.object({{
  endpointUrl: v(Schema.string().default('')).description('OpenViking 通信端点 URL (例如 https://vk.tide.red/mcp 或 http://127.0.0.1:1933/mcp)'),
  userKey: v(Schema.string().role('secret').default('')).description('所属用户 API Key / User Key (在 HTTP Header 中安全传递，带密码遮罩)'),
  userKeyEnv: v(Schema.string().default('OPENVIKING_USER_KEY')).description('从 DSH 凭据库 (.credentials.yaml) 或环境变量中引用的 Key 变量名'),
  userId: v(Schema.string().default('default')).description('租户 / 账户身份标识 (默认 default)'),
  enableMcp: v(Schema.boolean().default(true)).description('是否挂载 FastMCP 工具箱'),
  peer: v(Schema.string().default('{info["id"]}')).description('调用方节点标识 (用于服务端审计日志与调用链追踪)')
}}).description('{title} 通信桥梁配置') : undefined

function log(msg) {{
  try {{
    const home = process.env.USERPROFILE || process.env.HOME || 'C:\\\\Users\\\\Skl'
    const logPath = resolve(home, '.dsh', '{pkg_name}-hook.log')
    const line = `[${{new Date().toISOString()}}] ${{msg}}\\n`
    appendFileSync(logPath, line, 'utf8')
  }} catch (_) {{}}
}}

function getVal(v, fallback = '') {{
  if (v === undefined || v === null) return fallback
  if (typeof v?.get === 'function') {{
    const val = v.get()
    return (val !== undefined && val !== null && val !== '') ? String(val).trim() : fallback
  }}
  if (typeof v === 'string') {{
    const trimmed = v.trim()
    return trimmed !== '' ? trimmed : fallback
  }}
  return v
}}

export function apply(ctx, config = {{}}) {{
  const getEndpoint = () => getVal(config.endpointUrl, '')
  const getMcpBaseUrl = () => {{
    let ep = getEndpoint().trim()
    if (!ep) return ''
    if (!ep.endsWith('/mcp')) ep = `${{ep.replace(/\\/+$/, '')}}/mcp`
    return ep
  }}
  const getKey = () => {{
    const raw = getVal(config.userKey, '')
    if (raw) return raw
    const envNames = [getVal(config.userKeyEnv, 'OPENVIKING_USER_KEY'), 'OPENVIKING_USER_KEY', 'OPENVIKING_API_KEY']
    for (const name of envNames) {{
      if (name && process.env[name]) return process.env[name]
    }}
    return ''
  }}
  const getPeer = () => getVal(config.peer, '{info["id"]}')
  const getUserId = () => getVal(config.userId, 'default')
  const getEnableMcp = () => getVal(config.enableMcp, true) !== false

  log(`[INIT] {pkg_name} activated (peer=${{getPeer()}}, endpoint=${{getEndpoint()}})`)

  let currentMcpFork = null
  let lastMcpSignature = ''

  async function mountMcpIfNeeded() {{
    const enableMcp = getEnableMcp()
    const mcpBase = getMcpBaseUrl()
    if (!enableMcp || !mcpBase) {{
      if (currentMcpFork) {{
        try {{ currentMcpFork.dispose() }} catch (_) {{}}
        currentMcpFork = null
        lastMcpSignature = ''
      }}
      return
    }}

    try {{
      const key = getKey()
      const mcpUrl = `${{mcpBase}}?plugin_id={plugin_id}`
      const signature = `${{mcpUrl}}#${{key || 'nokey'}}`

      if (currentMcpFork && signature === lastMcpSignature) return
      if (currentMcpFork) {{
        try {{ currentMcpFork.dispose() }} catch (_) {{}}
        currentMcpFork = null
      }}

      const proxyPath = fileURLToPath(new URL('./servers/mcp-proxy.mjs', import.meta.url))
      log(`[MCP_MOUNT] mounting stdio proxy (${{proxyPath}}) targeting ${{mcpUrl}}`)

      let mcpPlugin = null
      try {{
        const mod = await import('@deepseek-ai/dsh-mcp-client')
        mcpPlugin = mod?.default || mod
      }} catch (_) {{
        if (typeof ctx.loader?.resolve === 'function') {{
          try {{ mcpPlugin = ctx.loader.resolve('@deepseek-ai/dsh-mcp-client') }} catch (_) {{}}
        }}
      }}

      if (mcpPlugin && typeof ctx.plugin === 'function') {{
        const homeDir = process.env.USERPROFILE || process.env.HOME || 'C:\\\\Users\\\\Skl'
        const childEnv = {{
          ...process.env,
          ELECTRON_RUN_AS_NODE: '1',
          OPENVIKING_URL: mcpBase,
          OPENVIKING_MCP_URL: mcpUrl,
          OPENVIKING_PEER_ID: getPeer(),
          OV_TARGET_PLUGIN: '{plugin_id}',
          OV_DEBUG_LOG: resolve(homeDir, '.dsh', '{pkg_name}-proxy.log')
        }}
        if (key) childEnv.OPENVIKING_API_KEY = key

        currentMcpFork = ctx.plugin(mcpPlugin, {{
          serverName: '{plugin_id}',
          transport: 'stdio',
          command: process.execPath,
          args: [proxyPath],
          env: childEnv,
          toolCallTimeoutMs: 60000,
          failOnStartupError: false,
          reconnect: {{ enabled: true, initialDelayMs: 500, maxDelayMs: 15000, maxAttempts: 10 }}
        }})
        lastMcpSignature = signature
        log(`[MCP_MOUNT_SUCCESS] {pkg_name} mounted successfully`)
      }}
    }} catch (err) {{
      log(`[MCP_MOUNT_WARN] failed to mount: ${{err?.message || err}}`)
    }}
  }}

  mountMcpIfNeeded().catch(() => {{}})
  ctx.on('loader/volatile-update', () => {{
    log('[VOLATILE_UPDATE] reloading dynamic config')
    mountMcpIfNeeded().catch(() => {{}})
  }})

  // 专属认知导轨上下文注入
  if (ctx.systemPrompt) {{
    try {{
      ctx.systemPrompt.context({{
        name: '{plugin_id}-routing-guide',
        order: 15,
        text: () => [
          '【{title} 导轨】',
          '当前已接入 {title} ({plugin_id})。',
          '{info["desc"]}',
          '请直接基于授权工具与 Hook 开展工作，开箱即用。'
        ].join('\\n')
      }})
    }} catch (_) {{}}
  }}
}}

apply.inject = ['systemPrompt', 'tools']
"""


# =========================================================================
# 2. KeePass 本地私有保险箱插件补齐 (dsh-plugin-keepass-vault)
# =========================================================================
def patch_keepass_plugin():
    kp_dir = BASE_DIR / "dsh-plugin-keepass-vault"
    kp_dir.mkdir(parents=True, exist_ok=True)

    # 1. package.json (补齐 dsh.bundle 声明)
    pkg = {
        "name": "dsh-plugin-keepass-vault",
        "version": "1.0.2",
        "type": "module",
        "main": "index.js",
        "description": "KeePass Vault 本地私有化凭据插件 (客户端本地挂载 KDBX + 查库第一公理 + 零云端依赖)",
        "keywords": ["deepseek-harness", "dsh-plugin", "cordis", "keepass", "vault", "credentials", "mcp"],
        "exports": {
            ".": "./index.js",
            "./client": "./client.js",
        },
        "files": ["index.js", "client.js", "schema.js", "cordis.patch.yml", "README.md"],
        "dsh": {
            "bundle": {
                "patch": "./cordis.patch.yml",
            },
            "client": {
                "platform": "web",
                "immediately": True,
                "inject": [
                    "@deepseek-ai/dsh-client-ui-plugin-manager",
                    "@deepseek-ai/dsh-client-ui-conversation",
                ],
            },
        },
        "peerDependencies": {
            "@deepseek-ai/cordis": "*",
            "@deepseek-ai/schemastery": "*",
        },
        "peerDependenciesMeta": {
            "@deepseek-ai/cordis": {"optional": True},
            "@deepseek-ai/schemastery": {"optional": True},
        },
    }
    (kp_dir / "package.json").write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 2. cordis.patch.yml
    patch_yml = """# KeePass Vault Bundle Patch for DeepSeek Harness (DSH)
# 本地私有运行，无需云端依赖
- insert:
    - id: keepass-vault
      name: dsh-plugin-keepass-vault
      config:
        kdbxPath: "~/.openviking/vault.kdbx"
        passwordEnv: "KEEPASS_VAULT_PASSWORD"
        masterKey: ""
        autoSnapshot: true
"""
    (kp_dir / "cordis.patch.yml").write_text(patch_yml, encoding="utf-8")

    # 3. client.js (带标准 slots 注册)
    client_js = """/**
 * client.js - KeePass 本地凭据保险箱 DSH Client Cockpit Plugin
 * 纯原生 React (由 DSH 宿主环境提供注入)，本地私有化凭据配置与验证面板。
 */

window.__ModuleLoader__.load({
  id: 'dsh-plugin-keepass-vault',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState, useEffect } = React;

    const STORAGE_KEY = 'dsh_plugin_keepass_vault_config';

    function loadSavedConfig() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      } catch (_) {}
      return {
        kdbxPath: 'C:\\\\Users\\\\Skl\\\\.openviking\\\\vault.kdbx',
        masterKey: '',
        passwordEnv: 'KEEPASS_VAULT_PASSWORD',
        autoSnapshot: true,
      };
    }

    function saveConfig(cfg) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg)); } catch (_) {}
    }

    function KeePassVaultConfigPanel(props) {
      const [config, setConfig] = useState(loadSavedConfig);
      const [showKey, setShowKey] = useState(false);
      const [saveToast, setSaveToast] = useState(null);

      const handleChange = (field, value) => {
        setConfig((prev) => ({ ...prev, [field]: value }));
      };

      const handleSave = () => {
        saveConfig(config);
        setSaveToast({ ok: true, msg: 'KeePass 本地配置已保存，客户端插件将使用此路径与凭据' });
        setTimeout(() => setSaveToast(null), 3500);
      };

      return h('div', {
        style: {
          padding: '16px',
          background: 'var(--dsw-alias-bg-l1, #ffffff)',
          color: 'var(--dsw-alias-text-primary, #0f1115)',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          fontSize: '12px',
          borderRadius: '8px',
          border: '1px solid var(--dsw-alias-border-l1, rgba(0,0,0,0.08))',
          margin: '8px 0',
        }
      },
        h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(0,0,0,0.08)', paddingBottom: '10px' } },
          h('span', { style: { fontSize: '18px' } }, '🔐'),
          h('div', null,
            h('div', { style: { fontWeight: '600', fontSize: '13px' } }, 'KeePass 本地私有凭据保险箱'),
            h('div', { style: { fontSize: '11px', color: '#64748b' } }, '纯客户端本地运行 · 零云端依赖 · 查库第一公理')
          )
        ),
        h('div', { style: { marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' } },
          h('div', null,
            h('label', { style: { display: 'block', marginBottom: '4px', fontWeight: '500' } }, 'KeePass 数据库绝对路径 (.kdbx):'),
            h('input', {
              type: 'text',
              value: config.kdbxPath,
              onChange: (e) => handleChange('kdbxPath', e.target.value),
              placeholder: '例如 C:\\Users\\Skl\\.openviking\\vault.kdbx',
              style: { width: '100%', boxSizing: 'border-box', padding: '6px 8px', fontSize: '12px', fontFamily: 'monospace', borderRadius: '6px', border: '1px solid rgba(0,0,0,0.15)', background: 'rgba(0,0,0,0.02)' },
            })
          ),
          h('div', null,
            h('label', { style: { display: 'block', marginBottom: '4px', fontWeight: '500' } }, '数据库主密码 (Master Password):'),
            h('div', { style: { display: 'flex', gap: '6px' } },
              h('input', {
                type: showKey ? 'text' : 'password',
                value: config.masterKey,
                onChange: (e) => handleChange('masterKey', e.target.value),
                placeholder: '留空则自动读取环境变量 KEEPASS_VAULT_PASSWORD',
                style: { flex: 1, boxSizing: 'border-box', padding: '6px 8px', fontSize: '12px', fontFamily: 'monospace', borderRadius: '6px', border: '1px solid rgba(0,0,0,0.15)', background: 'rgba(0,0,0,0.02)' },
              }),
              h('button', {
                type: 'button',
                onClick: () => setShowKey(!showKey),
                style: { padding: '0 10px', borderRadius: '6px', border: '1px solid rgba(0,0,0,0.15)', background: 'rgba(0,0,0,0.04)', fontSize: '12px', cursor: 'pointer' },
              }, showKey ? '隐藏' : '显示')
            )
          )
        ),
        h('div', { style: { marginTop: '14px', display: 'flex', justifyContent: 'flex-end', gap: '8px' } },
          h('button', {
            type: 'button',
            onClick: handleSave,
            style: {
              background: '#0891b2',
              color: '#ffffff',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              fontWeight: '600',
              fontSize: '12px',
              cursor: 'pointer',
            },
          }, '💾 保存配置')
        ),
        saveToast
          ? h('div', {
              style: {
                marginTop: '10px',
                padding: '8px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                background: 'rgba(6, 182, 212, 0.1)',
                border: '1px solid #0891b2',
                color: '#0891b2',
              },
            }, saveToast.msg)
          : null
      );
    }

    function apply(ctx) {
      ctx.slots.inject('plugins.bundle.config', () =>
        ctx.slots.register(
            {
              name: 'plugins.bundle.config',
              key: 'dsh-plugin-keepass-vault',
            },
            KeePassVaultConfigPanel
        )
      );
    }

    return {
      inject: ['slots'],
      apply,
    };
  },
});
"""
    (kp_dir / "client.js").write_text(client_js, encoding="utf-8")
    print("Successfully patched dsh-plugin-keepass-vault bundle metadata and slots client.js")


# =========================================================================
# 3. Dify 独立桥接器生成 (dsh-plugin-dify)
# =========================================================================
def generate_dify_plugin():
    dify_dir = BASE_DIR / "dsh-plugin-dify"
    dify_dir.mkdir(parents=True, exist_ok=True)

    pkg = {
        "name": "dsh-plugin-dify",
        "version": "1.0.1",
        "type": "module",
        "main": "index.js",
        "description": "Dify 智能体与工作流中枢 DSH 独立桥接器 (支持工作流唤起、Agent 协同与知识库检索)",
        "keywords": ["deepseek-harness", "dsh-plugin", "cordis", "dify", "workflow"],
        "exports": {
            ".": "./index.js",
            "./client": "./client.js",
        },
        "files": ["index.js", "client.js", "schema.js", "cordis.patch.yml", "README.md"],
        "dsh": {
            "bundle": {
                "patch": "./cordis.patch.yml",
            },
            "client": {
                "platform": "web",
                "immediately": True,
                "inject": [
                    "@deepseek-ai/dsh-client-ui-plugin-manager",
                    "@deepseek-ai/dsh-client-ui-conversation",
                ],
            },
        },
        "peerDependencies": {
            "@deepseek-ai/cordis": "*",
            "@deepseek-ai/schemastery": "*",
        },
        "peerDependenciesMeta": {
            "@deepseek-ai/cordis": {"optional": True},
            "@deepseek-ai/schemastery": {"optional": True},
        },
    }
    (dify_dir / "package.json").write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    patch_yml = """# Dify 智能体与工作流中枢 Bundle Patch for DeepSeek Harness (DSH)
- insert:
    - id: dify
      name: dsh-plugin-dify
      config:
        apiUrl: "https://api.dify.ai/v1"
        apiKey: ""
        apiKeyEnv: "DIFY_API_KEY"
"""
    (dify_dir / "cordis.patch.yml").write_text(patch_yml, encoding="utf-8")

    client_js = """/**
 * client.js - Dify 智能体与工作流中枢 DSH Client Cockpit Plugin
 */
window.__ModuleLoader__.load({
  id: 'dsh-plugin-dify',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState } = React;

    const STORAGE_KEY = 'dsh_plugin_dify_config';

    function loadSavedConfig() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      } catch (_) {}
      return {
        apiUrl: 'https://api.dify.ai/v1',
        apiKey: '',
      };
    }

    function saveConfig(cfg) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg)); } catch (_) {}
    }

    function DifyConfigPanel() {
      const [config, setConfig] = useState(loadSavedConfig);
      const [showKey, setShowKey] = useState(false);
      const [testing, setTesting] = useState(false);
      const [probeMsg, setProbeMsg] = useState(null);
      const [saveToast, setSaveToast] = useState(null);

      const handleChange = (field, value) => {
        setConfig((prev) => ({ ...prev, [field]: value }));
      };

      const handleTest = async () => {
        setTesting(true);
        setProbeMsg(null);
        try {
          const res = await fetch(`${config.apiUrl.replace(/\\/+$/, '')}/parameters`, {
            headers: {
              'Authorization': `Bearer ${config.apiKey}`,
              'Content-Type': 'application/json',
            },
            signal: AbortSignal.timeout(5000),
          });
          if (res.ok || res.status === 200) {
            setProbeMsg({ ok: true, msg: '✅ Dify 接口连接成功 · API Key 验证有效' });
          } else {
            setProbeMsg({ ok: false, msg: `❌ 连接返回 HTTP ${res.status} (${res.statusText || '鉴权失败'})` });
          }
        } catch (err) {
          setProbeMsg({ ok: false, msg: `❌ 连接超时或网络不可达: ${err.message}` });
        } finally {
          setTesting(false);
        }
      };

      const handleSave = () => {
        saveConfig(config);
        setSaveToast({ ok: true, msg: 'Dify 配置已保存成功' });
        setTimeout(() => setSaveToast(null), 3000);
      };

      return h('div', {
        style: {
          padding: '16px',
          background: 'var(--dsw-alias-bg-l1, #ffffff)',
          color: 'var(--dsw-alias-text-primary, #0f1115)',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          fontSize: '12px',
          borderRadius: '8px',
          border: '1px solid rgba(0,0,0,0.08)',
          margin: '8px 0',
        }
      },
        h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(0,0,0,0.08)', paddingBottom: '10px' } },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
            h('span', { style: { fontSize: '18px' } }, '🤖'),
            h('div', null,
              h('div', { style: { fontWeight: '600', fontSize: '13px' } }, 'Dify 智能体与工作流中枢'),
              h('div', { style: { fontSize: '11px', color: '#64748b' } }, 'dsh-plugin-dify · 专属独立桥接器')
            )
          ),
          h('button', {
            type: 'button',
            onClick: handleTest,
            disabled: testing,
            style: {
              background: '#0891b2',
              color: '#ffffff',
              border: 'none',
              padding: '4px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              cursor: testing ? 'not-allowed' : 'pointer',
            },
          }, testing ? '测试中...' : '⚡ 连通性测试')
        ),
        probeMsg
          ? h('div', {
              style: {
                margin: '10px 0',
                padding: '8px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                background: probeMsg.ok ? 'rgba(6, 182, 212, 0.08)' : 'rgba(244, 63, 94, 0.08)',
                border: `1px solid ${probeMsg.ok ? '#0891b2' : '#e11d48'}`,
                color: probeMsg.ok ? '#0891b2' : '#e11d48',
              },
            }, probeMsg.msg)
          : null,
        h('div', { style: { marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' } },
          h('div', null,
            h('label', { style: { display: 'block', marginBottom: '4px', fontWeight: '500' } }, 'Dify 访问接口地址:'),
            h('input', {
              type: 'text',
              value: config.apiUrl,
              onChange: (e) => handleChange('apiUrl', e.target.value),
              placeholder: '例如 https://api.dify.ai/v1 或自建地址 http://127.0.0.1/v1',
              style: { width: '100%', boxSizing: 'border-box', padding: '6px 8px', fontSize: '12px', fontFamily: 'monospace', borderRadius: '6px', border: '1px solid rgba(0,0,0,0.15)', background: 'rgba(0,0,0,0.02)' },
            })
          ),
          h('div', null,
            h('label', { style: { display: 'block', marginBottom: '4px', fontWeight: '500' } }, 'Dify API 密钥 (API Key):'),
            h('div', { style: { display: 'flex', gap: '6px' } },
              h('input', {
                type: showKey ? 'text' : 'password',
                value: config.apiKey,
                onChange: (e) => handleChange('apiKey', e.target.value),
                placeholder: '填入从 Dify 控制台获取的 API 密钥 (app-xxx)',
                style: { flex: 1, boxSizing: 'border-box', padding: '6px 8px', fontSize: '12px', fontFamily: 'monospace', borderRadius: '6px', border: '1px solid rgba(0,0,0,0.15)', background: 'rgba(0,0,0,0.02)' },
              }),
              h('button', {
                type: 'button',
                onClick: () => setShowKey(!showKey),
                style: { padding: '0 10px', borderRadius: '6px', border: '1px solid rgba(0,0,0,0.15)', background: 'rgba(0,0,0,0.04)', fontSize: '12px', cursor: 'pointer' },
              }, showKey ? '隐藏' : '显示')
            )
          )
        ),
        h('div', { style: { marginTop: '14px', display: 'flex', justifyContent: 'flex-end', gap: '8px' } },
          h('button', {
            type: 'button',
            onClick: handleSave,
            style: {
              background: '#0891b2',
              color: '#ffffff',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              fontWeight: '600',
              fontSize: '12px',
              cursor: 'pointer',
            },
          }, '💾 保存配置')
        ),
        saveToast
          ? h('div', {
              style: {
                marginTop: '10px',
                padding: '8px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                background: 'rgba(6, 182, 212, 0.1)',
                border: '1px solid #0891b2',
                color: '#0891b2',
              },
            }, saveToast.msg)
          : null
      );
    }

    function apply(ctx) {
      ctx.slots.inject('plugins.bundle.config', () =>
        ctx.slots.register(
            {
              name: 'plugins.bundle.config',
              key: 'dsh-plugin-dify',
            },
            DifyConfigPanel
        )
      );
    }

    return {
      inject: ['slots'],
      apply,
    };
  },
});
"""
    (dify_dir / "client.js").write_text(client_js, encoding="utf-8")

    index_js = """/**
 * dsh-plugin-dify
 * Dify 智能体与工作流中枢 DSH 独立桥接器。
 */
export const name = 'dsh-plugin-dify'
export const inject = ['agents', 'tools', 'systemPrompt']

export function apply(ctx, config = {}) {
  // 注入 Dify 专属工作流导轨
  if (ctx.systemPrompt) {
    try {
      ctx.systemPrompt.context({
        name: 'dify-workflow-guide',
        order: 20,
        text: () => '【Dify 工作流导轨】已接入 Dify 智能体中枢，可通过 API 直通工作流与知识库。'
      })
    } catch (_) {}
  }
}
"""
    (dify_dir / "index.js").write_text(index_js, encoding="utf-8")
    (dify_dir / "schema.js").write_text("export default null;\n", encoding="utf-8")
    (dify_dir / "README.md").write_text("# dsh-plugin-dify\nDify 智能体与工作流中枢 DSH 独立桥接器\n", encoding="utf-8")
    print("Successfully generated dsh-plugin-dify independent package")


# =========================================================================
# 4. CPA 算力协同独立桥接器生成 (dsh-plugin-cpa)
# =========================================================================
def generate_cpa_plugin():
    cpa_dir = BASE_DIR / "dsh-plugin-cpa"
    cpa_dir.mkdir(parents=True, exist_ok=True)

    pkg = {
        "name": "dsh-plugin-cpa",
        "version": "1.0.1",
        "type": "module",
        "main": "index.js",
        "description": "CPA 跨模型算力协同中枢 DSH 独立桥接器 (支持多模型聚合分摊与 2080Ti 算力集群调度)",
        "keywords": ["deepseek-harness", "dsh-plugin", "cordis", "cpa", "compute"],
        "exports": {
            ".": "./index.js",
            "./client": "./client.js",
        },
        "files": ["index.js", "client.js", "schema.js", "cordis.patch.yml", "README.md"],
        "dsh": {
            "bundle": {
                "patch": "./cordis.patch.yml",
            },
            "client": {
                "platform": "web",
                "immediately": True,
                "inject": [
                    "@deepseek-ai/dsh-client-ui-plugin-manager",
                    "@deepseek-ai/dsh-client-ui-conversation",
                ],
            },
        },
        "peerDependencies": {
            "@deepseek-ai/cordis": "*",
            "@deepseek-ai/schemastery": "*",
        },
        "peerDependenciesMeta": {
            "@deepseek-ai/cordis": {"optional": True},
            "@deepseek-ai/schemastery": {"optional": True},
        },
    }
    (cpa_dir / "package.json").write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    patch_yml = """# CPA 跨模型算力协同中枢 Bundle Patch for DeepSeek Harness (DSH)
- insert:
    - id: cpa-squad
      name: dsh-plugin-cpa
      config:
        apiUrl: "http://localhost:8317/v1"
        apiKey: "sk-cpa-master-2026"
"""
    (cpa_dir / "cordis.patch.yml").write_text(patch_yml, encoding="utf-8")

    client_js = """/**
 * client.js - CPA 跨模型算力协同中枢 DSH Client Cockpit Plugin
 */
window.__ModuleLoader__.load({
  id: 'dsh-plugin-cpa',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState } = React;

    const STORAGE_KEY = 'dsh_plugin_cpa_config';

    function loadSavedConfig() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      } catch (_) {}
      return {
        apiUrl: 'http://localhost:8317/v1',
        apiKey: 'sk-cpa-master-2026',
      };
    }

    function saveConfig(cfg) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg)); } catch (_) {}
    }

    function CpaConfigPanel() {
      const [config, setConfig] = useState(loadSavedConfig);
      const [showKey, setShowKey] = useState(false);
      const [testing, setTesting] = useState(false);
      const [probeMsg, setProbeMsg] = useState(null);
      const [saveToast, setSaveToast] = useState(null);

      const handleChange = (field, value) => {
        setConfig((prev) => ({ ...prev, [field]: value }));
      };

      const handleTest = async () => {
        setTesting(true);
        setProbeMsg(null);
        try {
          const res = await fetch(`${config.apiUrl.replace(/\\/+$/, '')}/models`, {
            headers: {
              'Authorization': `Bearer ${config.apiKey}`,
              'Content-Type': 'application/json',
            },
            signal: AbortSignal.timeout(5000),
          });
          if (res.ok) {
            const data = await res.json();
            const count = data.data?.length || 0;
            setProbeMsg({ ok: true, msg: `✅ CPA 算力集群连接正常 · 已发现 ${count} 个多模型算力节点` });
          } else {
            setProbeMsg({ ok: false, msg: `❌ 连接返回 HTTP ${res.status}` });
          }
        } catch (err) {
          setProbeMsg({ ok: false, msg: `❌ 算力中枢离线或地址不可达: ${err.message}` });
        } finally {
          setTesting(false);
        }
      };

      const handleSave = () => {
        saveConfig(config);
        setSaveToast({ ok: true, msg: 'CPA 算力协同配置已保存成功' });
        setTimeout(() => setSaveToast(null), 3000);
      };

      return h('div', {
        style: {
          padding: '16px',
          background: 'var(--dsw-alias-bg-l1, #ffffff)',
          color: 'var(--dsw-alias-text-primary, #0f1115)',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          fontSize: '12px',
          borderRadius: '8px',
          border: '1px solid rgba(0,0,0,0.08)',
          margin: '8px 0',
        }
      },
        h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(0,0,0,0.08)', paddingBottom: '10px' } },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
            h('span', { style: { fontSize: '18px' } }, '⚡'),
            h('div', null,
              h('div', { style: { fontWeight: '600', fontSize: '13px' } }, 'CPA 跨模型算力协同中枢'),
              h('div', { style: { fontSize: '11px', color: '#64748b' } }, 'dsh-plugin-cpa · 专属独立桥接器')
            )
          ),
          h('button', {
            type: 'button',
            onClick: handleTest,
            disabled: testing,
            style: {
              background: '#0891b2',
              color: '#ffffff',
              border: 'none',
              padding: '4px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              cursor: testing ? 'not-allowed' : 'pointer',
            },
          }, testing ? '测试中...' : '⚡ 算力探测')
        ),
        probeMsg
          ? h('div', {
              style: {
                margin: '10px 0',
                padding: '8px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                background: probeMsg.ok ? 'rgba(6, 182, 212, 0.08)' : 'rgba(244, 63, 94, 0.08)',
                border: `1px solid ${probeMsg.ok ? '#0891b2' : '#e11d48'}`,
                color: probeMsg.ok ? '#0891b2' : '#e11d48',
              },
            }, probeMsg.msg)
          : null,
        h('div', { style: { marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' } },
          h('div', null,
            h('label', { style: { display: 'block', marginBottom: '4px', fontWeight: '500' } }, 'CPA 算力端点接口地址:'),
            h('input', {
              type: 'text',
              value: config.apiUrl,
              onChange: (e) => handleChange('apiUrl', e.target.value),
              placeholder: '例如 http://localhost:8317/v1',
              style: { width: '100%', boxSizing: 'border-box', padding: '6px 8px', fontSize: '12px', fontFamily: 'monospace', borderRadius: '6px', border: '1px solid rgba(0,0,0,0.15)', background: 'rgba(0,0,0,0.02)' },
            })
          ),
          h('div', null,
            h('label', { style: { display: 'block', marginBottom: '4px', fontWeight: '500' } }, 'CPA API Key:'),
            h('div', { style: { display: 'flex', gap: '6px' } },
              h('input', {
                type: showKey ? 'text' : 'password',
                value: config.apiKey,
                onChange: (e) => handleChange('apiKey', e.target.value),
                placeholder: '填入 CPA 算力访问密钥',
                style: { flex: 1, boxSizing: 'border-box', padding: '6px 8px', fontSize: '12px', fontFamily: 'monospace', borderRadius: '6px', border: '1px solid rgba(0,0,0,0.15)', background: 'rgba(0,0,0,0.02)' },
              }),
              h('button', {
                type: 'button',
                onClick: () => setShowKey(!showKey),
                style: { padding: '0 10px', borderRadius: '6px', border: '1px solid rgba(0,0,0,0.15)', background: 'rgba(0,0,0,0.04)', fontSize: '12px', cursor: 'pointer' },
              }, showKey ? '隐藏' : '显示')
            )
          )
        ),
        h('div', { style: { marginTop: '14px', display: 'flex', justifyContent: 'flex-end', gap: '8px' } },
          h('button', {
            type: 'button',
            onClick: handleSave,
            style: {
              background: '#0891b2',
              color: '#ffffff',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              fontWeight: '600',
              fontSize: '12px',
              cursor: 'pointer',
            },
          }, '💾 保存配置')
        ),
        saveToast
          ? h('div', {
              style: {
                marginTop: '10px',
                padding: '8px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                background: 'rgba(6, 182, 212, 0.1)',
                border: '1px solid #0891b2',
                color: '#0891b2',
              },
            }, saveToast.msg)
          : null
      );
    }

    function apply(ctx) {
      ctx.slots.inject('plugins.bundle.config', () =>
        ctx.slots.register(
            {
              name: 'plugins.bundle.config',
              key: 'dsh-plugin-cpa',
            },
            CpaConfigPanel
        )
      );
    }

    return {
      inject: ['slots'],
      apply,
    };
  },
});
"""
    (cpa_dir / "client.js").write_text(client_js, encoding="utf-8")

    index_js = """/**
 * dsh-plugin-cpa
 * CPA 跨模型算力协同中枢 DSH 独立桥接器。
 */
export const name = 'dsh-plugin-cpa'
export const inject = ['agents', 'tools', 'systemPrompt']

export function apply(ctx, config = {}) {
  // 注入 CPA 算力导轨
  if (ctx.systemPrompt) {
    try {
      ctx.systemPrompt.context({
        name: 'cpa-squad-guide',
        order: 18,
        text: () => '【CPA 算力协同导轨】已接入 2080Ti CPA 多模型算力中枢，支持跨模型咨询与并发 Fanout。'
      })
    } catch (_) {}
  }
}
"""
    (cpa_dir / "index.js").write_text(index_js, encoding="utf-8")
    (cpa_dir / "schema.js").write_text("export default null;\n", encoding="utf-8")
    (cpa_dir / "README.md").write_text("# dsh-plugin-cpa\nCPA 跨模型算力协同中枢 DSH 独立桥接器\n", encoding="utf-8")
    print("Successfully generated dsh-plugin-cpa independent package")


def main():
    # 1. 生成原生 3 大插件
    for dir_name, info in NATIVE_PLUGINS.items():
        p_dir = BASE_DIR / dir_name
        p_dir.mkdir(parents=True, exist_ok=True)

        pkg = {
            "name": info["pkg_name"],
            "version": info["version"],
            "type": "module",
            "main": "index.js",
            "description": info["desc"],
            "keywords": ["deepseek-harness", "dsh-plugin", "cordis", "openviking", info["id"]],
            "exports": {
                ".": "./index.js",
                "./client": "./client.js",
            },
            "files": [
                "index.js",
                "client.js",
                "schema.js",
                "config.mjs",
                "mcp.mjs",
                "cordis.patch.yml",
                "README.md",
                "servers/",
                "shared/",
            ],
            "dsh": {
                "bundle": {
                    "patch": "./cordis.patch.yml",
                },
                "client": {
                    "platform": "web",
                    "immediately": True,
                    "inject": [
                        "@deepseek-ai/dsh-client-ui-plugin-manager",
                        "@deepseek-ai/dsh-client-ui-conversation",
                    ],
                },
            },
            "peerDependencies": {
                "@deepseek-ai/cordis": "*",
                "@deepseek-ai/schemastery": "*",
            },
            "peerDependenciesMeta": {
                "@deepseek-ai/cordis": {"optional": True},
                "@deepseek-ai/schemastery": {"optional": True},
            },
        }
        (p_dir / "package.json").write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        patch_yml = f"""# {info['title']} Bundle Patch for DeepSeek Harness (DSH)
# 遵循高内聚单包自包含规范，零侵入宿主配置，内部静默自治挂载
- insert:
    - id: {info['id']}
      name: {info['pkg_name']}
      config:
        endpointUrl: ""
        userKey: ""
        userKeyEnv: "OPENVIKING_USER_KEY"
        userId: "default"
        enableMcp: true
        peer: "{info['id']}"
"""
        (p_dir / "cordis.patch.yml").write_text(patch_yml, encoding="utf-8")

        readme = f"""# {info['title']} (`{info['pkg_name']}`)

{info['desc']}

## 接入要素
- 服务端端点: `{info['default_endpoint']}`
- 专属凭据: 用户 API Key (User Key)

## 安装方式
```bash
npm install https://vk.tide.red/studio/{info['pkg_name']}-{info['version']}.tgz
```
"""
        (p_dir / "README.md").write_text(readme, encoding="utf-8")
        (p_dir / "client.js").write_text(build_native_client_js(info), encoding="utf-8")
        (p_dir / "index.js").write_text(build_native_index_js(info), encoding="utf-8")

        print(f"Successfully generated full files for {dir_name}")

    # 2. 兼容别名包 dsh-plugin-openviking
    alias_dir = BASE_DIR / "dsh-plugin-openviking"
    mem_info = NATIVE_PLUGINS["dsh-plugin-openviking-memory"]
    (alias_dir / "client.js").write_text(build_native_client_js(mem_info), encoding="utf-8")
    (alias_dir / "cordis.patch.yml").write_text((BASE_DIR / "dsh-plugin-openviking-memory" / "cordis.patch.yml").read_text(encoding="utf-8"), encoding="utf-8")
    alias_pkg_path = alias_dir / "package.json"
    if alias_pkg_path.exists():
        alias_pkg_data = json.loads(alias_pkg_path.read_text(encoding="utf-8"))
        alias_pkg_data["version"] = mem_info["version"]
        alias_pkg_path.write_text(json.dumps(alias_pkg_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Synchronized compatibility alias dsh-plugin-openviking (version {mem_info['version']})")

    # 3. 补齐 KeePass 本地凭据插件
    patch_keepass_plugin()

    # 4. 生成 Dify 独立桥接器
    generate_dify_plugin()

    # 5. 生成 CPA 独立桥接器
    generate_cpa_plugin()

    print("\n🎉 All 7 DSH independent bridge packages successfully synchronized!")


if __name__ == "__main__":
    main()
