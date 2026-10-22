# OpenViking 记忆中枢交互与隔离准则 (Memory SSOT & Isolation Rules)

1. **唯一真相源 (SSOT)**：
   全系统所有架构决策、凭据配置与历史经验统一收口在 `viking://resources/master_memory/`，打破单会话与单智能体隔离。
2. **私有与共享双层隔离**：
   - 空间公共层：全智能体共享，用于权威规约与架构共识；
   - 专属私有层：按 User ID 打标隔离（如 `AntigravityIDE@2080Ti`），过程性草稿与排障流水账默认不跨号污染。
3. **安全与凭据铁律**：
   - 严禁在代码、注释或对话中泄露明文 API Key；
   - 客户端连接统一通过插件配置动态注入。
