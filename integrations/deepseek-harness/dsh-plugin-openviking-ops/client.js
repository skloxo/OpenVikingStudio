/**
 * client.js - OpenViking 系统运维治理插件 DSH Client Cockpit Plugin
 * 纯原生 React (由 DSH 宿主环境提供注入)，零外部打包依赖。
 * 遵循 Cockpit UI 规范：NO GREEN EVER 🚫 (#0891b2, #e11d48), 字号 >= 12px, 6px 微圆角。
 */

window.__ModuleLoader__.load({
  id: 'dsh-plugin-openviking-ops',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState, useEffect, useCallback } = React;

    const STORAGE_KEY = 'dsh_plugin_openviking_ops_config';
    const CAPS_STORAGE_KEY = 'dsh_plugin_openviking_ops_capabilities';

    function loadSavedConfig() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      } catch (_) {}
      return {
        endpointUrl: 'https://vk.tide.red',
        agentId: 'openviking-ops@sentinel',
        userKey: '',
        disabledTools: [],
        disabledHooks: [],
      };
    }

    function loadSavedCaps() {
      try {
        const raw = localStorage.getItem(CAPS_STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      } catch (_) {}
      return null;
    }

    function saveConfig(cfg) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg)); } catch (_) {}
    }

    function saveCaps(caps) {
      try { localStorage.setItem(CAPS_STORAGE_KEY, JSON.stringify(caps)); } catch (_) {}
    }

    function DshPluginOpenvikingOpsPanel(props) {
      const [config, setConfig] = useState(loadSavedConfig);
      const [caps, setCaps] = useState(loadSavedCaps);
      const [showKey, setShowKey] = useState(false);
      const [probeReport, setProbeReport] = useState(null);
      const [testing, setTesting] = useState(false);
      const [saving, setSaving] = useState(false);
      const [saveToast, setSaveToast] = useState(null);
      const [showToolsList, setShowToolsList] = useState(false);

      const handleChange = (field, value) => {
        setConfig((prev) => ({ ...prev, [field]: value }));
      };

      const toggleTool = (toolId) => {
        setConfig((prev) => {
          const list = prev.disabledTools || [];
          const next = list.includes(toolId) ? list.filter((t) => t !== toolId) : [...list, toolId];
          return { ...prev, disabledTools: next };
        });
      };

      const getBaseUrl = (url) => {
        let base = (url || '').trim();
        base = base.replace(/\/mcp\/?$/i, '').replace(/\/+$/, '');
        return base || 'https://vk.tide.red';
      };

      const handleTest = async () => {
        setTesting(true);
        setProbeReport(null);
        const base = getBaseUrl(config.endpointUrl);
        const start = Date.now();
        const fetchFn = typeof window !== 'undefined' && window.fetch ? window.fetch.bind(window) : fetch;

        const headers = { 'Content-Type': 'application/json' };
        if (config.userKey) headers['Authorization'] = `Bearer ${config.userKey}`;
        if (config.agentId) headers['X-Agent-ID'] = config.agentId;

        try {
          const res = await fetchFn(`${base}/api/v1/system/client-capabilities?plugin_id=openviking-ops&probe=full`, {
            headers,
            signal: AbortSignal.timeout(6000),
          });
          const totalLatency = Date.now() - start;

          if (res.ok) {
            const data = await res.json();
            setCaps(data);
            saveCaps(data);
            setProbeReport({
              ok: true,
              totalLatency,
              version: data.version || '1.0.1',
              toolsCount: data.total_authorized_tools || data.plugins?.[0]?.tools?.length || 17,
              hooksCount: data.hooks?.length || 2,
              role: data.role || 'user',
              probes: data.probes || {},
            });
          } else {
            setProbeReport({
              ok: false,
              totalLatency,
              status: res.status,
              error: `HTTP ${res.status} 鉴权或服务拒绝 (${res.statusText || 'Error'})`,
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
        saveConfig(config);
        setTimeout(() => {
          setSaving(false);
          setSaveToast({ ok: true, msg: '配置已持久化保存，将在下次会话原子生效' });
          setTimeout(() => setSaveToast(null), 3500);
        }, 300);
      };

      const toolsList = caps?.plugins?.[0]?.tools || [];

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
        // 头部
        h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--dsw-alias-border-l1, rgba(0,0,0,0.08))', paddingBottom: '10px' } },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
            h('span', { style: { fontSize: '18px' } }, '🛡️'),
            h('div', null,
              h('div', { style: { fontWeight: '600', fontSize: '13px' } }, 'OpenViking 系统运维治理插件'),
              h('div', { style: { fontSize: '11px', color: '#64748b' } }, 'dsh-plugin-openviking-ops · 专属解耦通信桥梁')
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
              fontWeight: '500',
              cursor: testing ? 'not-allowed' : 'pointer',
            },
          }, testing ? '探测中...' : '⚡ 连通性测试')
        ),
        // 探针报告条
        probeReport
          ? h('div', {
              style: {
                margin: '10px 0',
                padding: '8px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                background: probeReport.ok ? 'rgba(6, 182, 212, 0.08)' : 'rgba(244, 63, 94, 0.08)',
                border: `1px solid ${probeReport.ok ? '#0891b2' : '#e11d48'}`,
                color: probeReport.ok ? '#0891b2' : '#e11d48',
              },
            },
            probeReport.ok
              ? `✅ 连接成功 · 延迟 ${probeReport.totalLatency}ms · 服务端版本 v${probeReport.version} · 鉴权身份: ${probeReport.role} (就绪 ${probeReport.toolsCount} 项工具 / ${probeReport.hooksCount} 项 Hook)`
              : `❌ 连接失败 · ${probeReport.error}`
            )
          : null,
        // 表单字段组
        h('div', { style: { marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' } },
          // 接口地址
          h('div', null,
            h('div', { style: { display: 'flex', justifyContent: 'space-between', marginBottom: '4px' } },
              h('label', { style: { fontWeight: '500' } }, 'OpenViking 服务端接口地址:'),
              h('div', { style: { display: 'flex', gap: '6px' } },
                h('button', {
                  type: 'button',
                  onClick: () => handleChange('endpointUrl', 'https://vk.tide.red'),
                  style: { fontSize: '11px', padding: '1px 6px', background: config.endpointUrl.includes('vk.tide.red') ? '#0891b2' : 'transparent', color: config.endpointUrl.includes('vk.tide.red') ? '#fff' : '#0891b2', border: '1px solid #0891b2', borderRadius: '4px', cursor: 'pointer' }
                }, '公网 vk.tide.red'),
                h('button', {
                  type: 'button',
                  onClick: () => handleChange('endpointUrl', 'http://127.0.0.1:1933'),
                  style: { fontSize: '11px', padding: '1px 6px', background: config.endpointUrl.includes('127.0.0.1') ? '#0891b2' : 'transparent', color: config.endpointUrl.includes('127.0.0.1') ? '#fff' : '#0891b2', border: '1px solid #0891b2', borderRadius: '4px', cursor: 'pointer' }
                }, '本地 127.0.0.1')
              )
            ),
            h('input', {
              type: 'text',
              value: config.endpointUrl,
              onChange: (e) => handleChange('endpointUrl', e.target.value),
              placeholder: '例如 https://vk.tide.red 或 http://127.0.0.1:1933',
              style: { width: '100%', boxSizing: 'border-box', padding: '6px 8px', fontSize: '12px', fontFamily: 'monospace', borderRadius: '6px', border: '1px solid var(--dsw-alias-border-l2, rgba(0,0,0,0.15))', background: 'rgba(0,0,0,0.02)' },
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
                placeholder: '在 Web Studio 用户管理复制您的专属 User Key',
                style: { flex: 1, boxSizing: 'border-box', padding: '6px 8px', fontSize: '12px', fontFamily: 'monospace', borderRadius: '6px', border: '1px solid var(--dsw-alias-border-l2, rgba(0,0,0,0.15))', background: 'rgba(0,0,0,0.02)' },
              }),
              h('button', {
                type: 'button',
                onClick: () => setShowKey(!showKey),
                style: { padding: '0 10px', borderRadius: '6px', border: '1px solid var(--dsw-alias-border-l2, rgba(0,0,0,0.15))', background: 'rgba(0,0,0,0.04)', fontSize: '12px', cursor: 'pointer' },
              }, showKey ? '隐藏' : '显示')
            )
          )
        ),
        // 专属能力清单呈现
        h('div', { style: { marginTop: '12px', padding: '8px 10px', background: 'rgba(6, 182, 212, 0.03)', border: '1px solid rgba(6, 182, 212, 0.18)', borderRadius: '6px' } },
          h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' } },
            h('span', { style: { fontWeight: '600', color: '#0891b2' } }, `专属能力: ${toolsList.length || 17} 工具 · ${caps?.hooks?.length || 2} Hooks`),
            h('button', {
              type: 'button',
              onClick: () => setShowToolsList(!showToolsList),
              style: { background: 'transparent', border: 'none', color: '#0891b2', cursor: 'pointer', fontSize: '12px' },
            }, showToolsList ? '收起清单 ▲' : '查看工具清单 ▼')
          ),
          showToolsList && toolsList.length > 0
            ? h('div', { style: { marginTop: '8px', maxHeight: '180px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' } },
                toolsList.map(t => h('div', { key: t.id, style: { fontSize: '12px', color: '#64748b', display: 'flex', justifyContent: 'space-between' } },
                  h('span', { style: { fontFamily: 'monospace', color: '#0f1115' } }, t.name || t.id),
                  h('span', null, t.description)
                ))
              )
            : null
        ),
        // 保存按钮
        h('div', { style: { marginTop: '14px', display: 'flex', justifyContent: 'flex-end', gap: '8px' } },
          h('button', {
            type: 'button',
            onClick: handleSave,
            disabled: saving,
            style: {
              background: '#0891b2',
              color: '#ffffff',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              fontWeight: '600',
              fontSize: '12px',
              cursor: saving ? 'not-allowed' : 'pointer',
            },
          }, saving ? '保存校验中...' : '💾 保存配置')
        ),
        // 保存反馈 Toast
        saveToast
          ? h('div', {
              style: {
                marginTop: '10px',
                padding: '8px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                background: saveToast.ok ? 'rgba(6, 182, 212, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                border: `1px solid ${saveToast.ok ? '#0891b2' : '#e11d48'}`,
                color: saveToast.ok ? '#0891b2' : '#e11d48',
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
              key: 'dsh-plugin-openviking-ops',
            },
            DshPluginOpenvikingOpsPanel
        )
      );
      if ('dsh-plugin-openviking-ops' === 'dsh-plugin-openviking-memory') {
        ctx.slots.inject('plugins.bundle.config', () =>
          ctx.slots.register(
              {
                name: 'plugins.bundle.config',
                key: 'dsh-plugin-openviking',
              },
              DshPluginOpenvikingOpsPanel
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
