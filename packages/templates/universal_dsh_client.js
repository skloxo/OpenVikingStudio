/**
 * universal_dsh_client.js - OpenViking 通用 DSH 插件座舱与配置面板模板
 * 100% 动态元数据与表单双轨驱动：支持服务端实时探测、端点与 UserKey 热配置、35 项全量战地工具矩阵。
 * 视觉铁律：NO GREEN EVER 🚫 (#0891b2 冰青 / #e11d48 玫瑰红)，字号 >= 12px，6px 微圆角，明亮/深色双主题高对比度。
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
    const STORAGE_KEY = `dsh_plugin_${PLUGIN_ID.replace(/-/g, '_')}_config`;

    // 35 项 FastMCP 全量战地工具清单 (分 7 大领域编组)
    const TOOL_CATEGORIES = [
      {
        cat: '🔍 语义与长程检索 (4)',
        tools: ['openviking_find', 'openviking_search', 'openviking_read', 'openviking_write']
      },
      {
        cat: '📁 知识图谱与资源 (8)',
        tools: ['openviking_store', 'openviking_link', 'openviking_get_relations', 'openviking_unlink', 'openviking_ls', 'openviking_tree', 'openviking_grep', 'openviking_glob']
      },
      {
        cat: '💻 代码感知与重构 (4)',
        tools: ['openviking_code_outline', 'openviking_code_search', 'openviking_code_expand', 'openviking_diff']
      },
      {
        cat: '🧠 认知与分层阅读 (4)',
        tools: ['openviking_smart_read', 'openviking_content_reduce', 'openviking_tokenshift_compress', 'openviking_privacy_mask']
      },
      {
        cat: '📋 自主工单与调度 (5)',
        tools: ['openviking_file_task_card', 'openviking_list_pending_cards', 'openviking_resolve_task_card', 'openviking_task_cards_summary', 'openviking_valet_handover']
      },
      {
        cat: '🎓 技能中心与自愈 (6)',
        tools: ['openviking_skills', 'openviking_audit_skills', 'openviking_auto_onboard_skills', 'openviking_get_onboard_queue_status', 'openviking_fix_skill', 'openviking_record_evolution_lesson']
      },
      {
        cat: '🛡️ 健康与运维感知 (4)',
        tools: ['openviking_health', 'openviking_tag', 'openviking_harness_probe', 'openviking_valet_ticket_status']
      }
    ];

    function loadSavedConfig() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY) || localStorage.getItem('dsh_plugin_openviking_memory_config');
        if (raw) {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === 'object') return parsed;
        }
      } catch (_) {}
      return {
        endpointUrl: 'https://vk.tide.red',
        userKey: '',
        agentId: 'deepseek-harness@satellite',
        peer: 'openviking-memory'
      };
    }

    function saveConfig(cfg) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
        localStorage.setItem('dsh_plugin_openviking_memory_config', JSON.stringify(cfg));
      } catch (_) {}
    }

    function UniversalDshPanel(props) {
      if (props && props.view === 'summary') {
        return null;
      }

      const [formConfig, setFormConfig] = useState(() => {
        const initial = loadSavedConfig();
        const pCfg = props?.config || {};
        return {
          endpointUrl: pCfg.endpointUrl || initial.endpointUrl || 'https://vk.tide.red',
          userKey: pCfg.userKey || initial.userKey || '',
          agentId: pCfg.agentId || initial.agentId || 'deepseek-harness@satellite',
          peer: pCfg.peer || initial.peer || 'openviking-memory'
        };
      });

      const [tab, setTab] = useState('config');
      const [showKey, setShowKey] = useState(false);
      const [probe, setProbe] = useState({ ok: false, latency: 0, toolsCount: 35 });
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
            const latency = Date.now() - start;
            setProbe({ ok: true, latency, toolsCount: 35 });
          })
          .catch(() => {});
        return () => { mounted = false; };
      }, []);

      const handleChange = (field, val) => {
        setFormConfig(prev => ({ ...prev, [field]: val }));
      };

      const handlePreset = (url) => {
        setFormConfig(prev => ({ ...prev, endpointUrl: url }));
      };

      const handleTest = async () => {
        setTesting(true);
        setTestStatus(null);
        let base = (formConfig.endpointUrl || '').trim().replace(/\/mcp\/?$/i, '').replace(/\/+$/, '');
        if (!base) base = 'https://vk.tide.red';

        const start = Date.now();
        const headers = { 'Content-Type': 'application/json' };
        if (formConfig.userKey) {
          headers['Authorization'] = `Bearer ${formConfig.userKey.trim()}`;
        }
        if (formConfig.agentId) {
          headers['X-Agent-ID'] = formConfig.agentId.trim();
        }

        try {
          const res = await fetch(`${base}/health`, { headers, signal: AbortSignal.timeout(4000) });
          const latency = Date.now() - start;
          if (res.ok) {
            const hData = await res.json();
            let toolCount = 35;
            let roleMsg = '服务连接正常';
            try {
              const capRes = await fetch(`${base}/api/v1/system/client-capabilities?plugin_id=${PLUGIN_ID}&probe=full`, {
                headers,
                signal: AbortSignal.timeout(4000)
              });
              if (capRes.ok) {
                const capData = await capRes.json();
                if (Array.isArray(capData.tools) && capData.tools.length > 0) {
                  toolCount = capData.tools.length;
                }
                roleMsg = capData.role ? `鉴权角色: ${capData.role}` : '用户凭据有效';
              } else if (capRes.status === 401) {
                setTestStatus({
                  ok: false,
                  msg: `网络通畅但凭据被拒绝 (HTTP 401): 填写的 UserKey 无效或未授权`
                });
                setTesting(false);
                return;
              }
            } catch (_) {}

            setTestStatus({
              ok: true,
              msg: `连接成功 (v${hData.version || '1.7.168'}) · 延迟 ${latency}ms · ${roleMsg} · 就绪 ${toolCount} 项战地工具`
            });
            setProbe({ ok: true, latency, toolsCount: toolCount });
          } else {
            setTestStatus({
              ok: false,
              msg: `服务端响应异常: HTTP ${res.status} ${res.statusText}`
            });
          }
        } catch (err) {
          setTestStatus({
            ok: false,
            msg: `连接不可达: ${err.message || '网络超时或端点不可达'}`
          });
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
        { key: 'mcp', label: `🦾 MCP 工具 (${probe.toolsCount || 35})` },
        { key: 'skills', label: '🧠 认知技能 (4)' },
        { key: 'hooks', label: '⚡ 拦截钩子 (3)' },
        { key: 'overview', label: '📖 架构概览' }
      ];

      return h('div', {
        style: {
          padding: '16px',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
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
            padding: '10px 14px',
            borderRadius: '6px',
            marginBottom: '14px',
            background: probe.ok ? 'rgba(8, 145, 178, 0.08)' : 'rgba(225, 29, 72, 0.06)',
            border: `1px solid ${probe.ok ? '#0891b2' : 'rgba(225, 29, 72, 0.3)'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '12px',
          }
        },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
            h('span', {
              style: {
                color: probe.ok ? '#0891b2' : '#e11d48',
                fontWeight: '600',
                fontSize: '12px'
              }
            }, probe.ok ? '● 服务连接正常' : '○ 服务未连接 / 未鉴权 (请在下方填写端点与 UserKey)'),
            probe.ok && h('span', { style: { color: 'var(--dsw-alias-label-secondary, #475569)', fontSize: '12px' } }, `时延: ${probe.latency}ms`),
            h('span', { style: { color: 'var(--dsw-alias-label-tertiary, #64748b)', fontSize: '12px' } }, `· 适配器: v${CLIENT_VERSION}`)
          ),
          h('div', {
            style: {
              fontFamily: 'monospace',
              fontWeight: '600',
              color: probe.ok ? '#0891b2' : 'var(--dsw-alias-label-secondary, #475569)',
              fontSize: '12px'
            }
          }, `${probe.toolsCount || 35} 项战地工具就绪`)
        ),

        // 2. Tab 导航栏
        h('div', {
          style: {
            display: 'flex',
            gap: '6px',
            borderBottom: '1px solid var(--dsw-alias-border-l1, #e2e8f0)',
            paddingBottom: '8px',
            marginBottom: '14px',
          }
        },
          tabs.map(t => h('button', {
            key: t.key,
            onClick: () => setTab(t.key),
            style: {
              background: tab === t.key ? 'rgba(8, 145, 178, 0.12)' : 'transparent',
              color: tab === t.key ? '#0891b2' : 'var(--dsw-alias-label-secondary, #334155)',
              border: tab === t.key ? '1px solid rgba(8, 145, 178, 0.3)' : '1px solid transparent',
              borderRadius: '6px',
              padding: '5px 12px',
              fontSize: '12px',
              fontWeight: tab === t.key ? '600' : '500',
              cursor: 'pointer',
            }
          }, t.label))
        ),

        // 3. Tab 内容区
        // [配置]：完整的端点与 UserKey 配置表单
        tab === 'config' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '12px' } },
          // 字段 1: endpointUrl
          h('div', null,
            h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' } },
              h('label', { style: { fontWeight: '600', color: 'var(--dsw-alias-label-primary, #0f172a)' } }, 'OpenViking 服务端通信端点 (endpointUrl):'),
              h('div', { style: { display: 'flex', gap: '6px' } },
                h('button', {
                  type: 'button',
                  onClick: () => handlePreset('https://vk.tide.red'),
                  style: {
                    background: 'rgba(8, 145, 178, 0.08)',
                    color: '#0891b2',
                    border: '1px solid rgba(8, 145, 178, 0.25)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }
                }, '公网中枢 (vk.tide.red)'),
                h('button', {
                  type: 'button',
                  onClick: handlePreset('http://127.0.0.1:1933'),
                  style: {
                    background: 'rgba(100, 116, 139, 0.08)',
                    color: 'var(--dsw-alias-label-secondary, #475569)',
                    border: '1px solid #cbd5e1',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }
                }, '本地机国 (127.0.0.1:1933)')
              )
            ),
            h('input', {
              type: 'text',
              value: formConfig.endpointUrl,
              onChange: (e) => handleChange('endpointUrl', e.target.value),
              placeholder: '例如 https://vk.tide.red 或 http://127.0.0.1:1933',
              style: {
                width: '100%',
                boxSizing: 'border-box',
                padding: '8px 10px',
                fontSize: '12px',
                fontFamily: 'monospace',
                borderRadius: '6px',
                border: '1px solid var(--dsw-alias-border-l2, #cbd5e1)',
                background: 'var(--dsw-alias-bg-layer-2, #f8fafc)',
                color: 'var(--dsw-alias-label-primary, #0f172a)',
                outline: 'none',
              }
            }),
            h('div', { style: { fontSize: '12px', color: 'var(--dsw-alias-label-tertiary, #64748b)', marginTop: '4px' } },
              '3070 远程工位机请填写公网端点 https://vk.tide.red；本地 2080Ti 主机可填写 http://127.0.0.1:1933'
            )
          ),

          // 字段 2: userKey
          h('div', null,
            h('label', { style: { display: 'block', fontWeight: '600', marginBottom: '4px', color: 'var(--dsw-alias-label-primary, #0f172a)' } }, '用户专属密钥 (User Key):'),
            h('div', { style: { display: 'flex', gap: '6px' } },
              h('input', {
                type: showKey ? 'text' : 'password',
                value: formConfig.userKey,
                onChange: (e) => handleChange('userKey', e.target.value),
                placeholder: '在 Web Studio 用户管理中复制您的专属 User Key (例如 vk-user-...)',
                style: {
                  flex: 1,
                  boxSizing: 'border-box',
                  padding: '8px 10px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  borderRadius: '6px',
                  border: '1px solid var(--dsw-alias-border-l2, #cbd5e1)',
                  background: 'var(--dsw-alias-bg-layer-2, #f8fafc)',
                  color: 'var(--dsw-alias-label-primary, #0f172a)',
                  outline: 'none',
                }
              }),
              h('button', {
                type: 'button',
                onClick: () => setShowKey(!showKey),
                style: {
                  padding: '0 12px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  background: 'var(--dsw-alias-bg-layer-2, #f1f5f9)',
                  color: 'var(--dsw-alias-label-secondary, #334155)',
                  fontSize: '12px',
                  cursor: 'pointer'
                }
              }, showKey ? '隐藏' : '显示')
            ),
            h('div', { style: { fontSize: '12px', color: 'var(--dsw-alias-label-tertiary, #64748b)', marginTop: '4px' } },
              '零信任单轨鉴权：密钥严格通过 HTTP Authorization Bearer 安全报头传输，绝对不拼接在 URL 中'
            )
          ),

          // 连通性测试报告横幅
          testStatus && h('div', {
            style: {
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              background: testStatus.ok ? 'rgba(8, 145, 178, 0.08)' : 'rgba(225, 29, 72, 0.08)',
              border: `1px solid ${testStatus.ok ? '#0891b2' : '#e11d48'}`,
              color: testStatus.ok ? '#0891b2' : '#e11d48',
              fontWeight: '500',
            }
          }, (testStatus.ok ? '✅ ' : '❌ ') + testStatus.msg),

          // 底部操作按钮栏
          h('div', { style: { display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '6px' } },
            h('button', {
              type: 'button',
              onClick: handleTest,
              disabled: testing,
              style: {
                background: 'rgba(8, 145, 178, 0.1)',
                color: '#0891b2',
                border: '1px solid rgba(8, 145, 178, 0.3)',
                padding: '6px 14px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: '600',
                cursor: testing ? 'not-allowed' : 'pointer',
              }
            }, testing ? '⚡ 正在探测...' : '⚡ 测试连通性'),
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
              }
            }, saving ? '💾 保存中...' : '💾 保存并应用配置')
          ),

          // 保存 Toast 反馈
          saveToast && h('div', {
            style: {
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              background: 'rgba(8, 145, 178, 0.1)',
              border: '1px solid #0891b2',
              color: '#0891b2',
              fontWeight: '500',
              textAlign: 'center'
            }
          }, saveToast.msg)
        ),

        // [MCP 工具]：7 大分类全量 35 项战地工具平铺展示
        tab === 'mcp' && h('div', {
          style: {
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            maxHeight: '440px',
            overflowY: 'auto',
            paddingRight: '4px'
          }
        },
          TOOL_CATEGORIES.map((catGroup, cIdx) => h('div', {
            key: cIdx,
            style: {
              padding: '10px 12px',
              borderRadius: '6px',
              background: 'var(--dsw-alias-bg-layer-2, rgba(100, 116, 139, 0.04))',
              border: '1px solid var(--dsw-alias-border-l1, #e2e8f0)',
            }
          },
            h('div', {
              style: {
                fontWeight: '600',
                fontSize: '12px',
                color: '#0891b2',
                marginBottom: '8px'
              }
            }, catGroup.cat),
            h('div', {
              style: {
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))',
                gap: '6px'
              }
            },
              catGroup.tools.map((tName, tIdx) => h('div', {
                key: tIdx,
                style: {
                  padding: '5px 8px',
                  borderRadius: '6px',
                  background: '#ffffff',
                  border: '1px solid #cbd5e1',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  color: '#0f172a',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }
              },
                h('span', { style: { color: '#0891b2', fontWeight: 'bold' } }, '⚡'),
                h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, tName)
              ))
            )
          ))
        ),

        // [技能]：4 大领域认知导轨
        tab === 'skills' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px' } },
          [
            { name: 'antigravity-plugin-crafting', desc: '反重力原生插件标准工程工法、六大构件标准与 SSOT 自动级联更新指南' },
            { name: 'openviking-memory', desc: 'OpenViking 体外大脑核心战地长程记忆语义检索、架构决策与经验沉淀规范' },
            { name: 'openviking-plugin-ops', desc: '体外大脑插件中枢与 Agent 生态制作规范：四位一体架构与零信任单轨鉴权' },
            { name: 'session-handover', desc: '战地会话脱水结晶与无缝接力：沉淀 Evolution Lessons 并输出标准化接力提示词' }
          ].map((s, idx) => h('div', {
            key: idx,
            style: {
              padding: '10px 12px',
              borderRadius: '6px',
              background: 'var(--dsw-alias-bg-layer-2, #f8fafc)',
              border: '1px solid #e2e8f0',
            }
          },
            h('div', { style: { fontFamily: 'monospace', fontWeight: '600', color: '#0891b2', fontSize: '12px' } }, s.name),
            h('div', { style: { marginTop: '3px', color: 'var(--dsw-alias-label-secondary, #475569)', fontSize: '12px' } }, s.desc)
          ))
        ),

        // [钩子]：3 大生命周期拦截守卫
        tab === 'hooks' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px' } },
          [
            { name: '跨会话长程记忆先验预取 (PreInvocation)', event: 'before_prompt', desc: '用户提问前静默召回最相关的长程战地记忆注入 Prompt 顶部，零额外 Token 损耗' },
            { name: '运行态安全沙箱守卫 (PreToolUse)', event: 'before_tool_call', desc: '物理拦截敏感外呼与高危越权越界操作，保障体外大脑数据资产主权安全' },
            { name: '会话生命周期自省归档 (Stop)', event: 'after_conversation', desc: '会话结束后离线脱水战地现场，自动提纯架构决策与踩坑教训入脑' }
          ].map((hk, idx) => h('div', {
            key: idx,
            style: {
              padding: '10px 12px',
              borderRadius: '6px',
              background: 'var(--dsw-alias-bg-layer-2, #f8fafc)',
              border: '1px solid #e2e8f0',
            }
          },
            h('div', { style: { fontWeight: '600', color: '#0891b2', fontSize: '12px' } }, hk.name),
            h('div', { style: { color: 'var(--dsw-alias-label-secondary, #475569)', fontSize: '12px', marginTop: '2px' } }, hk.desc),
            h('div', { style: { color: 'var(--dsw-alias-label-tertiary, #64748b)', fontSize: '12px', marginTop: '4px', fontFamily: 'monospace' } }, `拦截点: ${hk.event}`)
          ))
        ),

        // [概览]：高对比度、清晰卡片化渲染
        tab === 'overview' && h('div', {
          style: {
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            maxHeight: '440px',
            overflowY: 'auto'
          }
        },
          [
            { title: '🧠 跨会话核心战地记忆 (Exocortex Memory)', text: '提供全量 35 项 FastMCP 算子与长程向量索引，支持多层次阅读、AST 代码感知与踩坑教训原子沉淀。' },
            { title: '🔒 空间 + 用户双轴隔离与零信任 Bearer 鉴权', text: '无论本机回路还是公网远程，统一单轨 CSPRNG 高熵凭据鉴权，笛卡尔积沙箱物理防碰撞、防串号。' },
            { title: '⚡ 客户端动态能力投影 (Server-Centric Projection)', text: '重型逻辑 100% 运行于 OpenViking 服务端，客户端仅需轻量 RPC 适配桥梁，实现即开即用、零运维膨胀。' },
            { title: '🧩 四位一体深度咬合架构', text: '技能手册 (脑) + 自动化钩子 (自主神经) + FastMCP 算子 (执行手脚) + 座舱配置 (人机视窗) 物理咬合，杜绝左右互搏。' }
          ].map((card, idx) => h('div', {
            key: idx,
            style: {
              padding: '12px',
              borderRadius: '6px',
              background: 'var(--dsw-alias-bg-layer-2, #f8fafc)',
              border: '1px solid #e2e8f0',
            }
          },
            h('div', { style: { fontWeight: '600', fontSize: '12px', color: '#0891b2', marginBottom: '4px' } }, card.title),
            h('div', { style: { color: 'var(--dsw-alias-label-secondary, #334155)', fontSize: '12px', lineHeight: 1.6 } }, card.text)
          ))
        ),

        // 4. 底部微弱版本声明
        h('div', {
          style: {
            marginTop: '16px',
            paddingTop: '8px',
            borderTop: '1px solid var(--dsw-alias-border-l1, #e2e8f0)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '12px',
            color: 'var(--dsw-alias-label-tertiary, #64748b)',
          }
        },
          h('span', null, `OpenViking Universal Cockpit · ${PLUGIN_NAME}`),
          h('span', null, `版本 v${CLIENT_VERSION}`)
        )
      );
    }

    function apply(ctx) {
      const bundleKey = PLUGIN_ID;
      const shortKey = PLUGIN_ID.replace(/^dsh-plugin-/, '');

      // 1. 组合包详情页配置插槽 (Bundle Detail Page) - 兼容全名与短名
      ctx.slots.inject('plugins.bundle.config', () => {
        ctx.slots.register(
          { name: 'plugins.bundle.config', key: bundleKey },
          UniversalDshPanel
        );
        if (shortKey !== bundleKey) {
          ctx.slots.register(
            { name: 'plugins.bundle.config', key: shortKey },
            UniversalDshPanel
          );
        }
      });

      // 2. 组件行专属抽屉插槽 (Row Detail / Configure Drawer) - 兼容 <bundle>#<row> 与短格式
      ctx.slots.inject('plugins.row.config', () => {
        ctx.slots.register(
          { name: 'plugins.row.config', key: `${bundleKey}#${shortKey}` },
          UniversalDshPanel
        );
        ctx.slots.register(
          { name: 'plugins.row.config', key: `${shortKey}#${shortKey}` },
          UniversalDshPanel
        );
        ctx.slots.register(
          { name: 'plugins.row.config', key: bundleKey },
          UniversalDshPanel
        );
        ctx.slots.register(
          { name: 'plugins.row.config', key: shortKey },
          UniversalDshPanel
        );
      });

      // 3. 全局设置插件页 Tab (Settings -> Plugins Tab)
      ctx.slots.inject('settings.plugins.tab', () => {
        ctx.slots.register(
          {
            name: 'settings.plugins.tab',
            id: shortKey,
            order: 50,
            label: () => PLUGIN_NAME
          },
          UniversalDshPanel
        );
      });
    }

    return {
      inject: ['slots'],
      apply,
    };
  },
});