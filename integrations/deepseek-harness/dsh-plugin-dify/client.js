/**
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
          const res = await fetch(`${config.apiUrl.replace(/\/+$/, '')}/parameters`, {
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
