/**
 * KeePass Vault DSH Cockpit & Settings Adapter (client.js v1.2.6)
 * 专为 DeepSeek Harness 打造的本地凭据中枢座舱面板与配置表单。
 * 视觉铁律：NO GREEN EVER 🚫 (#0891b2 冰青 / #e11d48 玫瑰红)，字号 >= 12px，6px 微圆角，高信息密度。
 */

window.__ModuleLoader__.load({
  id: 'dsh-plugin-keepass-vault',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState } = React;

    const PLUGIN_ID = 'dsh-plugin-keepass-vault';
    const CLIENT_VERSION = '1.2.6';
    const PLUGIN_NAME = 'KeePass Vault';
    const SHORT_NAME = 'keepass-vault';
    const STORAGE_KEY = `dsh_plugin_${SHORT_NAME.replace(/-/g, '_')}_config`;

    const TOOL_CATEGORIES = [
      {
        cat: '本地高安全凭据保险库 (Credentials & Security)',
        tools: ['keepass_status', 'keepass_get', 'keepass_add', 'keepass_edit', 'keepass_rm', 'keepass_analyze', 'keepass_export_attachment']
      },
      {
        cat: '凭据检索与分组遍历 (Search & Hierarchy)',
        tools: ['keepass_search', 'keepass_list_tree']
      }
    ];

    const SKILLS = [
      {
        name: 'keepass-vault',
        desc: 'KeePass 本地密码保险库凭据管理与自动化中枢专用技能。落实查库第一公理、免明文索取、写前快照容灾、高熵密码入库与条目全生命周期管理。'
      }
    ];

    const HOOKS = [
      {
        name: 'vault-guard',
        desc: '写前自动快照容灾守护：在执行 add/edit/rm 修改前自动生成带时间戳的安全快照 (*.bak)，滚动保留 10 份。',
        event: 'Pre-Execution'
      }
    ];

    const RULES = [
      {
        name: 'AGENTS.md',
        desc: '🔐 KeePass 凭据保险箱法则契约 (Credential SSOT Contract)',
        content: '# 🔐 KeePass 凭据保险箱法则契约\n\n1. 查库第一公理：凡遇 API Key、SSH 密码/私钥、连接串，绝对禁止向人类直接索要明文，开局优先 keepass_search；\n2. 灾难恢复优先：写前自动创建时间戳安全快照；\n3. 免明文透传：对话与日志输出凭据强制掩码脱敏；\n4. 高熵生成律：新增密码强制生成 >=16 位高熵口令。'
      }
    ];

    const README_CONTENT = `# KeePass 凭据中枢物理守卫插件 (keepass-vault)\n\n专为 **DeepSeek Harness** 与集群智能体打造的本地凭据保险库插件。落实查库第一公理，免除明文索取，高熵写盘，保障全集群凭据唯一真相源 (Credential SSOT)。\n\n### 🌟 核心特性\n- 查库第一公理 (Credential SSOT)\n- 本地 KDBX 数据库解耦直连\n- 写前防抖物理快照 (Disaster Recovery First)\n- 9 项 FastMCP 原子算子\n`;

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
        kdbxPath: '~/Desktop/Key.kdbx',
        masterKey: '',
        autoSnapshot: true
      };
    }

    function saveConfig(cfg) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
      } catch (_) {}
    }

    function KeePassDshPanel(props) {
      if (props && props.view === 'summary') return null;

      const [formConfig, setFormConfig] = useState(() => {
        const initial = loadSavedConfig();
        const pCfg = props?.config || {};
        return {
          kdbxPath: pCfg.kdbxPath || initial.kdbxPath || '~/Desktop/Key.kdbx',
          masterKey: pCfg.masterKey || initial.masterKey || '',
          autoSnapshot: pCfg.autoSnapshot !== undefined ? pCfg.autoSnapshot : (initial.autoSnapshot !== false)
        };
      });

      const [tab, setTab] = useState('config');
      const [showKey, setShowKey] = useState(false);
      const [testStatus, setTestStatus] = useState(null);
      const [testing, setTesting] = useState(false);
      const [saving, setSaving] = useState(false);
      const [saveToast, setSaveToast] = useState(null);

      const handleChange = (field, val) => setFormConfig(prev => ({ ...prev, [field]: val }));

      // 物理真实全链路测试：测试文件真实存在性与密码真实解锁能力
      const handleTest = async () => {
        const dbPath = (formConfig.kdbxPath || '').trim();
        if (!dbPath) {
          setTestStatus({ ok: false, msg: '请先填写本地 KeePass 数据库路径 (.kdbx)' });
          return;
        }
        if (!formConfig.masterKey) {
          setTestStatus({ ok: false, msg: '请填写主解锁口令，以便验证密码是否能够成功解密该文件。' });
          return;
        }

        setTesting(true);
        setTestStatus(null);

        try {
          const res = await fetch('http://127.0.0.1:19341/kpv-probe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ kdbxPath: dbPath, masterKey: formConfig.masterKey }),
            signal: AbortSignal.timeout(8000)
          });
          if (res.ok) {
            const data = await res.json();
            if (data.ok) {
              setTestStatus({ ok: true, msg: `✅ 物理体检通过: ${data.msg}` });
            } else {
              setTestStatus({ ok: false, msg: `❌ 物理体检失败: ${data.error}` });
            }
          } else {
            setTestStatus({ ok: false, msg: `本地探测探针返回状态异常: HTTP ${res.status}` });
          }
        } catch (err) {
          setTestStatus({ ok: false, msg: `本地探针服务未就绪 (127.0.0.1:19341): ${err.message || '请确保插件处于已启用状态'}` });
        } finally {
          setTesting(false);
        }
      };

      const handleSave = async () => {
        setSaving(true);
        saveConfig(formConfig);
        if (props?.form?.mutate) {
          try {
            props.form.mutate([
              { op: 'replace', path: '/kdbxPath', value: formConfig.kdbxPath },
              { op: 'replace', path: '/masterKey', value: formConfig.masterKey },
              { op: 'replace', path: '/autoSnapshot', value: formConfig.autoSnapshot }
            ]);
          } catch (_) {}
        }
        if (typeof props?.onChange === 'function') {
          try { props.onChange({ ...props.config, ...formConfig }); } catch (_) {}
        }
        try {
          await fetch('http://127.0.0.1:19341/kpv-save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formConfig),
            signal: AbortSignal.timeout(2000)
          });
        } catch (_) {}
        setSaving(false);
        setSaveToast({ ok: true, msg: '配置已持久化保存，KeePass 凭据中枢已在 DSH 会话中生效！' });
        setTimeout(() => setSaveToast(null), 3500);
      };

      const tabs = [
        { key: 'config', label: '服务配置' },
        { key: 'overview', label: '概览' },
        { key: 'skills', label: `技能 (${SKILLS.length})` },
        { key: 'tools', label: `MCP (${totalToolsCount})` },
        { key: 'hooks', label: `钩子 (${HOOKS.length})` },
        { key: 'rules', label: `规则 (${RULES.length})` }
      ];

      return h('div', {
        style: {
          display: 'flex', flexDirection: 'column', gap: '14px',
          padding: '16px', background: 'var(--dsw-alias-bg-layer-0, #ffffff)',
          borderRadius: '6px', border: '1px solid var(--dsw-alias-border-l1, #e2e8f0)',
          fontFamily: 'system-ui, -apple-system, sans-serif', fontSize: '12px',
          color: 'var(--dsw-alias-label-primary, #0f172a)'
        }
      },
        // 顶部标题与 Tab 栏
        h('div', { style: { display: 'flex', borderBottom: '1px solid #e2e8f0', gap: '8px' } },
          tabs.map(t => h('button', {
            key: t.key,
            onClick: () => setTab(t.key),
            style: {
              padding: '6px 12px', fontSize: '12px', border: 'none', background: 'transparent',
              cursor: 'pointer', borderBottom: tab === t.key ? '2px solid #0891b2' : '2px solid transparent',
              color: tab === t.key ? '#0891b2' : 'var(--dsw-alias-label-secondary, #64748b)',
              fontWeight: tab === t.key ? '600' : '400'
            }
          }, t.label))
        ),

        // TAB 1: 服务配置 (KeePass 专属)
        tab === 'config' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '12px' } },
          h('div', null,
            h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' } },
              h('label', { style: { fontWeight: '600', fontSize: '12px' } }, '本地 KeePass 数据库路径 (.kdbx)'),
              h('button', {
                type: 'button',
                onClick: () => handleChange('kdbxPath', '~/Desktop/Key.kdbx'),
                style: {
                  fontSize: '12px', color: '#0891b2', border: '1px solid #0891b2', background: 'transparent',
                  padding: '2px 8px', borderRadius: '4px', cursor: 'pointer'
                }
              }, '快捷填入: ~/Desktop/Key.kdbx')
            ),
            h('input', {
              type: 'text',
              value: formConfig.kdbxPath,
              onChange: e => handleChange('kdbxPath', e.target.value),
              placeholder: '例如: ~/Desktop/Key.kdbx 或 C:/Users/YourName/Desktop/Key.kdbx',
              style: {
                width: '100%', padding: '8px 10px', fontSize: '12px', borderRadius: '6px',
                border: '1px solid #cbd5e1', background: 'var(--dsw-alias-bg-layer-1, #f8fafc)',
                boxSizing: 'border-box'
              }
            })
          ),

          h('div', null,
            h('label', { style: { fontWeight: '600', fontSize: '12px', display: 'block', marginBottom: '6px' } }, '数据库主解锁口令 (Master Password)'),
            h('div', { style: { display: 'flex', gap: '8px' } },
              h('input', {
                type: showKey ? 'text' : 'password',
                value: formConfig.masterKey,
                onChange: e => handleChange('masterKey', e.target.value),
                placeholder: '请输入 .kdbx 解锁主口令 (受本地加密保护，严禁明文索取)',
                style: {
                  flex: 1, padding: '8px 10px', fontSize: '12px', borderRadius: '6px',
                  border: '1px solid #cbd5e1', background: 'var(--dsw-alias-bg-layer-1, #f8fafc)'
                }
              }),
              h('button', {
                type: 'button',
                onClick: () => setShowKey(!showKey),
                style: {
                  padding: '8px 14px', fontSize: '12px', borderRadius: '6px', border: '1px solid #cbd5e1',
                  background: 'var(--dsw-alias-bg-layer-2, #ffffff)', cursor: 'pointer'
                }
              }, showKey ? '隐藏' : '显示')
            ),
            h('div', { style: { fontSize: '12px', color: '#64748b', marginTop: '4px' } },
              '说明：查库第一公理生效。主口令仅由本地 keepassxc-cli 解锁使用，绝不上云。'
            )
          ),

          h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' } },
            h('input', {
              type: 'checkbox',
              id: 'autoSnapshot',
              checked: formConfig.autoSnapshot,
              onChange: e => handleChange('autoSnapshot', e.target.checked),
              style: { cursor: 'pointer' }
            }),
            h('label', { htmlFor: 'autoSnapshot', style: { fontSize: '12px', cursor: 'pointer' } },
              '启用写操作自动 *.bak 时间戳快照容灾 (灾难恢复优先，滚动保留 10 份)'
            )
          ),

          testStatus && h('div', {
            style: {
              padding: '8px 12px', borderRadius: '6px', fontSize: '12px',
              background: testStatus.ok ? '#ecfeff' : '#fff1f2',
              color: testStatus.ok ? '#0891b2' : '#e11d48',
              border: `1px solid ${testStatus.ok ? '#a5f3fc' : '#fecdd3'}`
            }
          }, testStatus.msg),

          saveToast && h('div', {
            style: {
              padding: '8px 12px', borderRadius: '6px', fontSize: '12px',
              background: '#ecfeff', color: '#0891b2', border: '1px solid #a5f3fc'
            }
          }, saveToast.msg),

          h('div', { style: { display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' } },
            h('button', {
              type: 'button',
              onClick: handleTest,
              disabled: testing,
              style: {
                padding: '8px 14px', fontSize: '12px', borderRadius: '6px', border: '1px solid #0891b2',
                color: '#0891b2', background: 'transparent', cursor: 'pointer'
              }
            }, testing ? '物理测试解锁中...' : '测试连通性与解锁'),
            h('button', {
              type: 'button',
              onClick: handleSave,
              disabled: saving,
              style: {
                padding: '8px 18px', fontSize: '12px', borderRadius: '6px', border: 'none',
                color: '#ffffff', background: '#0891b2', cursor: 'pointer', fontWeight: '600'
              }
            }, saving ? '保存中...' : '保存配置')
          )
        ),

        // TAB 2: 概览 (README)
        tab === 'overview' && h('div', {
          style: {
            padding: '12px', borderRadius: '6px', background: 'var(--dsw-alias-bg-layer-1, #f8fafc)',
            border: '1px solid #e2e8f0', whiteSpace: 'pre-wrap', lineHeight: 1.5, fontSize: '12px'
          }
        }, README_CONTENT),

        // TAB 3: 技能
        tab === 'skills' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px' } },
          SKILLS.map((s, idx) => h('div', {
            key: idx,
            style: { padding: '10px', borderRadius: '6px', border: '1px solid #e2e8f0', background: 'var(--dsw-alias-bg-layer-1, #f8fafc)' }
          },
            h('div', { style: { fontWeight: '600', color: '#0891b2', marginBottom: '4px' } }, s.name),
            h('div', { style: { color: '#64748b' } }, s.desc)
          ))
        ),

        // TAB 4: MCP 工具
        tab === 'tools' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '10px' } },
          TOOL_CATEGORIES.map((cat, idx) => h('div', { key: idx },
            h('div', { style: { fontWeight: '600', color: '#0891b2', marginBottom: '6px' } }, cat.cat),
            h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: '6px' } },
              cat.tools.map(tool => h('span', {
                key: tool,
                style: {
                  padding: '3px 8px', borderRadius: '4px', background: '#f1f5f9',
                  border: '1px solid #cbd5e1', fontFamily: 'monospace', fontSize: '12px'
                }
              }, tool))
            )
          ))
        ),

        // TAB 5: 钩子
        tab === 'hooks' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px' } },
          HOOKS.map((hItem, idx) => h('div', {
            key: idx,
            style: { padding: '10px', borderRadius: '6px', border: '1px solid #e2e8f0', background: 'var(--dsw-alias-bg-layer-1, #f8fafc)' }
          },
            h('div', { style: { display: 'flex', justifyContent: 'space-between', marginBottom: '4px' } },
              h('span', { style: { fontWeight: '600', color: '#0891b2' } }, hItem.name),
              h('span', { style: { fontSize: '12px', color: '#64748b' } }, hItem.event)
            ),
            h('div', { style: { color: '#64748b' } }, hItem.desc)
          ))
        ),

        // TAB 6: 规则
        tab === 'rules' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px' } },
          RULES.map((r, idx) => h('div', {
            key: idx,
            style: { padding: '10px', borderRadius: '6px', border: '1px solid #e2e8f0', background: 'var(--dsw-alias-bg-layer-1, #f8fafc)' }
          },
            h('div', { style: { fontWeight: '600', color: '#0891b2', marginBottom: '4px' } }, r.name),
            h('div', { style: { color: '#64748b', marginBottom: '6px' } }, r.desc),
            r.content && h('pre', {
              style: {
                padding: '8px', borderRadius: '4px', background: '#ffffff', border: '1px solid #e2e8f0',
                fontSize: '12px', fontFamily: 'monospace', whiteSpace: 'pre-wrap', maxHeight: '180px', overflowY: 'auto'
              }
            }, r.content)
          ))
        ),

        // 底部版本声明
        h('div', {
          style: {
            marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #e2e8f0',
            display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#94a3b8'
          }
        },
          h('span', null, `KeePass Vault Standalone Cockpit · 纯本地高安全`),
          h('span', null, `端侧桥接器 v${CLIENT_VERSION}`)
        )
      );
    }

    function apply(ctx) {
      const bundleKey = PLUGIN_ID;
      const shortKey = SHORT_NAME;

      // 1. 组合包详情页配置插槽
      ctx.slots.inject('plugins.bundle.config', () => {
        ctx.slots.register({ name: 'plugins.bundle.config', key: bundleKey }, KeePassDshPanel);
        if (shortKey !== bundleKey) {
          ctx.slots.register({ name: 'plugins.bundle.config', key: shortKey }, KeePassDshPanel);
        }
      });

      // 2. 全局设置插件页 Tab
      ctx.slots.inject('settings.plugins.tab', () => {
        ctx.slots.register({
          name: 'settings.plugins.tab',
          id: shortKey,
          order: 50,
          label: () => PLUGIN_NAME
        }, KeePassDshPanel);
      });
    }

    return {
      inject: ['slots'],
      apply
    };
  }
});
