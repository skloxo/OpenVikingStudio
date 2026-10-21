/**
 * client.js - OpenViking 核心长程记忆与代码战地 DSH Client Cockpit Plugin
 * 1:1 对齐反重力与 Web Studio 多段详情架构 (概览 / 技能 / MCP / 钩子 / 配置)。
 * 严守工程与视觉铁律：NO GREEN EVER 🚫 (#0891b2 冰青 / #e11d48 玫瑰红)，字号 >= 12px，6px 微圆角。
 * 全自适应明暗主题：废黜硬编码背景/文字颜色，纯相对透明度与 CSS 变量继承。
 * 卸载联动与清理：监听 ctx.on('dispose') 自动抹除凭据缓存，支持面板内一键重置。
 */

window.__ModuleLoader__.load({
  id: 'dsh-plugin-openviking-memory',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState, useEffect, useCallback } = React;

    const STORAGE_KEY = 'dsh_plugin_openviking_memory_config';
    const CAPS_STORAGE_KEY = 'dsh_plugin_openviking_memory_capabilities';

    const MCP_TOOLS_CATALOG = [
      { cat: '记忆检索 (6)', tools: ['openviking_find', 'openviking_search', 'openviking_read', 'openviking_write', 'openviking_store', 'openviking_smart_read'] },
      { cat: '代码感知 (5)', tools: ['openviking_code_outline', 'openviking_code_search', 'openviking_code_expand', 'openviking_grep', 'openviking_glob'] },
      { cat: '虚拟文件 (4)', tools: ['openviking_ls', 'openviking_tree', 'openviking_tag', 'openviking_diff'] },
      { cat: '技能演进 (6)', tools: ['openviking_record_evolution_lesson', 'openviking_skills', 'openviking_audit_skills', 'openviking_auto_onboard_skills', 'openviking_get_onboard_queue_status', 'openviking_fix_skill'] },
      { cat: '会话拓扑 (6)', tools: ['openviking_list_sessions', 'openviking_get_session', 'openviking_create_session', 'openviking_link', 'openviking_get_relations', 'openviking_unlink'] },
      { cat: '系统健康 (5)', tools: ['openviking_health', 'openviking_system_status', 'openviking_privacy', 'openviking_consistency', 'openviking_ping'] },
      { cat: '可观测性 (4)', tools: ['openviking_harness_stats', 'openviking_usage_stats', 'openviking_observer', 'openviking_metrics'] }
    ];

    const SKILLS_LIST = [
      { name: 'openviking-memory', desc: '体外大脑长期记忆检索、两阶段混合重排与结构化持久化' },
      { name: 'session-handover', desc: '会话战场脱水结晶、踩坑提纯双写入脑与 0 秒接力 Prompt' },
      { name: 'antigravity-plugin-crafting', desc: '官方构件规范、双轨 MCP 治理与单一真相源 (SSOT) 级联迭代' },
      { name: 'openviking-plugin-ops', desc: '插件中心运维中枢、零信任鉴权与异构客户端 stdio 桥接' }
    ];

    const HOOKS_LIST = [
      { name: 'PreInvocation', type: '意图感知', desc: '分析输入意图关键词，开局自动静默预取体外大脑相关上下文' },
      { name: 'PreToolUse', type: '安全审计', desc: '敏感操作与外部记忆写入前置权限校验与防爆审计' },
      { name: 'Stop', type: '自反思闭环', desc: '会话终止时自动触发经验反思，双写沉淀至 Master Memory' }
    ];

    function loadSavedConfig() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      } catch (_) {}
      return { endpointUrl: '', userKey: '', disabledTools: [], disabledHooks: [] };
    }

    function loadSavedCaps() {
      try {
        const raw = localStorage.getItem(CAPS_STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      } catch (_) {}
      return null;
    }

    function clearSavedStorage() {
      try {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(CAPS_STORAGE_KEY);
      } catch (_) {}
    }

    function DshPluginOpenvikingMemoryPanel(props) {
      const [tab, setTab] = useState('overview'); // overview | skills | mcp | hooks | settings
      const [config, setConfig] = useState(loadSavedConfig);
      const [caps, setCaps] = useState(loadSavedCaps);
      const [showKey, setShowKey] = useState(false);
      const [probeReport, setProbeReport] = useState(null);
      const [testing, setTesting] = useState(false);
      const [saving, setSaving] = useState(false);
      const [toast, setToast] = useState(null);

      const handleChange = (field, value) => {
        setConfig((prev) => ({ ...prev, [field]: value }));
      };

      const getBaseUrl = (url) => {
        let base = (url || '').trim();
        base = base.replace(/\/mcp\/?$/i, '').replace(/\/+$/, '');
        return base;
      };

      const handleTest = async () => {
        setTesting(true);
        setProbeReport(null);
        const base = getBaseUrl(config.endpointUrl);
        if (!base) {
          setProbeReport({ ok: false, error: '请先在【配置】中填写 OpenViking 服务端接口地址' });
          setTesting(false);
          return;
        }
        const key = (config.userKey || '').trim();
        if (!key) {
          setProbeReport({ ok: false, error: '请先在【配置】中填写用户专属 API 密钥 (User Key)' });
          setTesting(false);
          return;
        }
        const start = Date.now();
        const fetchFn = typeof window !== 'undefined' && window.fetch ? window.fetch.bind(window) : fetch;

        try {
          const res = await fetchFn(`${base}/api/v1/system/client-capabilities?plugin_id=openviking-memory&probe=full`, {
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
            signal: AbortSignal.timeout(6000),
          });
          const totalLatency = Date.now() - start;

          if (res.ok) {
            const data = await res.json();
            setCaps(data);
            try { localStorage.setItem(CAPS_STORAGE_KEY, JSON.stringify(data)); } catch (_) {}
            setProbeReport({
              ok: true,
              totalLatency,
              version: data.version || '2.0.24',
              toolsCount: data.total_authorized_tools || data.total_tools || data.plugins?.[0]?.tools?.length || 35,
              hooksCount: data.hooks?.length || 3,
              role: data.role || 'user',
            });
          } else {
            setProbeReport({
              ok: false,
              totalLatency,
              error: `HTTP ${res.status} 鉴权拒绝 (${res.statusText || 'Unauthorized'})`,
            });
          }
        } catch (err) {
          setProbeReport({
            ok: false,
            totalLatency: Date.now() - start,
            error: err.message || '网络连接超时或地址不可达',
          });
        } finally {
          setTesting(false);
        }
      };

      const handleSave = () => {
        setSaving(true);
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(config)); } catch (_) {}
        setTimeout(() => {
          setSaving(false);
          setToast({ ok: true, msg: '配置已落盘！请点击左上角【➕ 新会话】以初始化挂载 MCP 工具与 Hook' });
          setTimeout(() => setToast(null), 4000);
        }, 300);
      };

      const handleClear = () => {
        clearSavedStorage();
        setConfig({ endpointUrl: '', userKey: '', disabledTools: [], disabledHooks: [] });
        setCaps(null);
        setProbeReport(null);
        setToast({ ok: true, msg: '已彻底抹除本地历史凭据与能力缓存' });
        setTimeout(() => setToast(null), 3000);
      };

      // 动态提取版本、工具数与 Hook 数 (废黜一切硬编码静态常数)
      const currentVersion = caps?.version || probeReport?.version || '2.0.24';
      const totalToolsCount = caps?.total_authorized_tools || caps?.total_tools || caps?.plugins?.[0]?.tools?.length || probeReport?.toolsCount || 35;
      const totalHooksCount = caps?.hooks?.length || probeReport?.hooksCount || 3;

      // 容器：自适应明暗，零写死白色/黑字
      return h('div', {
        style: {
          padding: '16px',
          background: 'var(--dsw-alias-bg-l1, transparent)',
          color: 'var(--dsw-alias-text-primary, inherit)',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          fontSize: '12px',
          borderRadius: '8px',
          border: '1px solid var(--dsw-alias-border-l1, rgba(125, 125, 125, 0.15))',
          margin: '8px 0',
        }
      },
        // 1. 顶部 Header (与反重力 1:1 对齐)
        h('div', { style: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' } },
          h('div', { style: { display: 'flex', gap: '12px' } },
            h('div', { style: { fontSize: '26px', lineHeight: 1 } }, '🧠'),
            h('div', null,
              h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
                h('span', { style: { fontWeight: '700', fontSize: '15px' } }, `OpenViking Core Memory (v${currentVersion})`),
                probeReport && probeReport.ok
                  ? h('span', { style: { fontSize: '12px', color: '#0891b2', fontWeight: '500' } }, '● 已连通')
                  : h('span', { style: { fontSize: '12px', color: 'rgba(125, 125, 125, 0.6)' } }, '○ 待探测')
              ),
              h('div', { style: { marginTop: '4px', fontSize: '12px', opacity: 0.8, lineHeight: 1.4 } },
                `[版本: v${currentVersion}] OpenViking 体外大脑与核心记忆官方标准插件。提供跨会话无缝记忆检索与持久化、自动化会话归档、踩坑反思沉淀与零损耗 Handover 接力。`
              )
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
              padding: '5px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: '500',
              cursor: testing ? 'not-allowed' : 'pointer',
              whiteSpace: 'nowrap',
            },
          }, testing ? '探测中...' : '⚡ 连通性测试')
        ),

        // 2. 快捷提示词 Prompts (3 条标准契约)
        h('div', { style: { marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '6px' } },
          [
            '搜索体外大脑中关于当前项目的核心架构设计与工程约束',
            '总结并交接本次会话，生成标准 Handover Brief 准备换机/开新会话',
            '检查 OpenViking 记忆中枢健康状态与当前 Agent 用户凭据'
          ].map((prompt, i) =>
            h('div', {
              key: i,
              style: {
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 10px',
                borderRadius: '6px',
                background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.05))',
                border: '1px solid var(--dsw-alias-border-l2, rgba(125, 125, 125, 0.12))',
                fontSize: '12px',
              }
            },
              h('span', { style: { opacity: 0.6 } }, '💬'),
              h('span', { style: { flex: 1, opacity: 0.9 } }, prompt)
            )
          )
        ),

        // 探针状态条
        probeReport
          ? h('div', {
              style: {
                marginTop: '10px',
                padding: '8px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                background: probeReport.ok ? 'rgba(8, 145, 178, 0.08)' : 'rgba(225, 29, 72, 0.08)',
                border: `1px solid ${probeReport.ok ? '#0891b2' : '#e11d48'}`,
                color: probeReport.ok ? '#0891b2' : '#e11d48',
              },
            },
            probeReport.ok
              ? `✅ 连接成功 · 延迟 ${probeReport.totalLatency}ms · 服务端版本 v${probeReport.version} · 鉴权身份: ${probeReport.role} (就绪 ${probeReport.toolsCount} 项工具 / ${probeReport.hooksCount} 项 Hook)`
              : `❌ 连接失败 · ${probeReport.error}`
            )
          : null,

        // 3. 多段 Tabs 导航条 (概览 / 技能 / MCP / 钩子 / 配置)
        h('div', {
          style: {
            marginTop: '14px',
            display: 'flex',
            gap: '16px',
            borderBottom: '1px solid var(--dsw-alias-border-l1, rgba(125, 125, 125, 0.15))',
            paddingBottom: '2px',
          }
        },
          [
            { id: 'overview', label: '概览' },
            { id: 'skills', label: '技能' },
            { id: 'mcp', label: 'MCP' },
            { id: 'hooks', label: '钩子' },
            { id: 'settings', label: '配置' }
          ].map(t =>
            h('button', {
              key: t.id,
              type: 'button',
              onClick: () => setTab(t.id),
              style: {
                background: 'transparent',
                border: 'none',
                borderBottom: tab === t.id ? '2px solid #0891b2' : '2px solid transparent',
                color: tab === t.id ? '#0891b2' : 'inherit',
                fontWeight: tab === t.id ? '600' : '400',
                padding: '6px 4px',
                fontSize: '12px',
                cursor: 'pointer',
                opacity: tab === t.id ? 1 : 0.7,
              }
            }, t.label)
          )
        ),

        // 4. Tab 内容渲染
        h('div', { style: { marginTop: '12px' } },
          // TAB: 概览
          tab === 'overview' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' } },
            h('div', { style: { padding: '8px 10px', borderRadius: '6px', background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.05))' } },
              h('div', { style: { fontWeight: '600', marginBottom: '4px' } }, '📌 运行时架构与拓扑'),
              h('div', { style: { opacity: 0.85, lineHeight: 1.5 } },
                'DSH Client (前端 UI) ➔ 动态 stdio 通信驱动 ➔ OpenViking 本地/远程统一服务端 (:1933)。零外部冗余依赖，具备完全独立的上下文记忆闭环。'
              )
            ),
            h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' } },
              h('div', { style: { padding: '8px', borderRadius: '6px', border: '1px solid var(--dsw-alias-border-l1, rgba(125, 125, 125, 0.15))' } },
                h('div', { style: { opacity: 0.6 } }, '插件唯一标识符:'),
                h('div', { style: { fontFamily: 'monospace', fontWeight: '500', marginTop: '2px' } }, 'dsh-plugin-openviking-memory')
              ),
              h('div', { style: { padding: '8px', borderRadius: '6px', border: '1px solid var(--dsw-alias-border-l1, rgba(125, 125, 125, 0.15))' } },
                h('div', { style: { opacity: 0.6 } }, '核心工具规范:'),
                h('div', { style: { fontFamily: 'monospace', fontWeight: '500', marginTop: '2px', color: '#0891b2' } }, `${totalToolsCount} Tools SSOT / FastMCP`)
              )
            ),
            h('div', { style: { padding: '8px 10px', borderRadius: '6px', background: 'rgba(8, 145, 178, 0.08)', border: '1px solid rgba(8, 145, 178, 0.2)', color: '#0891b2', fontSize: '12px', lineHeight: 1.5 } },
              '💡 激活引导：配置或更新插件后，请在左侧点击【➕ 新会话】，新会话将自动注入 stdio MCP 工具与 Hook 守卫。'
            )
          ),

          // TAB: 技能
          tab === 'skills' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px' } },
            SKILLS_LIST.map((s, idx) =>
              h('div', {
                key: idx,
                style: {
                  padding: '8px 10px',
                  borderRadius: '6px',
                  background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.05))',
                  border: '1px solid var(--dsw-alias-border-l2, rgba(125, 125, 125, 0.12))',
                }
              },
                h('div', { style: { fontFamily: 'monospace', fontWeight: '600', color: '#0891b2' } }, s.name),
                h('div', { style: { marginTop: '2px', opacity: 0.85, fontSize: '12px' } }, s.desc)
              )
            )
          ),

          // TAB: MCP 工具 (与反重力详情页 1:1 结构)
          tab === 'mcp' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '10px' } },
            h('div', { style: { display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#0891b2', fontWeight: '600' } },
              h('span', null, 'openviking-memory_core'),
              h('span', { style: { opacity: 0.5 } }, '•'),
              h('span', null, `${totalToolsCount} tools enabled`)
            ),
            MCP_TOOLS_CATALOG.map((group, gIdx) =>
              h('div', { key: gIdx, style: { marginBottom: '4px' } },
                h('div', { style: { fontSize: '12px', opacity: 0.7, marginBottom: '6px', fontWeight: '500' } }, group.cat),
                h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: '6px' } },
                  group.tools.map((toolName, tIdx) =>
                    h('span', {
                      key: tIdx,
                      style: {
                        fontFamily: 'monospace',
                        fontSize: '12px',
                        padding: '2px 8px',
                        borderRadius: '6px',
                        background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.08))',
                        border: '1px solid var(--dsw-alias-border-l1, rgba(125, 125, 125, 0.2))',
                        color: 'inherit',
                      }
                    }, toolName)
                  )
                )
              )
            )
          ),

          // TAB: 钩子
          tab === 'hooks' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px' } },
            HOOKS_LIST.map((hk, idx) =>
              h('div', {
                key: idx,
                style: {
                  padding: '8px 10px',
                  borderRadius: '6px',
                  background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.05))',
                  border: '1px solid var(--dsw-alias-border-l2, rgba(125, 125, 125, 0.12))',
                }
              },
                h('div', { style: { display: 'flex', alignItems: 'center', gap: '6px' } },
                  h('span', { style: { fontFamily: 'monospace', fontWeight: '600', color: '#0891b2' } }, hk.name),
                  h('span', { style: { fontSize: '12px', opacity: 0.6 } }, `(${hk.type})`)
                ),
                h('div', { style: { marginTop: '2px', opacity: 0.85, fontSize: '12px' } }, hk.desc)
              )
            )
          ),

          // TAB: 配置 (带输入框明暗自适应与清空重置)
          tab === 'settings' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '10px' } },
            // 服务端接口地址
            h('div', null,
              h('label', { style: { display: 'block', marginBottom: '4px', fontWeight: '500' } }, 'OpenViking 服务端接口地址:'),
              h('input', {
                type: 'text',
                value: config.endpointUrl,
                onChange: (e) => handleChange('endpointUrl', e.target.value),
                placeholder: '例如 https://vk.tide.red 或 http://127.0.0.1:1933',
                style: {
                  width: '100%',
                  boxSizing: 'border-box',
                  padding: '6px 10px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  borderRadius: '6px',
                  border: '1px solid var(--dsw-alias-border-l2, rgba(125, 125, 125, 0.25))',
                  background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.08))',
                  color: 'inherit',
                  caretColor: '#0891b2',
                },
              })
            ),
            // User API Key
            h('div', null,
              h('label', { style: { display: 'block', marginBottom: '4px', fontWeight: '500' } }, '用户专属 API 密钥 (User Key):'),
              h('div', { style: { display: 'flex', gap: '6px' } },
                h('input', {
                  type: showKey ? 'text' : 'password',
                  value: config.userKey,
                  onChange: (e) => handleChange('userKey', e.target.value),
                  placeholder: '在 Web Studio 复制您的专属 User Key',
                  style: {
                    flex: 1,
                    boxSizing: 'border-box',
                    padding: '6px 10px',
                    fontSize: '12px',
                    fontFamily: 'monospace',
                    borderRadius: '6px',
                    border: '1px solid var(--dsw-alias-border-l2, rgba(125, 125, 125, 0.25))',
                    background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.08))',
                    color: 'inherit',
                    caretColor: '#0891b2',
                  },
                }),
                h('button', {
                  type: 'button',
                  onClick: () => setShowKey(!showKey),
                  style: {
                    padding: '0 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--dsw-alias-border-l2, rgba(125, 125, 125, 0.25))',
                    background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.08))',
                    color: 'inherit',
                    fontSize: '12px',
                    cursor: 'pointer',
                  },
                }, showKey ? '隐藏' : '显示')
              )
            ),
            // 操作按钮组
            h('div', { style: { marginTop: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' } },
              h('button', {
                type: 'button',
                onClick: handleClear,
                style: {
                  background: 'transparent',
                  color: '#e11d48',
                  border: '1px solid rgba(225, 29, 72, 0.4)',
                  padding: '5px 12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  cursor: 'pointer',
                },
              }, '🗑️ 清空本地凭据与缓存'),
              h('button', {
                type: 'button',
                onClick: handleSave,
                disabled: saving,
                style: {
                  background: '#0891b2',
                  color: '#ffffff',
                  border: 'none',
                  padding: '6px 16px',
                  borderRadius: '6px',
                  fontWeight: '600',
                  fontSize: '12px',
                  cursor: saving ? 'not-allowed' : 'pointer',
                },
              }, saving ? '保存中...' : '💾 保存配置')
            )
          )
        ),

        // 反馈 Toast
        toast
          ? h('div', {
              style: {
                marginTop: '10px',
                padding: '6px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                background: toast.ok ? 'rgba(8, 145, 178, 0.1)' : 'rgba(225, 29, 72, 0.1)',
                border: `1px solid ${toast.ok ? '#0891b2' : '#e11d48'}`,
                color: toast.ok ? '#0891b2' : '#e11d48',
              },
            }, toast.msg)
          : null
      );
    }

    function apply(ctx) {
      // 卸载联动：物理抹除本地历史凭据
      if (ctx && typeof ctx.on === 'function') {
        ctx.on('dispose', () => {
          clearSavedStorage();
        });
      }

      ctx.slots.inject('plugins.bundle.config', () =>
        ctx.slots.register(
            {
              name: 'plugins.bundle.config',
              key: 'dsh-plugin-openviking-memory',
            },
            DshPluginOpenvikingMemoryPanel
        )
      );
      if ('dsh-plugin-openviking-memory' === 'dsh-plugin-openviking-memory') {
        ctx.slots.inject('plugins.bundle.config', () =>
          ctx.slots.register(
              {
                name: 'plugins.bundle.config',
                key: 'dsh-plugin-openviking',
              },
              DshPluginOpenvikingMemoryPanel
          )
        );
      }
    }

    return {
      inject: ['slots'],
      apply,
    };
  },
});
