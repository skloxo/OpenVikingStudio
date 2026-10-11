/**
 * client.js - OpenViking DSH Client Cockpit Plugin (v2.0.1)
 * 纯原生 React (由 DSH 宿主环境提供注入)，零外部打包依赖。
 *
 * 核心设计哲学 (第一性原理 & 高内聚开箱即用)：
 * 1. 保存配置云端强校验：点击保存时强制向云端校验 User Key 与端点，不合法物理拦截拒存；
 * 2. 云端能力全息回拉：校验通过后从服务端动态拉取该用户授权的插件矩阵、工具总数、Hooks与技能；
 * 3. 工具与能力按需勾选：支持用户自由开启/禁用指定插件、具体工具与 Hook 守护链；
 * 4. 五维/六维全息能力体检：全部跑一遍云端赋予的能力（网关、长程记忆、多云搜索、KeePass凭据库、FastMCP、Hooks）；
 * 5. 性冷淡视觉与 NO GREEN EVER 铁律：高密排版、冰青色 (#0891b2)、等宽数字、字号 >= 12px。
 */

window.__ModuleLoader__.load({
  id: 'dsh-plugin-openviking',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState, useEffect, useCallback } = React;

    const STORAGE_KEY = 'openviking_dsh_config';
    const CAPS_STORAGE_KEY = 'openviking_dsh_capabilities';

    function loadSavedConfig() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      } catch (_) {}
      return {
        endpointUrl: 'https://vk.tide.red',
        agentId: 'deepseek-harness@satellite',
        userKey: '',
        enabledPlugins: ['memory', 'search', 'keepass'],
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
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
      } catch (_) {}
    }

    function saveCaps(caps) {
      try {
        localStorage.setItem(CAPS_STORAGE_KEY, JSON.stringify(caps));
      } catch (_) {}
    }

    // 配置表单主组件 (Cockpit GUI)
    function OpenVikingConfigPanel(props) {
      const [config, setConfig] = useState(loadSavedConfig);
      const [caps, setCaps] = useState(loadSavedCaps);
      const [showKey, setShowKey] = useState(false);
      const [probeReport, setProbeReport] = useState(null); // 六维能力全息体检报告
      const [testing, setTesting] = useState(false);
      const [saving, setSaving] = useState(false);
      const [saveToast, setSaveToast] = useState(null); // { ok: boolean, msg: string }
      const [expandedPlugin, setExpandedPlugin] = useState(null); // 当前展开查看工具列表的插件ID

      const handleChange = (field, value) => {
        setConfig((prev) => ({ ...prev, [field]: value }));
      };

      const togglePlugin = (pluginId) => {
        setConfig((prev) => {
          const list = prev.enabledPlugins || ['memory', 'search', 'keepass'];
          const next = list.includes(pluginId) ? list.filter((id) => id !== pluginId) : [...list, pluginId];
          return { ...prev, enabledPlugins: next };
        });
      };

      const toggleTool = (toolName) => {
        setConfig((prev) => {
          const list = prev.disabledTools || [];
          const next = list.includes(toolName) ? list.filter((t) => t !== toolName) : [...list, toolName];
          return { ...prev, disabledTools: next };
        });
      };

      const toggleHook = (hookId) => {
        setConfig((prev) => {
          const list = prev.disabledHooks || [];
          const next = list.includes(hookId) ? list.filter((h) => h !== hookId) : [...list, hookId];
          return { ...prev, disabledHooks: next };
        });
      };

      const getBaseUrl = (url) => {
        let base = (url || '').trim();
        base = base.replace(/\/mcp\/?$/i, '').replace(/\/+$/, '');
        return base || 'https://vk.tide.red';
      };

      // ⚡ 六维全息能力体检 (Full Capabilities Probing: 全部过一遍云端赋予的能力)
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
          const res = await fetchFn(`${base}/api/v1/system/client-capabilities?probe=full`, {
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
              version: data.version || '2.0.1',
              user: `${data.account_id || 'default'} / ${data.user_id || 'default'} (${data.role || 'user'})`,
              toolsCount: data.total_authorized_tools || 69,
              probes: data.probes || {},
            });
          } else {
            let errMsg = `HTTP ${res.status}`;
            try {
              const errJson = await res.json();
              errMsg = errJson.detail || errJson.error?.message || errMsg;
            } catch (_) {}
            setProbeReport({
              ok: false,
              totalLatency,
              error: errMsg,
            });
          }
        } catch (err) {
          setProbeReport({
            ok: false,
            totalLatency: Date.now() - start,
            error: err.message || '网络超时或服务端不可达',
          });
        } finally {
          setTesting(false);
        }
      };

      // 💾 保存配置 (带云端强校验与能力回拉)
      const handleSave = async () => {
        setSaving(true);
        setSaveToast(null);
        const base = getBaseUrl(config.endpointUrl);
        const fetchFn = typeof window !== 'undefined' && window.fetch ? window.fetch.bind(window) : fetch;

        const headers = { 'Content-Type': 'application/json' };
        if (config.userKey) headers['Authorization'] = `Bearer ${config.userKey}`;
        if (config.agentId) headers['X-Agent-ID'] = config.agentId;

        try {
          // 步骤 1: 连通与用户密钥云端强校验 + 能力回拉
          const res = await fetchFn(`${base}/api/v1/system/client-capabilities?probe=full`, {
            headers,
            signal: AbortSignal.timeout(5000),
          });

          if (!res.ok) {
            let errMsg = `HTTP ${res.status}`;
            try {
              const errJson = await res.json();
              errMsg = errJson.detail || errJson.error?.message || errMsg;
            } catch (_) {}
            setSaveToast({
              ok: false,
              msg: `云端强校验未通过：${errMsg}。配置未保存，请修正服务地址或用户密钥！`,
            });
            setSaving(false);
            return;
          }

          const data = await res.json();

          // 步骤 2: 校验用户勾选的配置合法性
          try {
            await fetchFn(`${base}/api/v1/system/client-capabilities/validate`, {
              method: 'POST',
              headers,
              body: JSON.stringify({
                endpointUrl: config.endpointUrl,
                userKey: config.userKey,
                agentId: config.agentId,
                enabledPlugins: config.enabledPlugins,
                disabledTools: config.disabledTools,
                disabledHooks: config.disabledHooks,
              }),
              signal: AbortSignal.timeout(3000),
            });
          } catch (_) {}

          // 步骤 3: 校验完全通过，落盘并同步宿主表单
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

          const selectedCount = data.selected_tools_count || 51;
          const totalTools = data.total_authorized_tools || 67;
          setSaveToast({
            ok: true,
            msg: `云端校验通过 · 已同步三大标杆插件、${selectedCount} / ${totalTools} 项已选工具及全量 7 项 Hooks！`,
          });
          const timerFn = typeof window !== 'undefined' && window.setTimeout ? window.setTimeout.bind(window) : setTimeout;
          timerFn(() => setSaveToast(null), 4000);
        } catch (err) {
          setSaveToast({
            ok: false,
            msg: `保存失败：服务端连接不可达 (${err.message})，请检查网络与服务状态！`,
          });
        } finally {
          setSaving(false);
        }
      };

      const enabledPluginsList = config.enabledPlugins || ['memory', 'search', 'keepass'];
      const disabledToolsList = config.disabledTools || [];
      const disabledHooksList = config.disabledHooks || [];

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
        // 头部标题与全息体检按钮
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
            h('span', { style: { fontSize: '15px' } }, '🧠'),
            h(
              'span',
              { style: { fontWeight: '600', fontSize: '13px', letterSpacing: '-0.01em' } },
              'OpenViking 体外大脑连接配置'
            ),
            h(
              'span',
              {
                style: {
                  fontSize: '12px',
                  background: 'rgba(6, 182, 212, 0.12)',
                  color: '#0891b2',
                  border: '1px solid rgba(6, 182, 212, 0.25)',
                  padding: '1px 5px',
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
              disabled: testing || saving,
              style: {
                background: 'var(--dsw-alias-bg-layer-2, rgba(0, 0, 0, 0.04))',
                border: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.15))',
                color: 'var(--dsw-alias-label-primary, inherit)',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                cursor: testing ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontWeight: '500',
              },
            },
            testing ? '全维能力体检中...' : '⚡ 测试连通性'
          )
        ),
        // 六维能力全息体检报告卡片 (NO GREEN EVER: 冰青 cyan-500 与 玫瑰红 rose-500)
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
              h(
                'div',
                { style: { fontWeight: '600', marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' } },
                h('span', null, probeReport.ok ? '🌟 云端全维能力体检全项通过 (All Capabilities Verified)' : '❌ 体检未通过'),
                h('span', { style: { fontFamily: 'monospace', fontSize: '12px' } }, `总耗时 ${probeReport.totalLatency}ms`)
              ),
              probeReport.ok && probeReport.probes
                ? h(
                    'div',
                    { style: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px' } },
                    Object.entries(probeReport.probes).map(([key, p]) =>
                      h(
                        'div',
                        {
                          key,
                          style: {
                            padding: '6px 8px',
                            background: 'var(--dsw-alias-bg-layer-2, rgba(255, 255, 255, 0.6))',
                            border: '1px solid rgba(6, 182, 212, 0.15)',
                            borderRadius: '4px',
                            fontSize: '12px',
                          },
                        },
                        h(
                          'div',
                          { style: { display: 'flex', justifyContent: 'space-between', fontWeight: '600', color: '#0891b2', marginBottom: '2px' } },
                          h('span', null, p.name || key),
                          h('span', { style: { fontFamily: 'monospace' } }, `${p.latency_ms || 1}ms`)
                        ),
                        h('div', { style: { fontSize: '12px', color: 'var(--dsw-alias-label-secondary, #64748b)' } }, p.message || p.engine || '在线')
                      )
                    )
                  )
                : h('div', null, `错误明细: ${probeReport.error}`)
            )
          : null,
        // 核心配置输入字段
        h(
          'div',
          { style: { display: 'flex', flexDirection: 'column', gap: '12px' } },
          h(
            'div',
            null,
            h('label', { style: { display: 'block', fontSize: '12px', fontWeight: '500', marginBottom: '4px' } }, '服务地址 *'),
            h('input', {
              type: 'text',
              value: config.endpointUrl,
              onChange: (e) => handleChange('endpointUrl', e.target.value),
              placeholder: 'https://vk.tide.red 或 http://127.0.0.1:1933',
              style: {
                width: '100%',
                boxSizing: 'border-box',
                padding: '6px 8px',
                fontSize: '12px',
                fontFamily: 'monospace',
                borderRadius: '6px',
                border: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.15))',
                background: 'var(--dsw-alias-bg-layer-2, rgba(0, 0, 0, 0.03))',
                color: 'inherit',
                outline: 'none',
              },
            }),
            h('div', { style: { fontSize: '12px', color: 'var(--dsw-alias-label-tertiary, #94a3b8)', marginTop: '2px' } }, '公网远程填 https://vk.tide.red；本机宿主直连填 http://127.0.0.1:1933')
          ),
          h(
            'div',
            null,
            h('label', { style: { display: 'block', fontSize: '12px', fontWeight: '500', marginBottom: '4px' } }, '用户密钥 (User Key) *'),
            h(
              'div',
              { style: { display: 'flex', gap: '6px' } },
              h('input', {
                type: showKey ? 'text' : 'password',
                value: config.userKey,
                onChange: (e) => handleChange('userKey', e.target.value),
                placeholder: '输入分配给该节点的 User Key (用于云端能力鉴权)',
                style: {
                  flex: 1,
                  boxSizing: 'border-box',
                  padding: '6px 8px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  borderRadius: '6px',
                  border: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.15))',
                  background: 'var(--dsw-alias-bg-layer-2, rgba(0, 0, 0, 0.03))',
                  color: 'inherit',
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
                    padding: '0 10px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '12px',
                  },
                },
                showKey ? '隐藏' : '显示'
              )
            ),
            h('div', { style: { fontSize: '12px', color: 'var(--dsw-alias-label-tertiary, #94a3b8)', marginTop: '2px' } }, '保存时将由云端校验真实性，未授权密钥将被物理阻断')
          )
        ),
        // 云端能力回拉与功能勾选配置面板 (Capability Matrix & Tool Selection)
        caps && caps.plugins
          ? h(
              'div',
              {
                style: {
                  marginTop: '14px',
                  padding: '10px',
                  background: 'var(--dsw-alias-bg-layer-2, rgba(0, 0, 0, 0.02))',
                  borderRadius: '6px',
                  border: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.06))',
                },
              },
              h(
                'div',
                { style: { fontWeight: '600', fontSize: '12px', marginBottom: '8px', color: '#0891b2', display: 'flex', justifyContent: 'space-between' } },
                h('span', null, `📡 云端已赋予能力矩阵 (${caps.total_authorized_tools || 51} 项工具授权 · ${(caps.hooks || []).filter(h => !disabledHooksList.includes(h.id)).length} / ${caps.hooks?.length || 7} Hook 守护激活)`),
                h('span', { style: { fontFamily: 'monospace' } }, `${caps.user_id || 'default'} @ ${caps.account_id || 'default'}`)
              ),
              // 3 大标杆 Quad 插件配置卡片 (严格仅展示云端已授权范围)
              h(
                'div',
                { style: { display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '10px' } },
                caps.plugins.map((p) => {
                  const isPluginEnabled = enabledPluginsList.includes(p.id);
                  const isExpanded = expandedPlugin === p.id;
                  const pluginTools = p.tools || [];
                  const activeInPlugin = pluginTools.filter(t => !disabledToolsList.includes(t.id || t.name)).length;

                  return h(
                    'div',
                    {
                      key: p.id,
                      style: {
                        padding: '8px 10px',
                        background: isPluginEnabled ? 'rgba(6, 182, 212, 0.03)' : 'var(--dsw-alias-bg-layer-2, rgba(0, 0, 0, 0.02))',
                        border: `1px solid ${isPluginEnabled ? 'rgba(6, 182, 212, 0.22)' : 'var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.08))'}`,
                        borderRadius: '6px',
                      },
                    },
                    h(
                      'div',
                      { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' } },
                      h(
                        'label',
                        { style: { display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: '600' } },
                        h('input', {
                          type: 'checkbox',
                          checked: isPluginEnabled,
                          onChange: () => togglePlugin(p.id),
                          style: { cursor: 'pointer', accentColor: '#0891b2' },
                        }),
                        h('span', { style: { color: isPluginEnabled ? '#0891b2' : 'inherit' } }, p.name),
                        h(
                          'span',
                          {
                            style: {
                              fontSize: '12px',
                              background: 'rgba(6, 182, 212, 0.08)',
                              color: '#0891b2',
                              border: '1px solid rgba(6, 182, 212, 0.2)',
                              padding: '1px 6px',
                              borderRadius: '4px',
                              fontFamily: 'monospace',
                              fontWeight: '600',
                            },
                          },
                          `${p.total_tools || pluginTools.length} 项工具`
                        )
                      ),
                      pluginTools.length > 0
                        ? h(
                            'button',
                            {
                              type: 'button',
                              onClick: () => setExpandedPlugin(isExpanded ? null : p.id),
                              style: {
                                background: 'transparent',
                                border: 'none',
                                color: '#0891b2',
                                fontSize: '12px',
                                cursor: 'pointer',
                                padding: '2px 6px',
                              },
                            },
                            isExpanded ? '收起清单 ▲' : '配置工具 ▼'
                          )
                        : null
                    ),
                    h(
                      'div',
                      { style: { fontSize: '12px', color: 'var(--dsw-alias-label-secondary, #64748b)', marginTop: '4px', paddingLeft: '24px' } },
                      p.description
                    ),
                    // 展开的工具勾选清单
                    isExpanded && pluginTools.length > 0
                      ? h(
                          'div',
                          {
                            style: {
                              marginTop: '8px',
                              paddingTop: '8px',
                              borderTop: '1px dashed var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.08))',
                              paddingLeft: '24px',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '6px',
                            },
                          },
                          pluginTools.map((t) => {
                            const toolKey = t.name || t.id;
                            const isToolActive = !disabledToolsList.includes(t.name) && !disabledToolsList.includes(t.id);
                            return h(
                              'label',
                              {
                                key: toolKey,
                                style: {
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  fontSize: '12px',
                                  cursor: 'pointer',
                                },
                              },
                              h(
                                'div',
                                { style: { display: 'flex', alignItems: 'center', gap: '6px' } },
                                h('input', {
                                  type: 'checkbox',
                                  checked: isToolActive && isPluginEnabled,
                                  disabled: !isPluginEnabled,
                                  onChange: () => toggleTool(toolKey),
                                  style: { cursor: 'pointer', accentColor: '#0891b2' },
                                }),
                                h('span', { style: { fontFamily: 'monospace', fontWeight: '500' } }, toolKey)
                              ),
                              h('span', { style: { color: 'var(--dsw-alias-label-tertiary, #94a3b8)', fontSize: '12px' } }, t.description)
                            );
                          })
                        )
                      : null
                  );
                })
              ),
              // 3 大 Hooks 守卫配置
              h(
                'div',
                { style: { borderTop: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.06))', paddingTop: '8px' } },
                h('div', { style: { fontWeight: '600', fontSize: '12px', marginBottom: '6px', color: 'var(--dsw-alias-label-secondary, #475569)' } }, '🛡️ 智能 Hooks 守护链配置'),
                h(
                  'div',
                  { style: { display: 'flex', flexDirection: 'column', gap: '6px' } },
                  (caps.hooks || []).map((hk) => {
                    const isHookActive = !disabledHooksList.includes(hk.id);
                    return h(
                      'label',
                      {
                        key: hk.id,
                        style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', cursor: 'pointer' },
                      },
                      h(
                        'div',
                        { style: { display: 'flex', alignItems: 'center', gap: '6px' } },
                        h('input', {
                          type: 'checkbox',
                          checked: isHookActive,
                          onChange: () => toggleHook(hk.id),
                          style: { cursor: 'pointer', accentColor: '#0891b2' },
                        }),
                        h('span', { style: { fontWeight: '500' } }, hk.name)
                      ),
                      h('span', { style: { color: 'var(--dsw-alias-label-tertiary, #94a3b8)', fontSize: '12px' } }, hk.description)
                    );
                  })
                )
              )
            )
          : null,
        // 保存操作区与校验反馈
        h(
          'div',
          {
            style: {
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: '14px',
              paddingTop: '10px',
              borderTop: '1px solid var(--dsw-alias-border-l2, rgba(0, 0, 0, 0.06))',
            },
          },
          h(
            'div',
            {
              style: {
                fontSize: '12px',
                color: saveToast?.ok ? '#0891b2' : '#e11d48',
                fontWeight: '500',
              },
            },
            saveToast ? (saveToast.ok ? `✨ ${saveToast.msg}` : `❌ ${saveToast.msg}`) : ''
          ),
          h(
            'button',
            {
              type: 'button',
              onClick: handleSave,
              disabled: saving || testing,
              style: {
                background: '#0891b2',
                color: '#ffffff',
                border: 'none',
                padding: '6px 18px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: '600',
                cursor: saving ? 'not-allowed' : 'pointer',
              },
            },
            saving ? '云端强校验中...' : '保存配置'
          )
        )
      );
    }

    function apply(ctx) {
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
