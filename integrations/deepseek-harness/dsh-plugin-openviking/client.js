/**
 * client.js - OpenViking DSH Client Plugin
 * 纯原生 React (由 DSH 宿主提供)，无外部打包依赖。
 * 向 DSH Web 客户端注册：
 * 1. plugins.bundle.config: 插件包主详情页顶部的【OpenViking 核心协同配置】座舱面板；
 * 2. plugins.row.config: 单组件行（openviking）的专属配置面板；
 * 3. conversation.composer.dock: 对话输入框上方体外大脑状态指示微胶囊。
 */

window.__ModuleLoader__.load({
  id: 'dsh-plugin-openviking',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState, useEffect, useCallback } = React;

    const STORAGE_KEY = 'openviking_dsh_config';

    function loadSavedConfig() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      } catch (_) {}
      return {
        endpointUrl: 'http://127.0.0.1:1933/mcp',
        agentId: 'deepseek-harness@satellite',
        userKey: '',
        peer: 'deepseek-harness@satellite',
        enableMcp: true,
        enableHook: true,
      };
    }

    function saveConfig(cfg) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
      } catch (_) {}
    }

    // 配置表单主组件
    function OpenVikingConfigPanel(props) {
      const [config, setConfig] = useState(loadSavedConfig);
      const [showKey, setShowKey] = useState(false);
      const [testStatus, setTestStatus] = useState(null); // { ok: boolean, msg: string }
      const [testing, setTesting] = useState(false);
      const [savedToast, setSavedToast] = useState(false);

      const handleChange = (field, value) => {
        setConfig((prev) => ({ ...prev, [field]: value }));
      };

      const handleTest = async () => {
        setTesting(true);
        setTestStatus(null);
        try {
          let base = (config.endpointUrl || '').trim();
          base = base.replace(/\/mcp\/?$/i, '').replace(/\/+$/, '');
          if (!base) base = 'http://127.0.0.1:1933';

          const start = Date.now();
          const headers = { 'Content-Type': 'application/json' };
          if (config.userKey) {
            headers['Authorization'] = `Bearer ${config.userKey}`;
          }
          if (config.agentId) {
            headers['X-Agent-ID'] = config.agentId;
          }

          const fetchFn = typeof window !== 'undefined' && window.fetch ? window.fetch.bind(window) : fetch;
          const res = await fetchFn(`${base}/health`, {
            headers,
            signal: AbortSignal.timeout(3000),
          });
          const latency = Date.now() - start;

          if (res.ok) {
            const data = await res.json();
            // 进一步验证密钥是否能通过鉴权 (SSOT 真实性验证)
            let authMsg = '认证: 免密或本地信任';
            try {
              const authRes = await fetchFn(`${base}/api/v1/system/status`, {
                headers,
                signal: AbortSignal.timeout(3000),
              });
              if (!authRes.ok) {
                setTestStatus({
                  ok: false,
                  msg: `网络通畅但密钥校验失败 (HTTP ${authRes.status}): 填写的 User Key 无效或未授权`,
                });
                return;
              }
              authMsg = '认证: 真实密钥校验通过';
            } catch (_) {}

            setTestStatus({
              ok: true,
              msg: `连接成功 (v${data.version || '1.7'}) · 延迟 ${latency}ms · ${authMsg}`,
            });
          } else {
            setTestStatus({
              ok: false,
              msg: `连接失败: HTTP ${res.status} ${res.statusText}`,
            });
          }
        } catch (err) {
          setTestStatus({
            ok: false,
            msg: `连接不可达: ${err.message || '网络超时或服务端未启动'}`,
          });
        } finally {
          setTesting(false);
        }
      };

      const handleSave = () => {
        saveConfig(config);
        setSavedToast(true);
        const timerFn = typeof window !== 'undefined' && window.setTimeout ? window.setTimeout.bind(window) : setTimeout;
        timerFn(() => setSavedToast(false), 2500);

        // 如果宿主提供了 form.mutate，尝试回写
        if (props?.form?.mutate) {
          try {
            props.form.mutate([
              { op: 'replace', path: '/endpointUrl', value: config.endpointUrl },
              { op: 'replace', path: '/agentId', value: config.agentId },
              { op: 'replace', path: '/userKey', value: config.userKey },
            ]);
          } catch (_) {}
        }
      };

      return h(
        'div',
        {
          style: {
            background: 'var(--dsw-alias-settings-card-fill, var(--dsw-alias-button-elevated-fill, #ffffff))',
            border: '1px solid var(--dsw-alias-settings-card-stroke, var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.08)))',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '16px',
            fontFamily: 'var(--dsw-font-family, system-ui, -apple-system, sans-serif)',
            fontSize: '13px',
            color: 'var(--dsw-alias-label-primary, #0f1115)',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
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
              marginBottom: '14px',
              borderBottom: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.06))',
              paddingBottom: '10px',
            },
          },
          h(
            'div',
            { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
            h('span', { style: { fontSize: '16px' } }, '🧠'),
            h(
              'span',
              { style: { fontWeight: '600', fontSize: '14px', letterSpacing: '-0.01em', color: 'var(--dsw-alias-label-primary, inherit)' } },
              'OpenViking 体外大脑连接配置'
            ),
            h(
              'span',
              {
                style: {
                  fontSize: '11px',
                  background: 'rgba(6, 182, 212, 0.12)',
                  color: '#0891b2',
                  border: '1px solid rgba(6, 182, 212, 0.25)',
                  padding: '1px 6px',
                  borderRadius: '4px',
                  fontFamily: 'monospace',
                  fontWeight: '600',
                },
              },
              'SSOT'
            )
          ),
          h(
            'button',
            {
              type: 'button',
              onClick: handleTest,
              disabled: testing,
              style: {
                background: 'var(--dsw-alias-bg-layer-2, rgba(0, 0, 0, 0.04))',
                border: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.15))',
                color: 'var(--dsw-alias-label-primary, inherit)',
                padding: '4px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                cursor: testing ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontWeight: '500',
              },
            },
            testing ? '探测中...' : '⚡ 测试连通性'
          )
        ),
        // 测试结果状态条 (NO GREEN EVER)
        testStatus
          ? h(
              'div',
              {
                style: {
                  padding: '8px 12px',
                  borderRadius: '6px',
                  marginBottom: '14px',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: testStatus.ok
                    ? 'rgba(6, 182, 212, 0.08)'
                    : 'rgba(244, 63, 94, 0.08)',
                  border: `1px solid ${
                    testStatus.ok ? 'rgba(6, 182, 212, 0.3)' : 'rgba(244, 63, 94, 0.3)'
                  }`,
                  color: testStatus.ok ? '#0891b2' : '#e11d48',
                  fontWeight: '500',
                },
              },
              testStatus.ok ? '✅ ' : '❌ ',
              testStatus.msg
            )
          : null,
        // 表单字段列表
        h(
          'div',
          { style: { display: 'flex', flexDirection: 'column', gap: '14px' } },
          // 字段 1: 服务地址 (Service Address)
          h(
            'div',
            null,
            h(
              'label',
              {
                style: {
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: '500',
                  marginBottom: '4px',
                  color: 'var(--dsw-alias-label-secondary, #475569)',
                },
              },
              '服务地址 *'
            ),
            h('input', {
              type: 'text',
              value: config.endpointUrl,
              onChange: (e) => handleChange('endpointUrl', e.target.value),
              placeholder: 'https://vk.tide.red 或 http://127.0.0.1:1933',
              style: {
                width: '100%',
                boxSizing: 'border-box',
                padding: '8px 10px',
                fontSize: '13px',
                fontFamily: 'monospace',
                borderRadius: '6px',
                border: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.15))',
                background: 'var(--dsw-alias-bg-layer-2, rgba(0, 0, 0, 0.03))',
                color: 'var(--dsw-alias-label-primary, inherit)',
                outline: 'none',
              },
            }),
            h(
              'div',
              {
                style: {
                  fontSize: '11px',
                  color: 'var(--dsw-alias-label-tertiary, #94a3b8)',
                  marginTop: '4px',
                },
              },
              '公网远程填 https://vk.tide.red；本机宿主直连填 http://127.0.0.1:1933'
            )
          ),
          // 字段 2: userKey (用户密钥)
          h(
            'div',
            null,
            h(
              'label',
              {
                style: {
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: '500',
                  marginBottom: '4px',
                  color: 'var(--dsw-alias-label-secondary, #475569)',
                },
              },
              '用户密钥 (User Key) *'
            ),
              {
                style: {
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: '500',
                  marginBottom: '4px',
                  color: 'var(--dsw-alias-label-secondary, #475569)',
                },
              },
              '用户 API Key / User Key (userKey)'
            ),
            h(
              'div',
              { style: { display: 'flex', gap: '8px' } },
              h('input', {
                type: showKey ? 'text' : 'password',
                value: config.userKey,
                onChange: (e) => handleChange('userKey', e.target.value),
                placeholder: '留空则从环境变量或 .credentials.yaml 读取',
                style: {
                  flex: 1,
                  boxSizing: 'border-box',
                  padding: '8px 10px',
                  fontSize: '13px',
                  fontFamily: 'monospace',
                  borderRadius: '6px',
                  border: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.15))',
                  background: 'var(--dsw-alias-bg-layer-2, rgba(0, 0, 0, 0.03))',
                  color: 'var(--dsw-alias-label-primary, inherit)',
                  outline: 'none',
                },
              }),
              h(
                'button',
                {
                  type: 'button',
                  onClick: () => setShowKey(!showKey),
                  style: {
                    background: 'var(--dsw-alias-bg-layer-2, rgba(0, 0, 0, 0.04))',
                    border: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.15))',
                    color: 'var(--dsw-alias-label-secondary, #475569)',
                    padding: '0 12px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: '500',
                  },
                },
                showKey ? '隐藏' : '显示'
              )
            ),
            h(
              'div',
              {
                style: {
                  fontSize: '11px',
                  color: 'var(--dsw-alias-label-tertiary, #94a3b8)',
                  marginTop: '4px',
                },
              },
              '可留空，插件将自动检索 OPENVIKING_USER_KEY 环境变量或本地凭据中枢'
            )
          )
        ),
        // 底部保存条
        h(
          'div',
          {
            style: {
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: '16px',
              paddingTop: '12px',
              borderTop: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.06))',
            },
          },
          h(
            'div',
            { style: { fontSize: '12px', color: '#0891b2', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '500' } },
            savedToast ? '✨ 配置已成功保存并即时生效' : ''
          ),
          h(
            'button',
            {
              type: 'button',
              onClick: handleSave,
              style: {
                background: '#0891b2',
                color: '#ffffff',
                border: 'none',
                padding: '7px 20px',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: '600',
                cursor: 'pointer',
                boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1)',
                transition: 'background 0.2s ease',
              },
            },
            '保存配置'
          )
        )
      );
    }

    function apply(ctx) {
      // 官方唯一正统插槽：渲染在包详情页（PackageDetail）描述与组件列表之间 (SSOT，消灭重复)
      ctx.slots.inject('plugins.bundle.config', () =>
        ctx.slots.register(
          {
            name: 'plugins.bundle.config',
            key: 'dsh-plugin-openviking',
          },
          OpenVikingConfigPanel
        )
      );
    }

    return {
      inject: ['slots'],
      apply,
    };
  },
});
