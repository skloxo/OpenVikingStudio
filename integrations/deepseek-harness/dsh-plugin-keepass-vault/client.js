/**
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
        kdbxPath: 'C:\\Users\\Skl\\.openviking\\vault.kdbx',
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
              placeholder: '例如 C:\Users\Skl\.openviking\vault.kdbx',
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
