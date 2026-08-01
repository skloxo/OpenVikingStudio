# OpenViking Studio — 唯一活跃原子工单看板 (REFACTORING_PLAN.md)

> **三层治理体系说明**：
> 1. **历史交付记录** ➔ 归档至 [DELIVERY_ARCHIVE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)（已交付 `v1.1.0` ~ `v1.1.24`）
> 2. **远期愿景与 Epic 路线图** ➔ 移入 [ROADMAP.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/ROADMAP.md)（按 Epic 拆解管理）
> 3. **本文档 (REFACTORING_PLAN.md)** ➔ **唯一活跃原子工单看板**（仅保留当前可调度、数据契约明确、验收标准量化的最小原子工单）

---

## 📅 当前正在调度的核心迭代 (Active Scheduled Tasks)

### ✅ v1.1.25 [已验收通过 ✅] 技能中心 6 卡片 3x2 KPI 观察阵列 + 布局精简 + 0 Mock 数据强约束

- **Git Tag**: `v1.1.25` (commit `f8c3017`)
- **交付内容**：
  - 扩张技能中心 KPI 区为 **6 大高价值 KPI 卡片 (3x2 矩形阵列)**
  - 新增 **`技能资产活跃复用率`** (显示活跃技能数/总技能数，解决僵尸技能盲区)
  - 新增 **`Context 提示词压缩率`** (显示结构化 SOP 节省 Context 比例，衡量 Token 降本)
  - 切除 header 冗余分割横线 `border-b`，使用 `items-end` 使 `3小时 Rolling` Badge 与副标题对齐
  - 移除了 `补全简介` 按钮与 `已装载 N 个技能` 重复 Badge，将搜索框右对齐嵌入 Scope 筛选栏
  - 彻底清洗硬编码 `98.6%` 和假满分 `100.0%` fallback，无记录时统一物理直白显示 `--`
- **修改文件**：`vite.config.ts` · `src/routes/skills/route.tsx` · `REFACTORING_PLAN.md`

---

### ✅ v1.1.24 [已验收通过 ✅] 技能中心 KPI 24H 滚动窗口 + 零 Mock 清洗 + 语义 Badge + 崩溃修复

- **Git Tag**: `v1.1.24` (commit `255ca50`)
- **交付内容**：
  - 4 大 KPI 卡片统计窗口切换至 **最近 24 小时 (24H Rolling)**，API 参数 `?window=24h` 显式传递
  - 彻底清洗 `find_calls: 210 / store_calls: 18 / total_calls: 228` 等全部 Mock 假数字，初始值归零
  - 修复缺失 `SearchIcon` import 导致的页面崩溃（Lesson #29）
  - 恢复 KPI 卡片 Badge 语义标签（意图感应 / 闭环质量 / 踩坑演进飞轮 / 白盒审计），去除冗余 `24H` 前缀（Lesson #30）
  - SKILL.md 归档 Lesson #26 ~ #30
- **修改文件**：`vite.config.ts` · `src/routes/skills/route.tsx` · `.agents/skills/openviking-studio-dev/SKILL.md`

---

### 📌 P0: [ ] v1.2.0-A：Harness 自然语言意图碰撞与语义歧义在线探测引擎

**类型**：Architecture / Feature  
**优先级**：P0 (高优先级 - 紧随任务中心/技能中心后执行)  
**来源**：用户指导 ("把哈尼斯的这个迭代优化写成原子化的任务卡片，优先级提到高一点... 准备做哈尼斯还有 Loop 的迭代")  
**负责人**：Agent (Antigravity)  
**预计规模**：S (1 个迭代)

#### 1. 目标
当 Wiki 或系统入库新技能时，Harness 引擎自动计算其 `description` 与已装载 175 个技能的语义向量距离。当重叠度 > 85% 时在后台发出“意图碰撞预警”并自动辅助微调区分度，彻底解决多技能争抢唤醒词的痛点。

#### 2. 量化验收标准
- [ ] 后端 `/api/v1/system/harness_collision_check` 接口可返回碰撞度 > 85% 的技能对列表。
- [ ] 前端技能详情抽屉中透明显示语义相似度警告及建议触发词微调提示。

---

### 📌 P0: [ ] v1.2.0-B：Harness 技能沙盒静默跑测与基准评估校验 (Sandbox Dry-Run Check)

**类型**：Architecture / Feature  
**优先级**：P0 (高优先级)  
**来源**：用户指导 (Harness 引擎迭代排期)  
**负责人**：Agent (Antigravity)  
**预计规模**：S (1 个迭代)

#### 1. 目标
新技能完成格式与简介生成后，Harness 引擎在隔离上下文 (Isolated Sandbox) 中试跑一次模拟 Dry-Run 校验，提前验证 SOP 步骤与 MCP 工具参数合规性，实现“上线即保通、零挂起”。

#### 2. 量化验收标准
- [ ] 隔离沙盒环境支持静默模拟执行技能并生成物理 Dry-Run 校验报告。
- [ ] `/harness-logs` 审计页同步呈现 Dry-Run 沙盒校验打点及通过状态。

---

### 📌 P0: [ ] v1.2.0-C：Harness SOP 提示词自适应进化与版本回溯飞轮 (Prompt Auto-Tuning)

**类型**：Architecture / Feature  
**优先级**：P0 (高优先级)  
**来源**：用户指导 (Harness 引擎迭代排期)  
**负责人**：Agent (Antigravity)  
**预计规模**：S (1 个迭代)

#### 1. 目标
结合近 24 小时技能运行成功率与报错记录，Harness 反思引擎物理自动提炼改写建议，并支持自动调整 `SKILL.md` 中模糊的 SOP 说明，形成版本改写履历。

#### 2. 量化验收标准
- [ ] 自动提炼微调建议并支持在 `SKILL.md` 中以 diff 履历追溯。
- [ ] 与 OpenViking 体外大脑 (`viking://resources/master_memory/`) 实时物理同步。

---

### 📌 P0: [ ] v1.2.0-D：Harness 运行时最小权限防线与白盒拦截账本 (Runtime Guardrails Ledger)

**类型**：Security / Architecture  
**优先级**：P0 (高优先级)  
**来源**：用户指导 (Harness 引擎迭代排期)  
**负责人**：Agent (Antigravity)  
**预计规模**：S (1 个迭代)

#### 1. 目标
在 Agent 动态调取技能执行时，Harness 动态管控允许调用的 MCP 工具白名单 (`allowed_tools`)，物理拦截越权操作与高危系统指令，白盒输出拦截账本。

#### 2. 量化验收标准
- [ ] 动态拦截违规 API/MCP 工具调用并生成白盒拦截日志。
- [ ] `/harness-logs` 呈现实时白盒拦截账本。

---

### 📌 P0: [ ] v1.1.23c：技能中心双门锁合规探针、待规范白盒曝光与一键规范化上架流程

**类型**：Feature  
**优先级**：P0 (用户明确指令：提前并集中在当前技能中心迭代中完成)  
**来源**：用户指导 ("关于技能中心进行迭代，往前提一提... 既能显示出合规的又能显示出不合规的... 一键规范化并上架")  
**负责人**：Agent (Antigravity)  
**预计规模**：S (1 个迭代)

#### 1. 问题描述
当前技能中心页面仅展示部分从后端口径读取到的已加载技能（黑盒），缺少对本地所有探针扫描到的“不合规技能（如缺失 `SKILL.md` 或缺 YAML Header）”的白盒曝光，且缺少一键补全规范要件并向 OpenViking 向量库上架的功能。

#### 2. 目标
1. **白盒双 Tab 渲染**：在 `/skills` 页面增加 `已就绪标准技能 (146)` 与 `⚠️ 待规范技能 (12)` 双分栏。
2. **缺件物理诊断**：透明列出待规范技能的名称、绝对路径、及具体缺件原因（如 `❌ 缺失 SKILL.md 文件`）。
3. **一键规范化上架**：提供 `⚡ 一键规范化上架` 交互按钮，自动补充合规 YAML Header 范本并生成 `SKILL.md`，自动建软链接并触发 1933 向量化索引上架！

#### 3. 数据与接口契约 (Data Contract)
- **API 接口**：`GET /api/v1/skills` 及网关本地探针 `_auto_sync_skills()`
- **关键字段**：
  - `name`: string (技能或目录名称)
  - `status`: `'compliant' | 'non_compliant'`
  - `missing_reason`: string (诊断原因，如 `'missing_skill_md' | 'missing_header'`)
  - `path`: string (本地绝对路径)

#### 4. 实施边界 (Domain Scope)
- 仅修改 `src/routes/skills/route.tsx` 及 `mcp-openviking/mcp_openviking_server.py`。

#### 5. 量化验收标准
- [ ] **物理诊断曝光**：技能页清晰展示 `已就绪 (146)` 与 `待规范 (12)` 统计，切换 Tab 能全量透视不合规技能清单与具体缺件原因。
- [ ] **一键规范化上架**：在 UI 点击“⚡ 规范化上架”，自动生成合规 `SKILL.md`，技能状态实时迁移至 `已就绪` 栏。
- [ ] **视觉规范**：遵循 NO GREEN EVER 规则，警告使用 `rose-500/80`，推荐按钮使用 `cyan-500`。
- [ ] **构建验证**：`npm run build` 无 TypeScript / Vite 编译报错。

#### 6. 验证命令
```bash
npm run build && cp -r dist/* /home/skloxo/.local/lib/python3.12/site-packages/openviking/web_studio/dist/
```

---

## 📅 Harness 物理级 3 层架构重构细粒度原子工单 (Atomic Harness Tasks)

### 📌 Task 1: [x] Harness Pre-Tool 物理前置拦截门锁 (NeMo Guardrails 式硬阻断) ✅

**类型**：Architecture & Safety  
**静态/物理验证**：已在 `mcp_openviking_server.py` 实现 `_harness_pre_execution_guard` 物理拦截函数并提交 Git (`ca30c41`)。支持拦截 `scripts/` 与 `public/` 下创建游离脚本、拦截未终验复制至 1933，拦截触发自动记录日志。

---

### 📌 Task 2: [x] Harness Reflexion 隐式自演进与向量重索引钩子 (Reflexion 模式) ✅

**类型**：Self-Evolution Engine  
**静态/物理验证**：已在 `mcp_openviking_server.py` 实现 `openviking_record_evolution_lesson` MCP 工具与 Reflexion 钩子函数并提交 Git (`76f5ae1`)。支持自动抽取 3 段式 Lesson 写入 `SKILL.md`，并增量更新度量与向量索引。

---

### 📌 Task 3: [x] 1936 UI 纯真实白盒透视看板对齐 ✅

**类型**：UI Alignment  
**静态/物理验证**：已在 `/skills` 页面全量对接 `Task 1` 与 `Task 2` 产生的底层指标日志并提交 Git (`2af99b4`)。卡片 1 物理渲染拦截器 `blockedCalls` 物理阻断次数；卡片 4 物理渲染 Reflexion 自演进 `lessons_count`。物理平齐底栏，NO GREEN EVER 色盘，彻底消除任何写死假数据与噪音文案。

---

### 📌 P1: [ ] v1.1.23d：全盘游离临时脚本与非源码文件彻底审计清洗专项

**类型**：Refactoring & Cleanup  
**优先级**：P1 (用户明确指令：技能中心开发完成后立即执行全盘排查)  
**来源**：用户指导 ("对我们自己开发的这些代码，以及 OpenWiki 所有的内容进行纠偏... 严禁在 scripts/ 或 public/ 乱写临时 .py/.json")  
**负责人**：Agent (Antigravity)  
**预计规模**：S (1 个迭代)

#### 1. 问题描述
历史上在开发调试过程中，可能遗留了某些游离在 `scripts/`、`public/` 或根目录下的临时 `.py`、`.json`、`.sh` 脚本或辅助文件。需要全盘白盒扫描，彻底清理一切违背“直改源码”原则的杂质文件。

#### 2. 目标与验收标准
1. **全盘扫隐患**：对 `OpenVikingStudio` 及 `mcp-openviking` 进行全盘物理扫描，找出所有不在标准 Git/源码目录下的游离脚本。
2. **源码级归集**：将所有合理逻辑 100% 收敛至 React 源码 component/route 或 Backend python 服务主逻辑中。
3. **零杂质交付**：彻底删除 `scripts/` 与 `public/` 下一切临时 `.py`/`.json` 文件，`git status` 显示绝对干净。

---

## 📋 待调度后续原子工单 (Backlog Queue)

### 📌 P1-1: [ ] v1.1.23d：检索测试台 `/retrieval` 页 L0/L1 白盒检索轨迹树与得分渲染
### 📌 P1-2: [ ] v1.1.23e：监控页 `/monitoring` Token 节省率与 SLA 时延对比折线图
### 📌 P2-1: [ ] v1.1.24a：核心服务心跳采集与健康探针模型
### 📌 P2-2: [ ] v1.1.24b：首页健康状态徽章与 CLI 降级告警
