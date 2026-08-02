# OpenViking Studio — 远期路线图与 Epic 规划 (ROADMAP.md)

> **规约**：当前的基线版本为 **`v1.2.25`**。本文档存放远期 Epic 愿景与大型模块规划（按 Milestone Phase 解耦）。当 Epic 准备进入迭代开发时，再拆解为原子工单填入 `REFACTORING_PLAN.md` 并在封板发版时映射具体 Tag。

---

## 📅 Milestone Phase 2 (v1.3.x 目标)：技能自演进闭环与质量门禁引擎

### 🚀 Epic-SKILL-LOOP：Skill-Loop 自进化闭环引擎
**愿景**：实现反思 -> Lesson 萃取 -> SKILL.md 审阅与回滚全流程。
- **解耦子工单**：
  - `LOOP-01`：修正事件的数据模型与 SQLite 存储结构
  - `LOOP-02`：物理校验结果与异常 Trace 自动捕获
  - `LOOP-03`：`CONTEXT / REFLECTION / LESSON` 3 段式萃取器
  - `LOOP-04`：Lesson 候选变更是/否人机协同审核页面
  - `LOOP-05`：`SKILL.md` 受控版本更新机制
  - `LOOP-06`：Git 分支与更新失败自动回滚
  - `LOOP-07`：清理与迁移遗留的 `~/self-improving/` 脚本

---

### 🚀 Epic-SKILL-OPT：SkillOpt Attempt / Judge 质量门禁引擎
**愿景**：基于微软 SkillOpt 论文构建 Attempt 执行 + Judge 门禁评分体系。
- **解耦子工单**：
  - `SKILLOPT-01`：Attempt 执行引擎与 Judge Gate 验证器
  - `SKILLOPT-02`：技能健康评分与自动修复建议生成
  - `SKILLOPT-03`：技能权重动态微调逻辑

---

## 📅 Milestone Phase 3 (v1.4.x / v2.0 目标)：在线创生与隐私安全治理

### 🚀 Epic-LIVE-GEN：Skill Live Generator 在线技能创生
**愿景**：可视化生成、编辑与沙盒验证 SKILL.md。
- **解耦子工单**：
  - `LIVEGEN-01`：SKILL.md 在线 Monaco 编辑器与 YAML Header 语法校验
  - `LIVEGEN-02`：沙盒环境模拟触发测试
  - `LIVEGEN-03`：一键自动向量化发布至 Viking 1933 存储

---

### 🚀 Epic-PRIVACY-GOV：端到端数据隐私与敏感信息治理
**愿景**：多 Agent 共享环境下的敏感信息二次授权与擦除防护。
- **解耦子工单**：
  - `PRIVACY-01`：服务端敏感字段检索二次过滤
  - `PRIVACY-02`：前端脱敏展示与安全展示开关
  - `PRIVACY-03`：脱敏审计日志与导出隔离

