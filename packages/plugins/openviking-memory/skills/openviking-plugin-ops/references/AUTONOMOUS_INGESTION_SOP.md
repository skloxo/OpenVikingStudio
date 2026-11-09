# 🧪 技能自动化准入四阶流水线规约 (Autonomous Ingestion Pipeline SSOT)

> **定位**：规范技能入库流程，彻底杜绝手工文件拷贝导致的索引脱节。


## 🧪 十、 Card-95 & Card-165 技能自动化准入演进流水线规约 (Autonomous Ingestion Pipeline SSOT) ⭐⭐⭐⭐⭐

> **核心第一性原理 (2026-10-19 铭刻)**：  
> “正常来说，VK技能中心感知到有新技能以后，它会走一个自动化的流程，这个技能才能正常的入库。”  
> 绝对禁止 Agent 使用 `cp`、`mv` 等方式手工拷贝技能文件到 `agent/skills/` 底层目录！必须由守护进程自动发现，或通过官方 API 提交，经过事务队列、视网膜门禁校验、大包归属判定、场景结晶与向量构建全流程后，状态机转为 `COMMITTED` 方完成合法入库。

### 1. 自动化准入四阶流水线 (The 4-Stage Autonomous Pipeline)

1. **自动侦测与投递 (Detection & Ingestion)**：
   - 本地开发目录变更由 `skill_syncer` 守护线程自动探测内容哈希；
   - 或通过 HTTP 接口 `POST /api/v1/skills/ingestion/submit` 投递；
   - 写入 `skill_ingestion_inbox.db` 事务数据库，生成唯一 `receipt_id`，初始状态为 `PENDING`。
2. **多维视网膜门禁校验 (Retina & Security Validation)**：
   - 校验 YAML Frontmatter（`name`, `description`, `version`, `author`）；
   - 执行 Zero-Secrets 零凭据泄漏审计（拦截高熵密码、Token、API Key）；
   - 执行领域 Seam 判定，动态评估领域亲和度与上下文内聚度，自动决策归入合适母包场景或自立新包。若不合规立即流转为 `REJECTED` 并记录失败根因。
3. **衍生结晶与索引重构 (Distillation & Indexing)**：
   - 自动在母包场景下生成 `.abstract.md`、`.overview.md`；
   - 自动刷新 `all_skills.json` 注册表与技能关系图谱；
   - 触发后台向量重构与 BM25 全文检索索引建立。
4. **事务提交与入籍 (Commitment & Receipt Finalization)**：
   - 状态机最终流转为 **`COMMITTED`**，生成不可变入库凭证；
   - 技能中枢对外 API 即刻可查询，动态投影至所有已授权的智能体与客户端。

### 2. 手工拷贝的反模式与破坏性后果 (Failure Mode of Manual Copying)
- **绕过安全审查**：手工拷贝跳过了密钥与敏感信息审查；
- **缺失事务凭证**：跳过 `skill_ingestion_inbox` 导致无 `receipt_id`，无法追踪来源与版本履历；
- **索引与大包断层**：未生成母包场景抽象与向量嵌入，导致“文件在磁盘上，但智能体检索网关搜不到”。

---

## 🧪 九、 演进教训库 (Evolution Lessons Persisted)

---
