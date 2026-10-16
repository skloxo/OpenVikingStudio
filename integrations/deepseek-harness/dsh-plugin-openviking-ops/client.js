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
              version: data.version || '1.0.0',
              user: `${data.account_id || 'default'} / ${data.user_id || 'default'} (${data.role || 'user'})`,
              toolsCount: data.total_authorized_tools || 17,
              probes: data.probes || {},
            });
          } else {
            let errMsg = `HTTP ${res.status}`;
            try {
              const errJson = await res.json();
              errMsg = errJson.detail || errJson.error?.message || errMsg;
            } catch (_) {}
            setProbeReport({ ok: false, totalLatency, error: errMsg });
          }
        } catch (err) {
          setProbeReport({ ok: false, totalLatency: Date.now() - start, error: err.message || '网络超时或服务端不可达' });
        } finally {
          setTesting(false);
        }
      };

      const handleSave = async () => {
        setSaving(true);
        setSaveToast(null);
        const base = getBaseUrl(config.endpointUrl);
        const fetchFn = typeof window !== 'undefined' && window.fetch ? window.fetch.bind(window) : fetch;

        const headers = { 'Content-Type': 'application/json' };
        if (config.userKey) headers['Authorization'] = `Bearer ${config.userKey}`;
        if (config.agentId) headers['X-Agent-ID'] = config.agentId;

        try {
          const res = await fetchFn(`${base}/api/v1/system/client-capabilities?plugin_id=openviking-ops&probe=full`, {
            headers,
            signal: AbortSignal.timeout(5000),
          });

          if (!res.ok) {
            let errMsg = `HTTP ${res.status}`;
            try {
              const errJson = await res.json();
              errMsg = errJson.detail || errJson.error?.message || errMsg;
            } catch (_) {}
            setSaveToast({ ok: false, msg: `云端鉴权未通过：${errMsg}。请修正服务地址或用户密钥！` });
            setSaving(false);
            return;
          }

          const data = await res.json();
          setCaps(data);
          saveCaps(data);
          saveConfig(config);

          if (props?.form?.mutate) {
            try {
              props.form.mutate([
                { op: 'replace', path: '/endpointUrl', value: config.endpointUrl },
                { op: 'replace', path: '/agentId', value: config.agentId },
                { op: 'replace', path: '/userKey', value: config.userKey },
              ]);
            } catch (_) {}
          }

          const toolsTotal = data.total_authorized_tools || 17;
          const enabledCount = toolsTotal - (config.disabledTools || []).length;
          setSaveToast({
            ok: true,
            msg: `配置保存成功 · 已同步 ${enabledCount} / ${toolsTotal} 项已授权工具及专属 Hooks！`,
          });
          setTimeout(() => setSaveToast(null), 4000);
        } catch (err) {
          setSaveToast({ ok: false, msg: `保存失败：服务端连接不可达 (${err.message})` });
        } finally {
          setSaving(false);
        }
      };

      const disabledList = config.disabledTools || [];
      const pluginObj = (caps?.plugins || [])[0];
      const toolsList = pluginObj?.tools || [];

      return h(
        'div',
        {
          style: {
            background: 'var(--dsw-alias-settings-card-fill, var(--dsw-alias-button-elevated-fill, #ffffff))',
            border: '1px solid var(--dsw-alias-settings-card-stroke, var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.08)))',
            borderRadius: '6px',
            padding: '14px',
            marginBottom: '14px',
            fontFamily: 'var(--dsw-font-family, system-ui, -apple-system, sans-serif)',
            fontSize: '12px',
            color: 'var(--dsw-alias-label-primary, #0f1115)',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.03)',
          },
        },
        // 头部
        h(
          'div',
          {
            style: {
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '12px',
              borderBottom: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.06))',
              paddingBottom: '8px',
            },
          },
          h(
            'div',
            { style: { display: 'flex', alignItems: 'center', gap: '6px' } },
            h('span', { style: { fontSize: '15px' } }, '🛡️'),
            h('span', { style: { fontWeight: '600', fontSize: '13px', letterSpacing: '-0.01em' } }, 'OpenViking 系统运维治理插件'),
            h('span', { style: { fontSize: '12px', background: 'rgba(6, 182, 212, 0.12)', color: '#0891b2', border: '1px solid rgba(6, 182, 212, 0.25)', padding: '1px 5px', borderRadius: '4px', fontFamily: 'monospace', fontWeight: '600' } }, 'SSOT')
          ),
          h('button', {
            type: 'button',
            onClick: handleTest,
            disabled: testing || saving,
            style: {
              background: 'var(--dsw-alias-bg-layer-2, rgba(0, 0, 0, 0.04))',
              border: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.15))',
              color: 'var(--dsw-alias-label-primary, inherit)',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '12px',
              cursor: testing ? 'not-allowed' : 'pointer',
              fontWeight: '500',
            },
          }, testing ? '体检中...' : '⚡ 测试连通性')
        ),
        // 体检卡片
        probeReport
          ? h(
              'div',
              {
                style: {
                  padding: '10px 12px',
                  borderRadius: '6px',
                  marginBottom: '12px',
                  fontSize: '12px',
                  background: probeReport.ok ? 'rgba(6, 182, 212, 0.05)' : 'rgba(244, 63, 94, 0.05)',
                  border: `1px solid ${probeReport.ok ? 'rgba(6, 182, 212, 0.28)' : 'rgba(244, 63, 94, 0.28)'}`,
                  color: probeReport.ok ? '#0891b2' : '#e11d48',
                },
              },
              h('div', { style: { fontWeight: '600', marginBottom: '6px', display: 'flex', justifyContent: 'space-between' } },
                h('span', null, probeReport.ok ? '🌟 专属插件通道体检通过' : '❌ 连通失败'),
                h('span', { style: { fontFamily: 'monospace' } }, `${probeReport.totalLatency}ms`)
              ),
              probeReport.ok && probeReport.probes
                ? h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px' } },
                    Object.entries(probeReport.probes).map(([k, p]) =>
                      h('div', { key: k, style: { padding: '4px 6px', background: 'rgba(255, 255, 255, 0.6)', border: '1px solid rgba(6, 182, 212, 0.15)', borderRadius: '4px' } },
                        h('div', { style: { fontWeight: '600', color: '#0891b2' } }, p.name || k),
                        h('div', { style: { fontSize: '11px', color: '#64748b' } }, p.message || '就绪')
                      )
                    )
                  )
                : h('div', null, `原因: ${probeReport.error}`)
            )
          : null,
        // 表单字段
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: '10px' } },
          h('div', null,
            h('label', { style: { display: 'block', fontSize: '12px', fontWeight: '500', marginBottom: '3px' } }, '服务地址 *'),
            h('input', {
              type: 'text',
              value: config.endpointUrl,
              onChange: (e) => handleChange('endpointUrl', e.target.value),
              placeholder: 'https://vk.tide.red 或 http://127.0.0.1:1933',
              style: { width: '100%', boxSizing: 'border-box', padding: '6px 8px', fontSize: '12px', fontFamily: 'monospace', borderRadius: '6px', border: '1px solid var(--dsw-alias-border-l2, rgba(0,0,0,0.15))', background: 'rgba(0,0,0,0.02)' },
            })
          ),
          h('div', null,
            h('label', { style: { display: 'block', fontSize: '12px', fontWeight: '500', marginBottom: '3px' } }, '用户密钥 (User Key) *'),
            h('div', { style: { display: 'flex', gap: '6px' } },
              h('input', {
                type: showKey ? 'text' : 'password',
                value: config.userKey,
                onChange: (e) => handleChange('userKey', e.target.value),
                placeholder: '在 Web Studio 用户中心复制专属 User Key',
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
        // 能力呈现
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

    return {
      name: 'dsh-plugin-openviking-ops',
      ConfigPanel: DshPluginOpenvikingOpsPanel,
    };
  },
});
