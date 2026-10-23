/**
 * universal_dsh_client.js - OpenViking 通用无状态 DSH 插件座舱与配置面板模板
 * 100% 动态元数据与表单双轨驱动：支持服务端实时探针、端点与 UserKey 热配置、三锚点全冗余插槽注册。
 * 视觉铁律：NO GREEN EVER 🚫 (#0891b2 冰青 / #e11d48 玫瑰红)，字号 >= 12px，6px 微圆角，高对比度。
 */

window.__ModuleLoader__.load({
  id: 'dsh-plugin-dify',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState, useEffect } = React;

    const PLUGIN_ID = 'dsh-plugin-dify';
    const CLIENT_VERSION = '1.0.1';
    const PLUGIN_NAME = 'Dify Orchestrator';
    const SHORT_NAME = 'dify';
    const STORAGE_KEY = `dsh_plugin_${SHORT_NAME.replace(/-/g, '_')}_config`;

    // 动态插值数据源
    const TOOL_CATEGORIES = [{"cat": "Dify 工作流与编排引擎 (Dify Engine)", "tools": ["dify_status", "dify_list_apps", "dify_get_app", "dify_export_dsl", "dify_import_dsl", "dify_delete_app", "dify_run_workflow", "dify_list_datasets", "dify_create_dataset", "dify_delete_dataset", "dify_list_model_providers"]}, {"cat": "核心长程记忆与检索 (Memory & Context)", "tools": ["dify_search_dataset"]}];
    const SKILLS = [{"name": "Dify Orchestrator 官方操作手册", "desc": "Dify Orchestrator 领域专家操作认知手册"}];
    const HOOKS = [];
    const OVERVIEW_CARDS = [{"title": "🔌 架构定位与契约", "text": "Dify 官方全量编排与知识库控制面工具集 (12 Tools)。用于管理应用、运行工作流、导入导出 DSL 蓝图及自动化管理知识库。"}, {"title": "🎯 建议交互指令", "text": "• 检查本地 Dify 控制台连接状态与工作区概况\n• 列出 Dify 中的所有已部署应用与工作流\n• 导出指定应用的 DSL 蓝图配置"}, {"title": "🛡️ 治理与审计规约", "text": "遵循 OpenViking 零信任治理公理与单一真相源 (SSOT)。所有调用行为均自动留存安全审计轨迹与调用链追踪。"}];

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
        endpointUrl: 'https://vk.tide.red',
        userKey: '',
        agentId: 'deepseek-harness@satellite',
        peer: SHORT_NAME
      };
    }

    function saveConfig(cfg) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
      } catch (_) {}
    }

    function UniversalDshPanel(props) {
      if (props && props.view === 'summary') return null;

      const [formConfig, setFormConfig] = useState(() => {
        const initial = loadSavedConfig();
        const pCfg = props?.config || {};
        return {
          endpointUrl: pCfg.endpointUrl || initial.endpointUrl || 'https://vk.tide.red',
          userKey: pCfg.userKey || initial.userKey || '',
          agentId: pCfg.agentId || initial.agentId || 'deepseek-harness@satellite',
          peer: pCfg.peer || initial.peer || SHORT_NAME
        };
      });

      const [tab, setTab] = useState('config');
      const [showKey, setShowKey] = useState(false);
      const [probe, setProbe] = useState({ ok: false, latency: 0, toolsCount: totalToolsCount });
      const [testStatus, setTestStatus] = useState(null);
      const [testing, setTesting] = useState(false);
      const [saving, setSaving] = useState(false);
      const [saveToast, setSaveToast] = useState(null);

      useEffect(() => {
        let mounted = true;
        const initial = loadSavedConfig();
        const base = (initial.endpointUrl || formConfig.endpointUrl || 'https://vk.tide.red').trim().replace(/\/mcp\/?$/i, '').replace(/\/+$/, '');
        const key = initial.userKey || formConfig.userKey || '';
        const headers = { 'Content-Type': 'application/json' };
        if (key) headers['Authorization'] = `Bearer ${key.trim()}`;

        const start = Date.now();
        fetch(`${base}/health`, { headers, signal: AbortSignal.timeout(3000) })
          .then(res => res.ok ? res.json() : null)
          .then(data => {
            if (!mounted || !data) return;
            setProbe({ ok: true, latency: Date.now() - start, toolsCount: totalToolsCount || 35 });
          })
          .catch(() => {});
        return () => { mounted = false; };
      }, []);

      const handleChange = (field, val) => setFormConfig(prev => ({ ...prev, [field]: val }));
      const handlePreset = (url) => setFormConfig(prev => ({ ...prev, endpointUrl: url }));

      const handleTest = async () => {
        setTesting(true);
        setTestStatus(null);
        let base = (formConfig.endpointUrl || '').trim().replace(/\/mcp\/?$/i, '').replace(/\/+$/, '') || 'https://vk.tide.red';
        const start = Date.now();
        const headers = { 'Content-Type': 'application/json' };
        if (formConfig.userKey) headers['Authorization'] = `Bearer ${formConfig.userKey.trim()}`;
        if (formConfig.agentId) headers['X-Agent-ID'] = formConfig.agentId.trim();

        try {
          const res = await fetch(`${base}/health`, { headers, signal: AbortSignal.timeout(4000) });
          const latency = Date.now() - start;
          if (res.ok) {
            const hData = await res.json();
            let toolCount = totalToolsCount || 35;
            let roleMsg = '服务连接正常';
            try {
              const capRes = await fetch(`${base}/api/v1/system/client-capabilities?plugin_id=${PLUGIN_ID}&probe=full`, {
                headers, signal: AbortSignal.timeout(4000)
              });
              if (capRes.ok) {
                const capData = await capRes.json();
                if (Array.isArray(capData.tools) && capData.tools.length > 0) toolCount = capData.tools.length;
                roleMsg = capData.role ? `鉴权角色: ${capData.role}` : '用户凭据有效';
              } else if (capRes.status === 401) {
                setTestStatus({ ok: false, msg: '网络通畅但凭据被拒绝 (HTTP 401): 填写的 UserKey 无效或未授权' });
                setTesting(false);
                return;
              }
            } catch (_) {}
            setTestStatus({ ok: true, msg: `连接成功 (v${hData.version || '1.7'}) · 延迟 ${latency}ms · ${roleMsg} · 就绪 ${toolCount} 项工具` });
            setProbe({ ok: true, latency, toolsCount: toolCount });
          } else {
            setTestStatus({ ok: false, msg: `服务端响应异常: HTTP ${res.status} ${res.statusText}` });
          }
        } catch (err) {
          setTestStatus({ ok: false, msg: `连接不可达: ${err.message || '网络超时或端点不可达'}` });
        } finally {
          setTesting(false);
        }
      };

      const handleSave = () => {
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
        setTimeout(() => {
          setSaving(false);
          setSaveToast({ ok: true, msg: '配置已持久化保存，并在 DSH 会话中实时热生效！' });
          setTimeout(() => setSaveToast(null), 3000);
        }, 200);
      };

      const tabs = [
        { key: 'config', label: '⚙️ 服务配置' },
        ...(TOOL_CATEGORIES.length > 0 ? [{ key: 'mcp', label: `🦾 MCP 工具 (${probe.toolsCount || totalToolsCount})` }] : []),
        ...(SKILLS.length > 0 ? [{ key: 'skills', label: `🧠 认知技能 (${SKILLS.length})` }] : []),
        ...(HOOKS.length > 0 ? [{ key: 'hooks', label: `⚡ 拦截钩子 (${HOOKS.length})` }] : []),
        { key: 'overview', label: '📖 架构概览' }
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
        // 1. 顶部状态横幅
        h('div', {
          style: {
            padding: '8px 12px',
            borderRadius: '6px',
            marginBottom: '12px',
            background: probe.ok ? 'rgba(8, 145, 178, 0.08)' : 'rgba(225, 29, 72, 0.06)',
            border: `1px solid ${probe.ok ? '#0891b2' : 'rgba(225, 29, 72, 0.3)'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '12px',
          }
        },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
            h('span', { style: { color: probe.ok ? '#0891b2' : '#e11d48', fontWeight: '600' } }, probe.ok ? '● 探针连接正常 (已鉴权)' : '○ 服务离线 / 待测试'),
            h('span', { style: { opacity: 0.7, color: 'var(--dsw-alias-label-secondary, #334155)' } }, `时延: ${probe.latency}ms · v${CLIENT_VERSION}`)
          ),
          h('div', { style: { fontFamily: 'monospace', fontWeight: '500', color: probe.ok ? '#0891b2' : 'var(--dsw-alias-label-tertiary, #64748b)' } },
            probe.ok ? `${probe.toolsCount || totalToolsCount} 项算子已挂载` : `${totalToolsCount} 项离线工具就绪`
          )
        ),

        // 2. Tab 导航栏
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

        // 3. Tab 内容区
        tab === 'config' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '10px' } },
          h('div', null,
            h('div', { style: { display: 'flex', justifyContent: 'space-between', marginBottom: '4px' } },
              h('label', { style: { fontWeight: '600', color: 'var(--dsw-alias-label-primary, #0f172a)' } }, 'OpenViking 服务端通信端点 (Endpoint URL)'),
              h('div', { style: { display: 'flex', gap: '6px' } },
                h('button', {
                  type: 'button',
                  onClick: () => handlePreset('https://vk.tide.red'),
                  style: { background: 'none', border: '1px solid #0891b2', color: '#0891b2', borderRadius: '4px', fontSize: '12px', padding: '1px 6px', cursor: 'pointer' }
                }, '云端默认'),
                h('button', {
                  type: 'button',
                  onClick: () => handlePreset('http://127.0.0.1:1933'),
                  style: { background: 'none', border: '1px solid #cbd5e1', color: 'var(--dsw-alias-label-secondary, #475569)', borderRadius: '4px', fontSize: '12px', padding: '1px 6px', cursor: 'pointer' }
                }, '本地直连')
              )
            ),
            h('input', {
              type: 'text',
              value: formConfig.endpointUrl,
              onChange: (e) => handleChange('endpointUrl', e.target.value),
              placeholder: '例如 https://vk.tide.red 或 http://127.0.0.1:1933',
              style: {
                width: '100%', padding: '6px 10px', borderRadius: '6px',
                border: '1px solid var(--dsw-alias-input-border, #cbd5e1)',
                background: 'var(--dsw-alias-input-bg, #ffffff)',
                color: 'var(--dsw-alias-label-primary, #0f172a)', fontSize: '12px', boxSizing: 'border-box'
              }
            })
          ),
          h('div', null,
            h('label', { style: { display: 'block', fontWeight: '600', marginBottom: '4px', color: 'var(--dsw-alias-label-primary, #0f172a)' } }, '专属 API Key / User Key'),
            h('div', { style: { display: 'flex', gap: '6px' } },
              h('input', {
                type: showKey ? 'text' : 'password',
                value: formConfig.userKey,
                onChange: (e) => handleChange('userKey', e.target.value),
                placeholder: '请输入用户授权密钥 (可留空自动继承环境凭据)',
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
              }, showKey ? '🙈 隐藏' : '👁️ 显示')
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
            }, testing ? '⚡ 探测中...' : '⚡ 测试连通性'),
            h('button', {
              type: 'button', onClick: handleSave, disabled: saving,
              style: {
                background: '#0891b2', color: '#ffffff', border: 'none',
                padding: '6px 16px', borderRadius: '6px', fontWeight: '600', fontSize: '12px',
                cursor: saving ? 'not-allowed' : 'pointer'
              }
            }, saving ? '💾 保存中...' : '💾 保存并应用配置')
          ),
          saveToast && h('div', {
            style: {
              padding: '6px 10px', borderRadius: '6px', fontSize: '12px',
              background: 'rgba(8, 145, 178, 0.1)', border: '1px solid #0891b2',
              color: '#0891b2', fontWeight: '500', textAlign: 'center'
            }
          }, saveToast.msg)
        ),

        tab === 'mcp' && h('div', {
          style: { display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '400px', overflowY: 'auto' }
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
                h('span', { style: { color: '#0891b2', fontWeight: 'bold' } }, '⚡'),
                h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, tName)
              ))
            )
          ))
        ),

        tab === 'skills' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '6px' } },
          SKILLS.map((s, idx) => h('div', {
            key: idx,
            style: { padding: '8px 10px', borderRadius: '6px', background: 'var(--dsw-alias-bg-layer-2, #f8fafc)', border: '1px solid #e2e8f0' }
          },
            h('div', { style: { fontFamily: 'monospace', fontWeight: '600', color: '#0891b2', fontSize: '12px' } }, s.name),
            h('div', { style: { marginTop: '2px', color: 'var(--dsw-alias-label-secondary, #475569)', fontSize: '12px' } }, s.desc)
          ))
        ),

        tab === 'hooks' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '6px' } },
          HOOKS.map((hk, idx) => h('div', {
            key: idx,
            style: { padding: '8px 10px', borderRadius: '6px', background: 'var(--dsw-alias-bg-layer-2, #f8fafc)', border: '1px solid #e2e8f0' }
          },
            h('div', { style: { fontWeight: '600', color: '#0891b2', fontSize: '12px' } }, hk.name),
            h('div', { style: { color: 'var(--dsw-alias-label-secondary, #475569)', fontSize: '12px' } }, hk.desc),
            h('div', { style: { color: 'var(--dsw-alias-label-tertiary, #64748b)', fontSize: '12px', marginTop: '2px', fontFamily: 'monospace' } }, `拦截点: ${hk.event}`)
          ))
        ),

        tab === 'overview' && h('div', {
          style: { display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '400px', overflowY: 'auto' }
        },
          OVERVIEW_CARDS.map((card, idx) => h('div', {
            key: idx,
            style: { padding: '10px', borderRadius: '6px', background: 'var(--dsw-alias-bg-layer-2, #f8fafc)', border: '1px solid #e2e8f0' }
          },
            h('div', { style: { fontWeight: '600', fontSize: '12px', color: '#0891b2', marginBottom: '2px' } }, card.title),
            h('div', { style: { color: 'var(--dsw-alias-label-secondary, #334155)', fontSize: '12px', lineHeight: 1.5 } }, card.text)
          ))
        ),

        // 4. 底部微弱版本声明
        h('div', {
          style: {
            marginTop: '12px', paddingTop: '6px',
            borderTop: '1px solid var(--dsw-alias-border-l1, #e2e8f0)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            fontSize: '12px', color: 'var(--dsw-alias-label-tertiary, #64748b)',
          }
        },
          h('span', null, `OpenViking Universal Cockpit · ${PLUGIN_NAME}`),
          h('span', null, `版本 v${CLIENT_VERSION}`)
        )
      );
    }

    function apply(ctx) {
      const bundleKey = PLUGIN_ID;
      const shortKey = SHORT_NAME;

      // 1. 组合包详情页配置插槽 (Bundle Detail Page) - 兼容全名与短名
      ctx.slots.inject('plugins.bundle.config', () => {
        ctx.slots.register({ name: 'plugins.bundle.config', key: bundleKey }, UniversalDshPanel);
        if (shortKey !== bundleKey) {
          ctx.slots.register({ name: 'plugins.bundle.config', key: shortKey }, UniversalDshPanel);
        }
      });

      // 2. 组件行专属抽屉插槽 (Row Detail / Configure Drawer) - 兼容 <bundle>#<row> 与短格式
      ctx.slots.inject('plugins.row.config', () => {
        ctx.slots.register({ name: 'plugins.row.config', key: `${bundleKey}#${shortKey}` }, UniversalDshPanel);
        ctx.slots.register({ name: 'plugins.row.config', key: `${shortKey}#${shortKey}` }, UniversalDshPanel);
        ctx.slots.register({ name: 'plugins.row.config', key: bundleKey }, UniversalDshPanel);
        ctx.slots.register({ name: 'plugins.row.config', key: shortKey }, UniversalDshPanel);
      });

      // 3. 全局设置插件页 Tab (Settings -> Plugins Tab)
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