/**
 * universal_dsh_client.js - OpenViking 通用无状态 DSH 插件座舱与配置面板模板
 * 100% 动态元数据与表单双轨驱动：支持服务端实时探针、端点与 UserKey 热配置、双锚点全冗余插槽注册。
 * 视觉铁律：NO GREEN EVER 🚫 (#0891b2 冰青 / #e11d48 玫瑰红)，字号 >= 12px，6px 微圆角，高对比度。
 */

window.__ModuleLoader__.load({
  id: 'dsh-plugin-openviking-ops',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState } = React;

    const PLUGIN_ID = 'dsh-plugin-openviking-ops';
    const CLIENT_VERSION = '1.0.7';
    const PLUGIN_NAME = 'OpenViking System Ops (v1.0.6)';
    const SHORT_NAME = 'openviking-ops';
    const STORAGE_KEY = `dsh_plugin_${SHORT_NAME.replace(/-/g, '_')}_config`;

    // 动态插值数据源 (离线兜底 SSOT)
    const TOOL_CATEGORIES = [{"cat": "系统运维治理与快照 (Ops & Snapshots)", "tools": ["openviking_add_resource", "openviking_list_resources", "openviking_delete_resource", "openviking_reindex", "openviking_retry_dead_letter", "openviking_server_control", "openviking_server_init", "openviking_server_doctor"]}, {"cat": "原子扩展工具箱 (FastMCP Tools)", "tools": ["openviking_commit", "openviking_mv", "openviking_rename", "openviking_list_watches", "openviking_cancel_watch", "openviking_manage_watch"]}, {"cat": "全网检索与智能抓取 (Network Search)", "tools": ["openviking_webdav_info"]}, {"cat": "核心长程记忆与检索 (Memory & Context)", "tools": ["openviking_memory_purity_report"]}];
    const SKILLS = [{"name": "openviking-ops", "desc": "OpenViking 核心服务运维、拓扑体检、存储初始化与特权管控专用技能。涵盖 16 项系统运维特权工具的高阶 SOP 与安全护栏。"}];
    const HOOKS = [{"name": "openviking-ops-sentinel", "desc": "拦截 SessionStart 事件，执行守卫检查", "event": "SessionStart"}, {"name": "openviking-ops-audit", "desc": "拦截 PreToolUse 事件，执行守卫检查", "event": "PreToolUse"}];
    const RULES = [];
    const README_CONTENT = "# OpenViking 系统运维治理插件 (openviking-ops)\n\n专为 **OpenViking (VK) 体外大脑** 打造的系统级运维治理与管控特权插件。面向后台运维智能体、哨兵巡检引擎与系统管理员，提供高特权物理算子与 Hook 神经反射守卫。\n\n---\n\n## 🌟 核心价值与特权架构\n\n1. **三位一体运维治理架构**：\n   - **MCP 特权工具层**：直连服务端核心接口，提供数据索引重建、底层文件安全原子重定位、死信队列自愈、记忆纯度审计与服务启停重载；\n   - **Hook 物理安全守卫**：包含 `SessionStart` 巡检心跳与 `PreToolUse` 破坏性操作安全审计，防止生产误停机；\n   - **专家认知导轨**：内嵌系统运维 SOP 与安全护栏，先查后动、原子提交版本快照。\n\n2. **零信任单轨鉴权与安全审计**：\n   - 严格要求管理员 Bearer 凭据，物理封杀本地未授权越权操作；\n   - 高危操作自动留下审计系谱日志，确保每一项系统级变更具备完整可追溯性。\n\n";

    const totalToolsCount = TOOL_CATEGORIES.reduce((acc, c) => acc + (c.tools ? c.tools.length : 0), 0);

    function loadSavedConfig() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY) || localStorage.getItem(`dsh_plugin_${PLUGIN_ID.replace(/-/g, '_')}_config`);
        if (raw) {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === 'object') return parsed;
        }
      } catch (_) {}
      return {
        endpointUrl: '',
        userKey: '',
        agentId: '',
        peer: SHORT_NAME
      };
    }

    function saveConfig(cfg) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
      } catch (_) {}
    }

    // 1. 顶层组合包主控座舱 (Bundle Master Cockpit)
    function UniversalDshPanel(props) {
      if (props && props.view === 'summary') return null;

      const [formConfig, setFormConfig] = useState(() => {
        const initial = loadSavedConfig();
        const pCfg = props?.config || {};
        return {
          endpointUrl: pCfg.endpointUrl || initial.endpointUrl || '',
          userKey: pCfg.userKey || initial.userKey || '',
          agentId: pCfg.agentId || initial.agentId || '',
          peer: pCfg.peer || initial.peer || SHORT_NAME
        };
      });

      const [tab, setTab] = useState('config');
      const [showKey, setShowKey] = useState(false);
      const [testStatus, setTestStatus] = useState(null);
      const [testing, setTesting] = useState(false);
      const [saving, setSaving] = useState(false);
      const [saveToast, setSaveToast] = useState(null);
      const [serverVersion, setServerVersion] = useState('');
      const [liveToolsCount, setLiveToolsCount] = useState(totalToolsCount);

      const handleChange = (field, val) => setFormConfig(prev => ({ ...prev, [field]: val }));
      const handlePreset = (url) => setFormConfig(prev => ({ ...prev, endpointUrl: url }));

      const handleTest = async () => {
        const endpoint = (formConfig.endpointUrl || '').trim();
        if (!endpoint) {
          setTestStatus({ ok: false, msg: '请先填写通信端点 (Endpoint URL)' });
          return;
        }
        setTesting(true);
        setTestStatus(null);
        const base = endpoint.replace(/\/mcp\/?$/i, '').replace(/\/+$/, '');
        const start = Date.now();
        const headers = { 'Content-Type': 'application/json' };
        if (formConfig.userKey) headers['Authorization'] = `Bearer ${formConfig.userKey.trim()}`;
        if (formConfig.agentId) headers['X-Agent-ID'] = formConfig.agentId.trim();

        try {
          const res = await fetch(`${base}/health`, { headers, signal: AbortSignal.timeout(4000) });
          const latency = Date.now() - start;
          if (res.ok) {
            const hData = await res.json();
            const sVer = hData.version || '1.7';
            setServerVersion(sVer);
            let toolCount = totalToolsCount || 35;
            let roleMsg = '服务连接正常';
            try {
              const capRes = await fetch(`${base}/api/v1/system/client-capabilities?plugin_id=${PLUGIN_ID}&probe=full`, {
                headers, signal: AbortSignal.timeout(4000)
              });
              if (capRes.ok) {
                const capData = await capRes.json();
                if (Array.isArray(capData.tools) && capData.tools.length > 0) {
                  toolCount = capData.tools.length;
                  setLiveToolsCount(toolCount);
                }
                roleMsg = capData.role ? `角色: ${capData.role}` : '凭据有效';
              } else if (capRes.status === 401) {
                setTestStatus({ ok: false, msg: '网络通畅但凭据被拒绝 (HTTP 401): 填写的 UserKey 无效' });
                setTesting(false);
                return;
              }
            } catch (_) {}
            setTestStatus({ ok: true, msg: `连接成功 (v${sVer}) · 延迟 ${latency}ms · ${roleMsg} · 就绪 ${toolCount} 项工具` });
          } else {
            setTestStatus({ ok: false, msg: `服务端响应异常: HTTP ${res.status} ${res.statusText}` });
          }
        } catch (err) {
          setTestStatus({ ok: false, msg: `连接不可达: ${err.message || '网络超时或端点不可达'}` });
        } finally {
          setTesting(false);
        }
      };

      const handleSave = async () => {
        setSaving(true);
        saveConfig(formConfig);
        if (props?.form?.mutate) {
          try {
            props.form.mutate([
              { op: 'replace', path: '/endpointUrl', value: formConfig.endpointUrl },
              { op: 'replace', path: '/userKey', value: formConfig.userKey },
              { op: 'replace', path: '/agentId', value: formConfig.agentId },
              { op: 'replace', path: '/peer', value: formConfig.peer }
            ]);
          } catch (_) {}
        }
        if (typeof props?.onChange === 'function') {
          try { props.onChange({ ...props.config, ...formConfig }); } catch (_) {}
        }
        try {
          await fetch('http://127.0.0.1:19339/ov-dsh-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pluginId: PLUGIN_ID, shortName: SHORT_NAME, config: formConfig }),
            signal: AbortSignal.timeout(2000)
          });
        } catch (_) {}
        setSaving(false);
        setSaveToast({ ok: true, msg: '配置已持久化保存，并在 DSH 会话中实时生效' });
        setTimeout(() => setSaveToast(null), 3000);
      };

      const tabs = [
        { key: 'config', label: '服务配置' },
        { key: 'overview', label: '概览' },
        ...(SKILLS.length > 0 ? [{ key: 'skills', label: `技能 (${SKILLS.length})` }] : []),
        ...(TOOL_CATEGORIES.length > 0 ? [{ key: 'mcp', label: `MCP (${liveToolsCount})` }] : []),
        ...(HOOKS.length > 0 ? [{ key: 'hooks', label: `钩子 (${HOOKS.length})` }] : []),
        ...(RULES.length > 0 ? [{ key: 'rules', label: `规则 (${RULES.length})` }] : [])
      ];

      return h('div', {
        style: {
          padding: '14px',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          fontSize: '12px',
          color: 'var(--dsw-alias-label-primary, #0f172a)',
          background: 'var(--dsw-alias-settings-card-fill, var(--dsw-alias-bg-l1, #ffffff))',
          borderRadius: '8px',
          border: '1px solid var(--dsw-alias-settings-card-stroke, var(--dsw-alias-border-l1, #e2e8f0))',
          lineHeight: 1.5,
          margin: '6px 0',
        }
      },
        // 0. 局部注入样式：彻底物理蒸发 DSH 原生冗余的 "包含的组件" (<section data-plugin-rows>) 区块
        h('style', null, `
          div[data-plugin-detail] [data-plugin-rows] {
            display: none !important;
          }
        `),

        // 1. Tab 导航栏
        h('div', {
          style: {
            display: 'flex',
            gap: '4px',
            borderBottom: '1px solid var(--dsw-alias-border-l1, #e2e8f0)',
            marginBottom: '12px',
            paddingBottom: '2px'
          }
        },
          tabs.map(t => h('button', {
            key: t.key,
            type: 'button',
            onClick: () => setTab(t.key),
            style: {
              background: 'transparent',
              border: 'none',
              borderBottom: tab === t.key ? '2px solid #0891b2' : '2px solid transparent',
              color: tab === t.key ? '#0891b2' : 'var(--dsw-alias-label-secondary, #475569)',
              fontWeight: tab === t.key ? '600' : 'normal',
              padding: '6px 12px',
              fontSize: '12px',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }
          }, t.label))
        ),

        // 2. Tab 内容区
        tab === 'config' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '10px' } },
          h('div', null,
            h('div', { style: { display: 'flex', justifyContent: 'space-between', marginBottom: '4px' } },
              h('label', { style: { fontWeight: '600', color: 'var(--dsw-alias-label-primary, #0f172a)' } }, 'OpenViking 服务端通信端点 (Endpoint URL)'),
              h('div', { style: { display: 'flex', gap: '6px' } },
                h('button', {
                  type: 'button',
                  onClick: () => handlePreset('http://127.0.0.1:1933'),
                  style: { background: 'none', border: '1px solid #0891b2', color: '#0891b2', borderRadius: '4px', fontSize: '12px', padding: '1px 6px', cursor: 'pointer' }
                }, '本地直连 (http://127.0.0.1:1933)')
              )
            ),
            h('input', {
              type: 'text',
              value: formConfig.endpointUrl,
              onChange: (e) => handleChange('endpointUrl', e.target.value),
              placeholder: '请输入通信端点 (例如 http://127.0.0.1:1933 或 https://vk.example.com)',
              style: {
                width: '100%', padding: '6px 10px', borderRadius: '6px',
                border: '1px solid var(--dsw-alias-input-border, #cbd5e1)',
                background: 'var(--dsw-alias-input-bg, #ffffff)',
                color: 'var(--dsw-alias-label-primary, #0f172a)', fontSize: '12px', boxSizing: 'border-box'
              }
            })
          ),
          h('div', null,
            h('label', { style: { display: 'block', fontWeight: '600', marginBottom: '4px', color: 'var(--dsw-alias-label-primary, #0f172a)' } }, '专属 UserKey 授权凭据'),
            h('div', { style: { display: 'flex', gap: '6px' } },
              h('input', {
                type: showKey ? 'text' : 'password',
                value: formConfig.userKey,
                onChange: (e) => handleChange('userKey', e.target.value),
                placeholder: '请输入专属 UserKey (格式: account.user.signature，留空自动继承环境凭据)',
                style: {
                  flex: 1, padding: '6px 10px', borderRadius: '6px',
                  border: '1px solid var(--dsw-alias-input-border, #cbd5e1)',
                  background: 'var(--dsw-alias-input-bg, #ffffff)',
                  color: 'var(--dsw-alias-label-primary, #0f172a)', fontSize: '12px', boxSizing: 'border-box'
                }
              }),
              h('button', {
                type: 'button',
                onClick: () => setShowKey(!showKey),
                style: {
                  padding: '0 10px', borderRadius: '6px', border: '1px solid #cbd5e1',
                  background: 'var(--dsw-alias-bg-layer-2, #f8fafc)',
                  color: 'var(--dsw-alias-label-secondary, #475569)', cursor: 'pointer', fontSize: '12px'
                }
              }, showKey ? '隐藏' : '显示')
            )
          ),
          testStatus && h('div', {
            style: {
              padding: '8px 10px', borderRadius: '6px', fontSize: '12px',
              background: testStatus.ok ? 'rgba(8, 145, 178, 0.08)' : 'rgba(225, 29, 72, 0.08)',
              border: `1px solid ${testStatus.ok ? '#0891b2' : '#e11d48'}`,
              color: testStatus.ok ? '#0891b2' : '#e11d48'
            }
          }, testStatus.msg),
          h('div', { style: { display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '6px' } },
            h('button', {
              type: 'button', onClick: handleTest, disabled: testing,
              style: {
                background: 'transparent', color: '#0891b2', border: '1px solid #0891b2',
                padding: '6px 14px', borderRadius: '6px', fontWeight: '600', fontSize: '12px',
                cursor: testing ? 'not-allowed' : 'pointer'
              }
            }, testing ? '探测中...' : '测试连通性'),
            h('button', {
              type: 'button', onClick: handleSave, disabled: saving,
              style: {
                background: '#0891b2', color: '#ffffff', border: 'none',
                padding: '6px 16px', borderRadius: '6px', fontWeight: '600', fontSize: '12px',
                cursor: saving ? 'not-allowed' : 'pointer'
              }
            }, saving ? '保存中...' : '保存配置')
          ),
          saveToast && h('div', {
            style: {
              padding: '6px 10px', borderRadius: '6px', fontSize: '12px',
              background: 'rgba(8, 145, 178, 0.1)', border: '1px solid #0891b2',
              color: '#0891b2', fontWeight: '500', textAlign: 'center'
            }
          }, saveToast.msg)
        ),

        tab === 'overview' && h('div', {
          style: {
            maxHeight: '440px',
            overflowY: 'auto',
            padding: '12px 14px',
            borderRadius: '6px',
            background: 'var(--dsw-alias-bg-layer-2, #f8fafc)',
            border: '1px solid var(--dsw-alias-border-l1, #e2e8f0)',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            fontSize: '12px',
            lineHeight: 1.6,
            color: 'var(--dsw-alias-label-primary, #0f172a)'
          }
        },
          h('pre', {
            style: {
              margin: 0,
              fontFamily: 'inherit',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: '12px',
              color: 'inherit'
            }
          }, README_CONTENT || `${PLUGIN_NAME} 暂无详细文档说明`)
        ),

        tab === 'skills' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '440px', overflowY: 'auto' } },
          SKILLS.map((s, idx) => h('div', {
            key: idx,
            style: { padding: '8px 10px', borderRadius: '6px', background: 'var(--dsw-alias-bg-layer-2, #f8fafc)', border: '1px solid #e2e8f0' }
          },
            h('div', { style: { fontFamily: 'monospace', fontWeight: '600', color: '#0891b2', fontSize: '12px' } }, s.name),
            h('div', { style: { marginTop: '2px', color: 'var(--dsw-alias-label-secondary, #475569)', fontSize: '12px' } }, s.desc)
          ))
        ),

        tab === 'mcp' && h('div', {
          style: { display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '440px', overflowY: 'auto' }
        },
          TOOL_CATEGORIES.map((catGroup, cIdx) => h('div', {
            key: cIdx,
            style: { padding: '8px 10px', borderRadius: '6px', background: 'var(--dsw-alias-bg-layer-2, #f8fafc)', border: '1px solid #e2e8f0' }
          },
            h('div', { style: { fontWeight: '600', fontSize: '12px', color: '#0891b2', marginBottom: '6px' } }, catGroup.cat),
            h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '4px' } },
              catGroup.tools.map((tName, tIdx) => h('div', {
                key: tIdx,
                style: {
                  padding: '4px 6px', borderRadius: '4px', background: '#ffffff', border: '1px solid #cbd5e1',
                  fontFamily: 'monospace', fontSize: '12px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '4px'
                }
              },
                h('span', { style: { color: '#0891b2', fontWeight: 'bold' } }, '•'),
                h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, tName)
              ))
            )
          ))
        ),

        tab === 'hooks' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '440px', overflowY: 'auto' } },
          HOOKS.map((hk, idx) => h('div', {
            key: idx,
            style: { padding: '8px 10px', borderRadius: '6px', background: 'var(--dsw-alias-bg-layer-2, #f8fafc)', border: '1px solid #e2e8f0' }
          },
            h('div', { style: { fontWeight: '600', color: '#0891b2', fontSize: '12px' } }, hk.name),
            h('div', { style: { color: 'var(--dsw-alias-label-secondary, #475569)', fontSize: '12px' } }, hk.desc),
            h('div', { style: { color: 'var(--dsw-alias-label-tertiary, #64748b)', fontSize: '12px', marginTop: '2px', fontFamily: 'monospace' } }, `拦截点: ${hk.event}`)
          ))
        ),

        tab === 'rules' && h('div', {
          style: { display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '440px', overflowY: 'auto' }
        },
          RULES.length === 0 ? h('div', { style: { padding: '12px', color: '#64748b', textAlign: 'center', fontSize: '12px' } }, '暂无规则规约') :
          RULES.map((rule, idx) => h('div', {
            key: idx,
            style: { padding: '10px 12px', borderRadius: '6px', background: 'var(--dsw-alias-bg-layer-2, #f8fafc)', border: '1px solid #e2e8f0' }
          },
            h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' } },
              h('span', { style: { fontFamily: 'monospace', fontWeight: '600', color: '#0891b2', fontSize: '12px' } }, rule.name),
              h('span', { style: { fontSize: '12px', color: 'var(--dsw-alias-label-tertiary, #64748b)' } }, rule.desc)
            ),
            rule.content && h('pre', {
              style: {
                marginTop: '6px', padding: '8px 10px', borderRadius: '4px',
                background: 'var(--dsw-alias-bg-layer-1, #ffffff)', border: '1px solid #e2e8f0',
                fontSize: '12px', fontFamily: 'monospace', whiteSpace: 'pre-wrap', lineHeight: 1.45,
                color: 'var(--dsw-alias-label-secondary, #334155)', maxHeight: '200px', overflowY: 'auto'
              }
            }, rule.content)
          ))
        ),

        // 3. 底部版本声明与云端动态能力同频状态
        h('div', {
          style: {
            marginTop: '12px', paddingTop: '6px',
            borderTop: '1px solid var(--dsw-alias-border-l1, #e2e8f0)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            fontSize: '12px', color: 'var(--dsw-alias-label-tertiary, #64748b)',
          }
        },
          h('span', null, `OpenViking Universal Cockpit · ${PLUGIN_NAME}`),
          h('span', null, serverVersion ? `端侧桥接器 v${CLIENT_VERSION} · 云端内核 v${serverVersion}` : `端侧桥接器 v${CLIENT_VERSION}`)
        )
      );
    }

    function apply(ctx) {
      const bundleKey = PLUGIN_ID;
      const shortKey = SHORT_NAME;

      // 启动时自动将浏览器端已保存的凭据同步至本机 Node.js 插件宿主，零手工干预生效
      try {
        const saved = loadSavedConfig();
        if (saved && (saved.endpointUrl || saved.userKey)) {
          fetch('http://127.0.0.1:19339/ov-dsh-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pluginId: PLUGIN_ID, shortName: SHORT_NAME, config: saved })
          }).catch(() => {});
        }
      } catch (_) {}

      // 1. 组合包详情页配置插槽 (Bundle Detail Page)
      ctx.slots.inject('plugins.bundle.config', () => {
        ctx.slots.register({ name: 'plugins.bundle.config', key: bundleKey }, UniversalDshPanel);
        if (shortKey !== bundleKey) {
          ctx.slots.register({ name: 'plugins.bundle.config', key: shortKey }, UniversalDshPanel);
        }
      });

      // 2. 全局设置插件页 Tab (Settings -> Plugins Tab)
      ctx.slots.inject('settings.plugins.tab', () => {
        ctx.slots.register({
          name: 'settings.plugins.tab',
          id: shortKey,
          order: 50,
          label: () => PLUGIN_NAME
        }, UniversalDshPanel);
      });
    }

    return {
      inject: ['slots'],
      apply,
    };
  },
});