/**
 * universal_dsh_client.js - OpenViking 通用 DSH 插件元数据渲染器模板
 * 100% 动态元数据驱动：动态渲染母本 README、服务端探针 MCP/Skill/Hook 矩阵。
 * 视觉铁律：NO GREEN EVER 🚫 (#0891b2 冰青 / #e11d48 玫瑰红)，字号 >= 12px，6px 微圆角。
 * 单一真相源：版本直连母本声明，禁止任何本地写死文案与脏缓存覆写。
 */

window.__ModuleLoader__.load({
  id: '__PLUGIN_ID__',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState, useEffect } = React;

    const PLUGIN_ID = '__PLUGIN_ID__';
    const CLIENT_VERSION = '__PLUGIN_VERSION__';
    const PLUGIN_NAME = '__PLUGIN_NAME__';
    const README_RAW = `__README_CONTENT__`;

    // 默认回退战地工具清单 (仅在无网络离线时兜底)
    const FALLBACK_TOOLS = [
      'openviking_find', 'openviking_search', 'openviking_read', 'openviking_write',
      'openviking_store', 'openviking_link', 'openviking_get_relations', 'openviking_unlink',
      'openviking_ls', 'openviking_tree', 'openviking_grep', 'openviking_glob',
      'openviking_code_outline', 'openviking_code_search', 'openviking_code_expand', 'openviking_diff'
    ];

    function UniversalDshPanel(props) {
      const [tab, setTab] = useState('overview');
      const [probe, setProbe] = useState({ ok: false, tools: FALLBACK_TOOLS, skills: [], hooks: [], latency: 0 });
      const [loading, setLoading] = useState(true);

      const config = props.config || {};
      const endpoint = (config.endpointUrl || 'http://127.0.0.1:1933').replace(/\/mcp$/, '');

      useEffect(() => {
        let mounted = true;
        const start = Date.now();
        fetch(`${endpoint}/api/v1/system/client-capabilities?plugin_id=${PLUGIN_ID}&probe=full`, {
          headers: config.userKey ? { 'Authorization': `Bearer ${config.userKey}` } : {},
          signal: AbortSignal.timeout(4000),
        })
          .then(res => res.ok ? res.json() : null)
          .then(data => {
            if (!mounted || !data) return;
            const toolList = Array.isArray(data.tools) && data.tools.length > 0
              ? data.tools.map(t => typeof t === 'string' ? t : (t.name || t.id))
              : FALLBACK_TOOLS;
            setProbe({
              ok: true,
              tools: toolList,
              skills: data.skills || [],
              hooks: data.hooks || [],
              latency: Date.now() - start,
              kernelVersion: data.kernel_version || data.version || '1.7.160'
            });
            setLoading(false);
          })
          .catch(() => {
            if (mounted) setLoading(false);
          });
        return () => { mounted = false; };
      }, [endpoint, config.userKey]);

      const tabs = [
        { key: 'overview', label: '概览' },
        { key: 'mcp', label: `MCP (${probe.tools.length})` },
        { key: 'skills', label: '技能' },
        { key: 'hooks', label: '钩子' },
        { key: 'config', label: '配置' }
      ];

      return h('div', {
        style: {
          padding: '14px 16px',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          fontSize: '12px',
          color: 'var(--dsw-alias-text-primary, #e2e8f0)',
          lineHeight: 1.5,
        }
      },
        // 1. 顶部状态横幅
        h('div', {
          style: {
            padding: '8px 12px',
            borderRadius: '6px',
            marginBottom: '14px',
            background: probe.ok ? 'rgba(8, 145, 178, 0.08)' : 'rgba(125, 125, 125, 0.08)',
            border: `1px solid ${probe.ok ? '#0891b2' : 'rgba(125, 125, 125, 0.2)'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '12px',
          }
        },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
            h('span', { style: { color: probe.ok ? '#0891b2' : '#94a3b8', fontWeight: '600' } },
              probe.ok ? '● 探针连接正常' : (loading ? '○ 正在连接服务...' : '○ 服务离线/未鉴权')
            ),
            h('span', { style: { opacity: 0.6 } }, `时延: ${probe.latency}ms`),
            h('span', { style: { opacity: 0.6 } }, `· 适配器: v${CLIENT_VERSION}`)
          ),
          h('div', { style: { fontFamily: 'monospace', opacity: 0.8 } },
            probe.ok ? `${probe.tools.length} 项战地工具就绪` : '--'
          )
        ),

        // 2. Tab 导航栏
        h('div', {
          style: {
            display: 'flex',
            gap: '4px',
            borderBottom: '1px solid var(--dsw-alias-border-l1, rgba(125, 125, 125, 0.15))',
            paddingBottom: '6px',
            marginBottom: '12px',
          }
        },
          tabs.map(t => h('button', {
            key: t.key,
            onClick: () => setTab(t.key),
            style: {
              background: tab === t.key ? 'rgba(8, 145, 178, 0.15)' : 'transparent',
              color: tab === t.key ? '#0891b2' : 'inherit',
              border: 'none',
              borderRadius: '6px',
              padding: '4px 12px',
              fontSize: '12px',
              fontWeight: tab === t.key ? '600' : 'normal',
              cursor: 'pointer',
            }
          }, t.label))
        ),

        // 3. Tab 内容区
        // [概览]：渲染母本 README
        tab === 'overview' && h('div', {
          style: {
            whiteSpace: 'pre-wrap',
            fontFamily: 'monospace',
            lineHeight: 1.6,
            opacity: 0.9,
            maxHeight: '400px',
            overflowY: 'auto',
            padding: '8px',
            background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.04))',
            borderRadius: '6px',
          }
        }, README_RAW),

        // [MCP 工具]：1:1 平铺 Badge
        tab === 'mcp' && h('div', {
          style: {
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: '6px',
            maxHeight: '400px',
            overflowY: 'auto',
          }
        },
          probe.tools.map((tool, idx) => h('div', {
            key: idx,
            style: {
              padding: '4px 8px',
              borderRadius: '6px',
              background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.05))',
              border: '1px solid var(--dsw-alias-border-l2, rgba(125, 125, 125, 0.12))',
              fontFamily: 'monospace',
              fontSize: '12px',
              color: '#0891b2',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }
          }, `⚡ ${tool}`))
        ),

        // [技能]：专家认知导轨
        tab === 'skills' && h('div', {
          style: { display: 'flex', flexDirection: 'column', gap: '8px' }
        },
          (probe.skills.length > 0 ? probe.skills : [{ name: `${PLUGIN_ID}-guide`, description: '专家认知导轨与操作手册' }]).map((s, idx) =>
            h('div', {
              key: idx,
              style: {
                padding: '8px 10px',
                borderRadius: '6px',
                background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.05))',
                border: '1px solid var(--dsw-alias-border-l2, rgba(125, 125, 125, 0.12))',
              }
            },
              h('div', { style: { fontFamily: 'monospace', fontWeight: '600', color: '#0891b2' } }, s.name || s.skill_id),
              h('div', { style: { marginTop: '2px', opacity: 0.85, fontSize: '12px' } }, s.description || s.desc)
            )
          )
        ),

        // [钩子]：生命周期守卫
        tab === 'hooks' && h('div', {
          style: { display: 'flex', flexDirection: 'column', gap: '8px' }
        },
          (probe.hooks.length > 0 ? probe.hooks : [{ id: 'pre_invocation', name: '跨会话记忆预取', triggerEvent: 'before_prompt' }]).map((hk, idx) =>
            h('div', {
              key: idx,
              style: {
                padding: '8px 10px',
                borderRadius: '6px',
                background: 'var(--dsw-alias-bg-l2, rgba(125, 125, 125, 0.05))',
                border: '1px solid var(--dsw-alias-border-l2, rgba(125, 125, 125, 0.12))',
              }
            },
              h('div', { style: { fontWeight: '600', color: '#0891b2' } }, hk.name || hk.id),
              h('div', { style: { opacity: 0.7, fontSize: '12px', marginTop: '2px' } }, `事件: ${hk.triggerEvent || hk.trigger_event || '自动拦截'}`)
            )
          )
        ),

        // [配置]：指引
        tab === 'config' && h('div', {
          style: { lineHeight: 1.6, opacity: 0.85, fontSize: '12px' }
        },
          h('p', null, '服务地址与 UserKey 可在上方配置面板直接调整。'),
          h('p', null, `当前端点: ${endpoint}`)
        ),

        // 4. 底部微弱版本声明
        h('div', {
          style: {
            marginTop: '16px',
            paddingTop: '8px',
            borderTop: '1px solid var(--dsw-alias-border-l1, rgba(125, 125, 125, 0.12))',
            textAlign: 'center',
            fontSize: '12px',
            opacity: 0.5,
          }
        }, `版本 ${CLIENT_VERSION}`)
      );
    }

    function apply(ctx) {
      ctx.slots.inject('plugins.bundle.config', () =>
        ctx.slots.register(
          {
            name: 'plugins.bundle.config',
            key: PLUGIN_ID,
          },
          UniversalDshPanel
        )
      );
    }

    return {
      inject: ['slots'],
      apply,
    };
  },
});