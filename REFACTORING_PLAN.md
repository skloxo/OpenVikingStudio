# OpenViking Studio — 唯一活跃原子工单看板 (REFACTORING_PLAN.md)

> **双轨制管理规约 (Dual-Track Management Rules)**：
> 1. **工单 ID 解耦 (Task ID Decoupling)**：卡片使用模块持久化 ID（如 `TASK-SKILL-01` / `TASK-HARNESS-01`），**严禁在排期阶段过早绑定版本号**！插队/新增任务时可无缝创建新工单 ID。
> 2. **阶段封板映射 (Milestone Tag Binding)**：按【阶段目标 Milestone】进行分组管理；只有当用户显式下达“封板/打 Tag 发版”指令时，AI 才有权限根据实际交付按顺序映射物理 Tag（当前基线为 `v1.2.35`）。
> 3. **本地私有留存**：本文件及内部研发记录只在本地管理 (`.gitignore`)，远程仓库保持绝对代码纯净与数据脱敏。

---

## 📅 第一部分：【当前核心执行阶段：Phase 1 — 技能中心与 Harness 引擎双向打通】

---

### 📌 P0: [ ] [TASK-HARNESS-SOP-01] 预制规约检查引擎与全量技能简介自动生成闭环 (Builtin SOP & Description Auto-Gen)

**模块**：Harness 引擎 + 技能中心  
**工单 ID**：`TASK-HARNESS-SOP-01`  
**优先级**：P0（最高）  
**来源**：用户指导 — 36 条预制规约当前仅为 UI 硬编码数组无检查；260+ 技能无简介显示"暂无额外说明"  
**预计规模**：M (2 个迭代)

#### 1. 现状与根因
- `BUILTIN_LESSONS`（36条）在 `harness-logs.tsx` 中为 UI 硬编码静态数组，缺乏后台 Python 逻辑进行真实审计与阻断；
- 大量技能 `SKILL.md` 的 YAML frontmatter 缺少 `description` 字段，后端返回空字符串，前端退化显示"暂无额外说明"；
- 缺乏自动扫描与后台 LLM 提炼无人值守生成管道。

#### 2. 交付目标与技术方案
1. **预制规约静态/动态检查**：建立后台算子 `harness_sop_checker.py`，遍历全量 260+ 技能检查：
   - 是否包含规范 `SKILL.md` (Rule 14)
   - `description` 是否存在且 >10 字 (Rule 31)
   - 检查结果输出至 `harness_metrics.json`，算出真实合规率 (%) 并在 Harness 审计页曝光；
2. **简介后台自动生成**：对无描述的技能，调用 Harness LLM（依赖 `TASK-HARNESS-LLM-01`）提炼 30 字中文自解释，写回 `SKILL.md` YAML frontmatter。

#### 3. 量化验收标准
- [ ] 36 条规约转换为真正可运行的 Python 合规检查器；
- [ ] 260+ 技能卡片中的“暂无额外说明”被自动提炼生成的中文简介替换；
- [ ] Harness 审计页展示全盘技能真实合规率 (%)。

---

### 📌 P1: [ ] [TASK-SESSION-SYNC-01] IDE ↔ OpenViking 全量会话与记忆实时自动同步 (Session & Memory Auto-Sync)

**模块**：OpenViking Session Gateway + FastMCP  
**工单 ID**：`TASK-SESSION-SYNC-01`  
**优先级**：P1  
**来源**：用户疑问 — IDE 会话是否自动传给 VK？首页“今日检索次数”为何显示 0 次？  
**预计规模**：M (2 个迭代)

#### 1. 现状与根因
- IDE 与 OpenViking 的交互目前仅在 Agent 主动调用 `memory_store` 时沉淀，会话消息未实时流式写入 `/api/v1/sessions`；
- 首页调用的 `/api/v1/console/dashboard/summary` 依赖 `today_retrievals`，由于未自动捕捉隐式检索，导致数据呈现为 0。

#### 2. 交付目标与技术方案
1. **会话静默实时流转**：在 MCP 服务器 (`mcp_openviking_server.py`) 中增加消息拦截 Hook，在交互过程中自动调用 `openviking.session` 写入会话历史；
2. **检索次数物理统计**：将 MCP 隐式与显式检索统一汇入 `today_retrievals` 统计，使首页“今日检索次数”真实更新。

#### 3. 量化验收标准
- [ ] IDE 会话消息实时同步至 OpenViking Studio `/sessions` 页面；
- [ ] 首页“今日检索次数”随交互真实增加，不再恒定为 0。

---

### 📌 P1: [ ] [TASK-SKILL-CENTER-01] 隐式自动唤醒率真实数据打通 (auto_wakeup_rate via MCP 主动上报)

**模块**：技能中心 全托管感应引擎 + Harness MCP  
**工单 ID**：`TASK-SKILL-CENTER-01`  
**优先级**：P1  
**来源**：`auto_wakeup_rate` 当前缺少 `find_calls` 主动上报数据  
**预计规模**：S (1 个迭代)

#### 1. 交付目标
1. **后端 (`mcp_openviking_server.py`)**：在 `openviking_find` / `openviking_search` MCP 工具内，识别命中的 SKILL.md 路径，将 `skill_name` 写入 `harness_metrics.json` 的 `skill_find_log` 字段；
2. **后端 (`system.py`)**：`get_harness_metrics()` 从 `skill_find_log` 统计 `find_calls` 并派生 `auto_wakeup_rate`。

#### 2. 量化验收标准
- [ ] 调用一次 `openviking_find` 后，`harness_metrics` 返回 `auto_wakeup_rate > 0`；
- [ ] 技能中心“隐式自动唤醒率”显示真实百分比。

---

### 📌 P2: [ ] [TASK-SKILL-CENTER-02] Context 提示词压缩率实现 (context_compression_ratio via LLMLingua-2)

**模块**：技能中心 + Harness 引擎  
**工单 ID**：`TASK-SKILL-CENTER-02`  
**优先级**：P2  
**来源**：`context_compression_ratio` 字段待接入组件化压缩模型  
**预计规模**：M (2 个迭代)

#### 1. 交付目标与技术方案
1. 遵从 Rule 7（组件化嵌入与非侵入式适配原则），在同进程内初始化微型 `LLMLingua-2` 概率筛选模型；
2. 针对注入给 Agent 的 SOP 提示词进行动态 Token 压缩，固化超参数 `rate=0.50`，保护 YAML Header 与代码块；
3. 将实际省下的 Token 比率写入 `harness_metrics.json` 中的 `context_compression_ratio`。

#### 2. 量化验收标准
- [ ] 技能中心 KPI 卡片 5 展示真实 Token 压缩率（如 `35.4%`）；
- [ ] 压缩算法熔断保底，不影响主服务稳定性。

---

### 📌 P2: [ ] [TASK-HARNESS-LLM-01] Harness 配置化 LLM 后端集成

**模块**：Harness 引擎  
**工单 ID**：`TASK-HARNESS-LLM-01`  
**优先级**：P2  
**来源**：实现无人值守技能描述生成与反思萃取的 LLM 算子基础  
**预计规模**：S (1 个迭代)

#### 1. 交付目标
- `ov.conf` 增加可选 `[harness.llm]` 配置块（`base_url`, `api_key`, `model`）；
- 若未配置则优雅降级回退至本地 VLM 代理服务 (`mimo-v2.5` on `:8317`)。

---

## 📅 第二部分：【远期规划 backlog 阶段：Phase 2 & Phase 3 — 技能自演进与在线创生】

> 说明：本阶段卡片来自 `ROADMAP.md`，当 Phase 1 核心打通并封板发版后，按顺序进入 Phase 2/3 开发。

---

### 🚀 Milestone Phase 2：技能自演进闭环与质量门禁引擎 (v1.3.x 目标)

#### 1. `[TASK-LOOP-01~07]` Epic-SKILL-LOOP 自进化闭环引擎
- `TASK-LOOP-01`：修正事件的数据模型与 SQLite 存储结构；
- `TASK-LOOP-02`：物理校验结果与异常 Trace 自动捕获；
- `TASK-LOOP-03`：`CONTEXT / REFLECTION / LESSON` 3 段式自动萃取器；
- `TASK-LOOP-04`：Lesson 候选变更人机协同审核 View；
- `TASK-LOOP-05`：`SKILL.md` 受控版本安全更新与 Git 自动回滚。

#### 2. `[TASK-SKILLOPT-01~03]` Epic-SKILLOPT 质量门禁引擎
- `TASK-SKILLOPT-01`：Attempt 执行引擎与 Judge Gate 评分验证器；
- `TASK-SKILLOPT-02`：技能健康评分与自动修复建议生成；
- `TASK-SKILLOPT-03`：技能权重动态微调与排名算法。

---

### 🚀 Milestone Phase 3：在线创生与端到端隐私安全治理 (v1.4.x / v2.0 目标)

#### 1. `[TASK-LIVEGEN-01~03]` Epic-LIVE-GEN Skill Live Generator
- `TASK-LIVEGEN-01`：SKILL.md 在线 Monaco 编辑器与 YAML Header 语法校验；
- `TASK-LIVEGEN-02`：沙盒环境模拟触发测试；
- `TASK-LIVEGEN-03`：一键自动向量化发布至 Viking 1933 存储。

#### 2. `[TASK-PRIVACY-01~03]` Epic-PRIVACY-GOV 敏感信息二次授权
- `TASK-PRIVACY-01`：服务端敏感字段检索二次过滤与鉴权；
- `TASK-PRIVACY-02`：前端脱敏展示与安全开关；
- `TASK-PRIVACY-03`：脱敏审计日志与导出隔离。

---

## 📦 第三部分：【历史已验收交付归档 (Delivery Archive)】

> 说明：本部分记录已完成开发、验收通过并打入 Git Tag 的物理历史工单。

- **`[TASK-SKILL-FILECOUNT-01]`** 技能卡片全量关联文件数准确透视 ✅
  - **交付 Tag**：`v1.2.35` | **Commit**：`22541b5`
  - **内容**：后端递归扫描 `file_count`，前端卡片动态精准呈现（如 `openviking-master` 显示 `4 文件`）。

- **`[TASK-METRICS-CONSOLIDATION-01]`** Harness 指标与全局去重修复 ✅
  - **交付 Tag**：`v1.2.34` | **Commit**：`c1312bd`
  - **内容**：`system.py` 注入 `active_skills_count` 与 5 分钟 inotify 去重感应。

- **`[TASK-HARNESS-LOGS-PERSISTENCE-01]`** Harness Logs 拦截日志物理持久化 ✅
  - **交付 Tag**：`v1.2.33` | **Commit**：`90812ab`
  - **内容**：解决 F5 刷新日志丢失问题，实现持久化落盘。
