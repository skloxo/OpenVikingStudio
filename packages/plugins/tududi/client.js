/**
 * universal_dsh_client.js - OpenViking 通用无状态 DSH 插件座舱与配置面板模板
 * 100% 动态元数据与表单双轨驱动：支持服务端实时探针、端点与 UserKey 热配置、双锚点全冗余插槽注册。
 * 视觉铁律：NO GREEN EVER 🚫 (#0891b2 冰青 / #e11d48 玫瑰红)，字号 >= 12px，6px 微圆角，高对比度。
 */

window.__ModuleLoader__.load({
  id: 'dsh-plugin-tududi',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useState } = React;

    const PLUGIN_ID = 'dsh-plugin-tududi';
    const CLIENT_VERSION = '1.1.9';
    const PLUGIN_NAME = 'Tududi Task Manager';
    const SHORT_NAME = 'tududi';
    const STORAGE_KEY = `dsh_plugin_${SHORT_NAME.replace(/-/g, '_')}_config`;

    // 动态插值数据源 (离线兜底 SSOT)
    const TOOL_CATEGORIES = [{"cat": "敏捷任务与全域 GTD 生产力 (Tasks & Productivity)", "tools": ["add_subtask", "add_task_comment", "add_to_inbox", "complete_task", "create_area", "create_goal", "create_habit", "create_project", "create_task", "create_task_relation", "create_view", "delete_area", "delete_goal", "delete_habit", "delete_habit_completion", "delete_inbox_item", "delete_project", "delete_task", "delete_view", "get_area", "get_goal", "get_habit", "get_habit_completions", "get_habit_stats", "get_inbox_item", "get_project", "get_task", "get_task_metrics", "get_view", "list_areas", "list_goals", "list_habits", "list_inbox", "list_projects", "list_task_comments", "list_task_relations", "list_tasks", "list_views", "log_habit_completion", "process_inbox_item", "remove_task_relation", "skip_task_occurrence", "update_area", "update_goal", "update_habit", "update_inbox_item", "update_project", "update_task", "update_view"]}, {"cat": "原子扩展工具箱 (FastMCP Tools)", "tools": ["create_note", "create_person", "create_tag", "delete_note", "delete_person", "delete_tag", "get_note", "get_person", "get_tag", "list_notes", "list_people", "list_tags", "update_note", "update_person", "update_tag"]}, {"cat": "核心长程记忆与检索 (Memory & Context)", "tools": ["search"]}];
    const SKILLS = [{"name": "tududi_ops", "desc": "Tududi (todo) 任务管理系统生产级运维、OKR+GTD 五层标准架构、Agent 三大自动作业反射、原生 FastMCP 65 算子实战调用 SOP 与防标签滥用标准化技能 (Tududi Ops & OKR-GTD Governance SOP)。"}];
    const HOOKS = [{"name": "tududi-okr-gtd-guard", "desc": "拦截 PreToolUse 事件，执行五重守卫（Task id 与实体 uid 异构纠偏、空主键删除阻断、priority/status 枚举校验、防标签滥用）", "event": "PreToolUse"}];
    const RULES = [{"name": "AGENTS.md", "desc": "📋 Tududi (todo) 全域任务管理与 OKR+GTD 生产力中枢规约契约 (Tududi Agent Rules SSOT)", "content": "# 📋 Tududi (todo) 全域任务管理与 OKR+GTD 生产力中枢规约契约 (Tududi Agent Rules SSOT)\n\n本规约是全集群智能体（Google Antigravity、DeepSeek Harness、Pi Agent）在涉及任务、待办、项目、习惯、目标与收集箱管理时的常驻潜意识法则。\n\n---\n\n## 一、 意图识别与工具分流第一公理 (Intent Routing Axiom)\n1. **自然语言第一反射**：凡人类提及 **“Tududi”、“todo”、“待办”、“任务清单”、“今日任务”、“收集箱 (Inbox)”、“习惯打卡”、“项目进度”、“周报/月报/OKR进度”** 时，必须 **100% 路由至 `tududi` (`tududi_core`) MCP 工具集**，并遵循 `tududi_ops` 技能规范；\n2. **职责边界清晰**：\n   - **Tududi (`https://todo.tide.red`)**：统管全集群与人类的 **OKR 目标 (Goals)、业务项目 (Projects)、日常/研发任务 (Tasks & Subtasks)、周期习惯 (Habits)、收集箱 (Inbox) 与参考笔记 (Notes)**，是人类网页端零 Token 感知进度与导出周报/月报/OKR 的唯一事实源；\n   - **代码仓库 `REFACTORING_PLAN.md`**：仅记录单仓库内部文件级编码微步，模块级与业务级任务一律在 Tududi 统管。\n\n---\n\n## 二、 OKR + GTD 五层标准映射定式 (5-Layer Hierarchy SSOT)\n全系统实体严格遵循「上半截管 OKR 战略交账、下半截管 GTD 落地执行」的五层咬合结构，严禁混层：\n\n1. **L1 `Area (领域)` —— 公私最高物理边界（永不结案）**：\n   - 全系统仅设 2 个顶级领域：**`工作`** (`id: 6, uid: \"bchf3cj1tr44xv7\"`) 与 **`个人`** (`id: 7, uid: \"f9hshwtupevwy8q\"`)。\n2. **L2 `Goal (目标)` —— 对应公司年度/季度 OKR 考核大项 (`O`)**：\n   - 仅在 `工作` 领域下建立，100% 严格对齐公司提交的 OKR 原文名称：**`O1：数字化产品创新建设`**、**`O2：后勤服务系统建设`**、**`O3：行政办公 AI 辅助系统`**、**`O4：部门例行工作`**（`个人` 领域无需建 OKR 目标）；\n   - **严禁加额外括号解释或将软件小迭代版本号建成 Goal**。\n3. **L3 `Project (项目)` —— 具体业务系统/专案主体（直接承接核心 `KR` 载体）**：\n   - **容器与指标分离定式 (`Project ≈ KR`)**：`Project` 标题与本地目录保持简短清爽（容器名），对应的年度/季度量化 `KR` 验收标准写入 `Goal/Project.description` 与本地 `Ox_.../AGENTS.md`；该项目下所有已完成 Task 的 `【达成成果】` 汇总即构成该条 `KR` 的结案证明；\n   - **O1~O4 标准映射**：O1 `网格化管理平台` #1；O2 `干部公寓与世纪华庭` #2；O3 `安防监控中台` #21、`任务调度中枢 (Tududi)` #20、`AI监控` #17；O4 `滴滴企业打车` #16、`园区门户` #19、`仓储方案` #18、`技术运维与例行保障` #15（个人下：`智能体与知识中枢` #4、`CPA 算力网关` #8、`算力集群与运维` #3 等）；\n   - **严禁将单个功能开发卡（如 `TASK-042`）提拔建成独立 Project**。\n4. **L4 `Tag (标签)` —— 横切区分任务的「工作性质」**：\n   - 核心职能标签严格收敛为 5 个：**`规划`**、**`开发`**、**`运维`**、**`汇报`**、**`缺陷`**；\n   - **严禁创建或使用表示优先级（如 `P0`、`紧急`）、状态（如 `待办`、`已完成`）或重复领域名的标签**。\n5. **L5 `Task ➔ Subtask (两层任务)` —— 落地执行动作**：\n   - **常规任务**：`Task` 放功能特性或独立事项（标题带 `[规划]` / `[开发]` / `[运维]` / `[汇报]` / `[缺陷]` 前缀并挂对应 Tag）➔ `Subtask` 放可验收的模块/步骤 ➔ 更细的代码文件级微步写入 `Task.note` 的 Markdown Checklist；\n   - **跨周巨型任务**：拆为带 `[专题名 1/N]` 前缀的并列一级 `Task`，通过 `create_task_relation(type=\"blocks\")` 建立先后依赖链，每个 `Task` 下挂各自的 `Subtask`。\n\n---\n\n## 三、 Agent 三大自动作业神经反射 (Three Agent Reflexes)\n1. **开局自动领活 (Read on Start)**：新会话提及具体项目或询问下一步任务时，Agent 自动调用 `list_tasks(project_id=..., status=\"in_progress\")` 与 `list_tasks(project_id=..., status=\"planned\")` 盘点当前进度，免除人类翻找文档负担；\n2. **过程随手记分支 (Capture on the Fly)**：开发或排障中途发现顺带缺陷、分支问题或新优化点时，不打断当前主线，立即调用 `create_task` 挂入对应 `Project`（设 `status=\"not_started\"`，打 `缺陷` 或 `开发`/`运维` 标签），确保 100% 零遗忘；\n3. **完工强制留双行汇报锚点 (Quantified Closure)**：任务达成调用 `complete_task` 前，必须通过 `update_task` 在任务 `note` 中写入结构化交付总结（供周报/月报/OKR 直接抽取）：\n   - `【达成成果】`：量化交付物与真实物理锚点（具体模块、接口数、设备数、单测通过数）；\n   - `【解决挑战】`：解决的业务痛点、技术难点或理顺的跨部门协同机制。\n\n---\n\n## 四、 65 项 MCP 工具入参异构避坑铁律 (Parameter Contract Guardrails)\n1. **主键字段名异构律 (`id` vs `uid`)**：\n   - **Task（任务）专属主键为 `id`**：调用 `get_task`、`update_task`、`complete_task`、`delete_task`、`skip_task_occurrence`、`add_task_comment`、`list_task_comments`、`create_task_relation`、`list_task_relations`、`remove_task_relation` 时，主键参数名一律为 **`id`**；`add_subtask` 父任务参数名为 **`parent_id`**；\n   - **其余全部实体主键为 `uid`**：调用 Area、Project、Goal、Habit、Inbox、Note、Person、Tag、View 的 `get_*`、`update_*`、`delete_*`、`log_habit_completion`、`process_inbox_item` 时，主键参数名一律为 **`uid`**（15 位字符串）。\n2. **外键关联字段律**：\n   - `create_task` / `update_task` 绑定项目传 **`project_id`**（数字 ID），绑定领域传 **`area_id`**（数字 ID）或 **`area_uid`**（字符串 UID）；\n   - `create_project` / `update_project` 绑定领域传 **`area_id`**（数字 ID），绑定目标传 **`goal_id`**（数字 ID）或 **`goal_uid`**（字符串 UID）；`create_goal` 绑定领域传 **`area_id`**（数字 ID）。\n3. **优先级 (`priority`) 类型异构律**：\n   - **任务与习惯 (`create_task` / `update_task` / `add_subtask` / `create_habit`)**：`priority` 为**字符串枚举** `\"none\" | \"low\" | \"medium\" | \"high\"`（🚫 **绝对禁止传 `\"urgent\"`**）；\n   - **项目 (`create_project` / `update_project`)**：`priority` 为**数字枚举** `0` (低)、`1` (中)、`2` (高)。\n4. **状态 (`status`) 枚举律**：\n   - 任务与项目的 `status` 严格限定为：**`\"not_started\" | \"planned\" | \"in_progress\" | \"waiting\" | \"done\" | \"cancelled\"`**（🚫 **绝对禁止传 `\"todo\"`**）；\n   - 目标 (`Goal`) 的 `status` 限定为：**`\"active\" | \"achieved\" | \"paused\" | \"dropped\"`**，周期 `horizon` 限定为 **`\"season\" | \"year\"`**。"}];
    const README_CONTENT = "# Tududi 全域任务管理与 OKR+GTD 生产力中枢插件 (tududi)\n\n专为 **Google Antigravity IDE / Desktop**、**DeepSeek Harness (DSH)** 与全集群智能体打造的一等公民原生任务管理与生产力中枢插件。将公司年度/季度 OKR 战略目标、业务专案 KR 拆解、日常 GTD 研发任务、周期性工程巡检习惯与周报/月报成果归档完全内聚，彻底替代零散的手工台账。\n\n---\n\n## 🌟 核心价值与架构定位\n\n1. **OKR + GTD 五层战略执行咬合**：\n   - 严格确立「领域 (Area: 工作/个人) ➔ 目标 (Goal: O1~O4) ➔ 项目 (Project: 核心 KR 载体) ➔ 职能标签 (Tag: 规划/开发/运维/汇报/缺陷) ➔ 两层任务 (Task/Subtask)」五级结构；\n   - 项目标题保持简短清爽，具体量化 KR 验收标准内聚于项目描述，旗下全部已完成任务的达成成果自动汇聚为季度/年度结案证明。\n\n2. **智能体三大自动作业神经反射**：\n   - 开局自动领活：新会话提及项目时自动盘点进行中与计划内任务，免除人工翻找文档交代背景的负担；\n   - 过程随手记分支与完工双行锚点：中途发现分支问题即时挂单零遗忘；结案前强制写入【达成成果】与【解决挑战】，一键支撑周报、月报与 OKR 导出。\n\n3. **双网自愈网关与五重物理拦截守卫**：\n   - 内置公网 HTTPS 端点与局域网直连端点毫秒级自动容灾切换，保障全天候零中断响应；\n   - 挂载前置拦截守卫，自动完成任务 id 与实体 uid 异构主键纠偏、空主键删除阻断、优先级/状态枚举校验及违规标签拦截。\n\n---\n\n## 🧭 构件导引与单一真相源 (SSOT)\n\n本插件已实现 100% 构件自治内聚，各资产明细直接通过上方 Tab 查阅：\n- **技能与命令**：见上方 **「技能」Tab**（涵盖五层映射字典、三大自动作业反射与 65 项算子分类速查）；\n- **MCP 算子矩阵**：见上方 **「MCP」Tab**（涵盖任务、子任务、依赖、项目、目标、领域、习惯、收集箱、笔记与视图全量 65 项工具）；\n- **生命周期守卫**：见上方 **「钩子」Tab**（涵盖前置五重参数纠偏与防标签滥用物理防线）；\n- **行为规约约束**：见上方 **「规则」Tab**（涵盖常驻潜意识意图分流与参数异构避坑契约）。\n";

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

      const handleSave = async () => {
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
        try {
          await fetch('http://127.0.0.1:19339/ov-dsh-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pluginId: PLUGIN_ID, shortName: SHORT_NAME, config: formConfig }),
            signal: AbortSignal.timeout(2000)
          });
        } catch (_) {}
        setSaving(false);
        setSaveToast({ ok: true, msg: '配置已持久化保存，并在 DSH 会话中实时生效' });
        setTimeout(() => setSaveToast(null), 3000);
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
        // 0. 局部注入样式：彻底物理蒸发 DSH 原生冗余的 "包含的组件" (<section data-plugin-rows>) 区块
        h('style', null, `
          div[data-plugin-detail] [data-plugin-rows] {
            display: none !important;
          }
        `),

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

    function apply(ctx) {
      const bundleKey = PLUGIN_ID;
      const shortKey = SHORT_NAME;

      // 启动时自动将浏览器端已保存的凭据同步至本机 Node.js 插件宿主，零手工干预生效
      try {
        const saved = loadSavedConfig();
        if (saved && (saved.endpointUrl || saved.userKey)) {
          fetch('http://127.0.0.1:19339/ov-dsh-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pluginId: PLUGIN_ID, shortName: SHORT_NAME, config: saved })
          }).catch(() => {});
        }
      } catch (_) {}

      // 1. 组合包详情页配置插槽 (Bundle Detail Page)
      ctx.slots.inject('plugins.bundle.config', () => {
        ctx.slots.register({ name: 'plugins.bundle.config', key: bundleKey }, UniversalDshPanel);
        if (shortKey !== bundleKey) {
          ctx.slots.register({ name: 'plugins.bundle.config', key: shortKey }, UniversalDshPanel);
        }
      });

      // 2. 全局设置插件页 Tab (Settings -> Plugins Tab)
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