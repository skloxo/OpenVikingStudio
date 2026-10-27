# OpenViking 记忆中枢交互与隔离准则 (Memory SSOT & Isolation Rules)

1. **唯一真相源 (SSOT)**：
   全系统所有架构决策、凭据配置与历史经验统一收口在 `viking://resources/master_memory/`，打破单会话与单智能体隔离。
2. **私有与共享双层隔离**：
   - 空间公共层：全智能体共享，用于权威规约与架构共识；
   - 专属私有层：按 User ID 打标隔离（如 `AntigravityIDE@2080Ti`），过程性草稿与排障流水账默认不跨号污染。
3. **安全与凭据铁律**：
   - 严禁在代码、注释或对话中泄露明文 API Key；
   - 客户端连接统一通过插件配置动态注入。
4. **过程草稿与主脑物理隔离公理 (Zero Interference in Flight)**：
   - 交互调试与开发过程中产生的一切中间文档、调试脚本和临时配置必须物理隔离在本地工作区或脑区临时目录；
   - 严禁将未经验证的草稿与推测参数倒灌入 `viking://resources/master_memory/`；
   - 生命周期 Hook 保持绝对静默，严禁在交互中途弹窗中断人类心流。
5. **结案与交接闭环契约 (Contractual Closure & Zero Leaks)**：
   - 智能体在宣布“任务结案”或用户触发 `/handover`（会话交接）时，必须执行物理清点对账；
   - **若踩坑**：必须调用 `openviking_record_evolution_lesson` 录入体外大脑；
   - **若形成新范式/新规**：必须调用 `openviking_write` 直写 `viking://resources/master_memory/recipes/`；
   - 结案回复文末强制附带存盘 URI 对账单，严禁将已验证经验遗留为本地未同步死数据。
