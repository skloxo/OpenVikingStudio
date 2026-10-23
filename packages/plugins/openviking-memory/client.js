/**
 * universal_dsh_client.js - OpenViking 通用无状态 DSH 插件座舱与配置面板模板
 * 100% 动态元数据与表单双轨驱动：支持服务端实时探针、端点与 UserKey 热配置、双锚点全冗余插槽注册。
 * 视觉铁律：NO GREEN EVER 🚫 (#0891b2 冰青 / #e11d48 玫瑰红)，字号 >= 12px，6px 微圆角，高对比度。
 */

window.__ModuleLoader__.load({
  id: 'dsh-plugin-openviking-memory',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState } = React;

    const PLUGIN_ID = 'dsh-plugin-openviking-memory';
    const CLIENT_VERSION = '2.0.35';
    const PLUGIN_NAME = 'OpenViking Core Memory';
    const SHORT_NAME = 'openviking-memory';
    const STORAGE_KEY = `dsh_plugin_${SHORT_NAME.replace(/-/g, '_')}_config`;

    // 动态插值数据源 (离线兜底 SSOT)
    const TOOL_CATEGORIES = [{"cat": "核心长程记忆与检索 (Memory & Context)", "tools": ["openviking_find", "openviking_search", "openviking_read", "openviking_write", "openviking_store", "openviking_tree", "openviking_grep", "openviking_glob", "openviking_code_search", "openviking_smart_read"]}, {"cat": "原子扩展工具箱 (FastMCP Tools)", "tools": ["openviking_link", "openviking_get_relations", "openviking_unlink", "openviking_ls", "openviking_code_outline", "openviking_code_expand", "openviking_diff", "openviking_content_reduce", "openviking_tag", "openviking_skills", "openviking_auto_onboard_skills", "openviking_get_onboard_queue_status", "openviking_fix_skill", "openviking_record_evolution_lesson", "openviking_file_task_card", "openviking_list_pending_cards", "openviking_resolve_task_card", "openviking_task_cards_summary", "openviking_privacy", "openviking_ping", "openviking_harness_stats"]}, {"cat": "模型聚合路由与多租户分摊 (CPA Squad)", "tools": ["openviking_tokenshift_compress"]}, {"cat": "系统运维治理与快照 (Ops & Snapshots)", "tools": ["openviking_audit_skills"]}, {"cat": "卫星集群网络与节点同频 (Fleet & Mesh)", "tools": ["openviking_valet_handover", "openviking_valet_ticket_status"]}];
    const SKILLS = [{"name": "antigravity-plugin-crafting", "desc": "本技能为在 **Google Antigravity Desktop (桌面端)** 与 **Google Antigravity IDE (编程端)** 生态下，打造 100% 官方合规、非暴力、非入侵式原生插件的**单一真相源 (SSOT) 标准工程工法**。"}, {"name": "openviking-memory", "desc": "OpenViking 体外大脑核心记忆操作规范 — 指导 Agent 在开局检索历史经验、执行中精准查阅架构与凭据、任务结束时将关键决策与经验教训持久化回写至 Master Memory。"}, {"name": "openviking-plugin-ops", "desc": "\"OpenViking (VK) 插件中心与 Agent 生态制作与运维中枢：三大官方标杆插件(记忆/凭据/搜索)、四位一体全息模型(Skill+Hook+MCP+GUI)、零信任单轨鉴权铁律与私有封闭堡垒公理、空间用户双轴防碰撞物理契约、异构客户端(DSH) stdio 桥接与 pre-step 隐藏 runtime-context 注入闭环、SPA 路由先于通配注册铁律、用户消息气泡零污染铁律、新节点接入六阶闭环验收及四大反模式避坑指南 (SSOT)\""}, {"name": "session-handover", "desc": "会话总结、经验沉淀与跨会话无缝接力技能 (Session Handover & Distillation SOP) — 当用户提到 \"总结会话\", \"交接本次会话\", \"开新的会话接续任务\", \"整理会话\", \"会话交接\", \"生成接力提示词\", \"无缝接力\", \"handoff\", \"handover session\", \"交接任务\", \"会话总结\", \"结晶会话\" 等意图时自动触发。负责脱水战地现场、提取 Evolution Lessons 与 Recipes 入 OpenViking 记忆中枢、审查演进技能库，并输出供全新冷启动会话 0 秒满血接续的标准化 Handover Prompt。"}];
    const HOOKS = [{"name": "openviking-memory-prefetch", "desc": "拦截 PreInvocation 事件，执行守卫检查", "event": "PreInvocation"}, {"name": "openviking-session-archiver", "desc": "拦截 Stop 事件，执行守卫检查", "event": "Stop"}, {"name": "openviking-sandbox-guard", "desc": "拦截 PreToolUse 事件，执行守卫检查", "event": "PreToolUse"}];
    const RULES = [{"name": "AGENTS.md", "desc": "OpenViking 记忆中枢交互与隔离准则 (Memory SSOT & Isolation Rules)", "content": "# OpenViking 记忆中枢交互与隔离准则 (Memory SSOT & Isolation Rules)\n\n1. **唯一真相源 (SSOT)**：\n   全系统所有架构决策、凭据配置与历史经验统一收口在 `viking://resources/master_memory/`，打破单会话与单智能体隔离。\n2. **私有与共享双层隔离**：\n   - 空间公共层：全智能体共享，用于权威规约与架构共识；\n   - 专属私有层：按 User ID 打标隔离（如 `AntigravityIDE@2080Ti`），过程性草稿与排障流水账默认不跨号污染。\n3. **安全与凭据铁律**：\n   - 严禁在代码、注释或对话中泄露明文 API Key；\n   - 客户端连接统一通过插件配置动态注入。"}];
    const README_CONTENT = "# OpenViking 核心长程记忆与代码战地插件 (openviking-memory)\n\n专为 **Google Antigravity IDE / Desktop** 打造的一等公民原生体外大脑插件。将跨会话语义记忆检索、代码 AST 符号感知、工作区拓扑、会话结晶归档与经验反思完全内聚，彻底替代传统的外部散装配置。\n\n---\n\n## 🌟 核心价值与架构定位\n\n1. **体外大脑全息记忆中枢**：\n   - 跨会话统一持久化存储与双向图谱关联，智能体长线重构与多轮对话记忆永不丢失；\n   - 预设 `PreInvocation` 先验自动召回预取，零额外 Token 损耗注入上下文。\n\n2. **代码 AST 符号与工作区态势感知**：\n   - 原生支持符号大纲提取、跨文件跳转扩展、正则行匹配与双向语义关联；\n   - 支撑智能体渐进式展开寻源，避免一次性吞入过多无关文件导致上下文爆炸。\n\n3. **会话无缝交接 (Handover) 与踩坑经验沉淀**：\n   - 内置标准化三阶交接规约，一键输出供新会话秒级启动的接力提示词；\n   - 疑难排障闭环后支持将物理根因、反思与代码差异原子沉淀至 Evolution Lessons。\n\n---\n\n## 🧭 构件导引与单一真相源 (SSOT)\n\n本插件已实现 100% 构件自治内聚，各资产明细直接通过上方 Tab 查阅（下方卡片为 Antigravity 宿主原生快速跳转入口）：\n- **技能与命令**：见上方 **「技能」Tab**（或点击下方 `Commands >` 快捷直达）；\n- **MCP 算子矩阵**：见上方 **「MCP」Tab**（或点击下方 `MCP servers >` 快捷直达）；\n- **生命周期守卫**：见上方 **「钩子」Tab**（或点击下方 `钩子 >` 快捷直达）；\n- **行为规约约束**：见上方 **「规则」Tab**（或点击下方 `规则 >` 快捷直达）。\n\n\n";

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
          setSaveToast({ ok: true, msg: '配置已持久化保存，并在 DSH 会话中实时生效' });
          setTimeout(() => setSaveToast(null), 3000);
        }, 200);
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

    // 2. 底层组件行专属运行态详情卡 (Component Row Runtime Stub Card)
    // 解决 DSH "包含的组件" 路由点击后的重复镜像套娃问题，以极轻卡片清晰展示通信管道状态
    function UniversalDshRowPanel(props) {
      if (props && props.view === 'summary') return null;
      const initial = loadSavedConfig();
      const endpoint = initial.endpointUrl || '未指定 (继承环境全局默认)';
      const peer = initial.peer || SHORT_NAME;

      return h('div', {
        style: {
          padding: '16px',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          fontSize: '12px',
          color: 'var(--dsw-alias-label-primary, #0f172a)',
          background: 'var(--dsw-alias-settings-card-fill, var(--dsw-alias-bg-l1, #ffffff))',
          borderRadius: '8px',
          border: '1px solid var(--dsw-alias-settings-card-stroke, var(--dsw-alias-border-l1, #e2e8f0))',
          lineHeight: 1.6,
          margin: '6px 0',
        }
      },
        h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' } },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
            h('span', { style: { fontSize: '13px', fontWeight: '600', color: '#0891b2' } }, '● 核心桥接存根运行态 (Bridge Runtime Stub)'),
            h('span', { style: { background: 'rgba(8, 145, 178, 0.1)', color: '#0891b2', padding: '1px 6px', borderRadius: '4px', fontFamily: 'monospace' } }, `v${CLIENT_VERSION}`)
          ),
          h('span', { style: { color: '#64748b' } }, '无状态极轻转发存根')
        ),
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px', color: 'var(--dsw-alias-label-secondary, #475569)' } },
          h('div', { style: { display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--dsw-alias-bg-layer-2, #f8fafc)', borderRadius: '6px' } },
            h('span', { style: { fontWeight: '600' } }, '宿主环境节点标识 (Peer ID):'),
            h('span', { style: { fontFamily: 'monospace', color: '#0891b2' } }, peer)
          ),
          h('div', { style: { display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--dsw-alias-bg-layer-2, #f8fafc)', borderRadius: '6px' } },
            h('span', { style: { fontWeight: '600' } }, '目标通信中枢端点:'),
            h('span', { style: { fontFamily: 'monospace', color: '#0891b2' } }, endpoint)
          ),
          h('div', { style: { display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--dsw-alias-bg-layer-2, #f8fafc)', borderRadius: '6px' } },
            h('span', { style: { fontWeight: '600' } }, '端侧 Hook 神经反射守卫:'),
            h('span', { style: { color: '#0891b2' } }, `${HOOKS.length} 项守卫就绪 (${HOOKS.map(h => h.name).join(', ')})`)
          ),
          h('div', { style: { display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--dsw-alias-bg-layer-2, #f8fafc)', borderRadius: '6px' } },
            h('span', { style: { fontWeight: '600' } }, '物理职责说明:'),
            h('span', { style: { color: '#64748b' } }, '本进程为纯透明转发存根，业务算子与计算本体 100% 运行于 OpenViking 服务端')
          )
        ),
        h('div', { style: { marginTop: '12px', padding: '8px 12px', borderRadius: '6px', background: 'rgba(8, 145, 178, 0.05)', border: '1px solid rgba(8, 145, 178, 0.2)', color: '#0891b2', fontSize: '12px' } },
          '💡 提示：所有参数配置、UserKey 凭据、技能手册与规则规约已由外层主控制台统一托管。点击左上方返回按钮即可回到插件主控制台。'
        )
      );
    }

    function apply(ctx) {
      const bundleKey = PLUGIN_ID;
      const shortKey = SHORT_NAME;

      // 1. 组合包详情页配置插槽 (Bundle Detail Page) - DSH 点击插件行直达 OpenViking 全功能主控座舱
      ctx.slots.inject('plugins.bundle.config', () => {
        ctx.slots.register({ name: 'plugins.bundle.config', key: bundleKey }, UniversalDshPanel);
        if (shortKey !== bundleKey) {
          ctx.slots.register({ name: 'plugins.bundle.config', key: shortKey }, UniversalDshPanel);
        }
      });

      // 2. 组件行专属抽屉插槽 (Row Detail / Configure Drawer) - 渲染轻量桥接运行态存根，彻底告别套娃重影
      ctx.slots.inject('plugins.row.config', () => {
        ctx.slots.register({ name: 'plugins.row.config', key: bundleKey }, UniversalDshRowPanel);
        ctx.slots.register({ name: 'plugins.row.config', key: shortKey }, UniversalDshRowPanel);
        ctx.slots.register({ name: 'plugins.row.config', key: `${bundleKey}#${shortKey}` }, UniversalDshRowPanel);
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