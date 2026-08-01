# OpenViking Studio — 远期路线图与 Epic 规划 (ROADMAP.md)

> 本文档存放 OpenViking 系统的远期 Epic 愿景与大型模块规划。当 Epic 准备进入迭代开发时，再拆解为原子工单写入 `REFACTORING_PLAN.md`。

---

## 🚀 Epic v1.1.24：Skill-Loop 自进化闭环引擎
**愿景**：实现反思 -> Lesson 萃取 -> SKILL.md 审阅与回滚全流程。
- **子任务拆解**：
  - `v1.1.24a`：修正事件的数据模型与 SQLite 存储结构
  - `v1.1.24b`：物理校验结果与异常 Trace 自动捕获
  - `v1.1.24c`：`CONTEXT / REFLECTION / LESSON` 3段式萃取器
  - `v1.1.24d`：Lesson 候选变更是/否人机协同审核页面
  - `v1.1.24e`：`SKILL.md` 受控版本更新机制
  - `v1.1.24f`：Git 分支与更新失败自动回滚
  - `v1.1.24g`：清理与迁移遗留的 `~/self-improving/` 脚本

---

## 🚀 Epic v1.1.25：SkillOpt Attempt / Judge 质量门禁引擎
**愿景**：基于微软 SkillOpt 论文构建 Attempt 执行 + Judge 门禁评分体系。
- **子任务拆解**：
  - `v1.1.25a`：Attempt 执行引擎与 Judge Gate 验证器
  - `v1.1.25b`：技能健康评分与自动修复建议生成
  - `v1.1.25c`：技能权重动态微调逻辑

---

## 🚀 Epic v1.1.26：Skill Live Generator 在线技能创生
**愿景**：可视化生成、编辑与沙盒验证 SKILL.md。
- **子任务拆解**：
  - `v1.1.26a`：SKILL.md 在线 Monaco 编辑器与 YAML Header 语法校验
  - `v1.1.26b`：沙盒环境模拟触发测试
  - `v1.1.26c`：一键自动向量化发布至 Viking 1933 存储

---

## 🚀 Epic v1.1.40：端到端数据隐私与敏感信息治理
**愿景**：多 Agent 共享环境下的敏感信息二次授权与擦除防护。
- **子任务拆解**：
  - `v1.1.40a`：服务端敏感字段检索二次过滤
  - `v1.1.40b`：前端脱敏展示与安全展示开关
  - `v1.1.40c`：脱敏审计日志与导出隔离
