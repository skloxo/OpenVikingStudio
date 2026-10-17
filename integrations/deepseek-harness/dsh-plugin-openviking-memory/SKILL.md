# 🧠 OpenViking 核心长程记忆与代码战地操作说明书 (SKILL.md)

## 一、身份契约与能力定位
本机智能体已挂载 OpenViking 核心长程记忆与代码感知完全体，拥有体外大脑中枢。
全系统共授权挂载 34 项战地武器与 3 项 Hook 物理守卫，开箱即用。

## 二、严禁行为 (Negative Guardrails) 🚫
1. **绝对禁止自写 Python 脚本测试工具**：所有工具已通过原生 FastMCP 挂载到当前会话，直接发起 Tool Call，严禁在工作区编写 `probe_*.py`、`test_*.py` 脚本盲跑探测；
2. **绝对禁止盲目全量读取大文件**：严禁无脑读取上千行源码，必须遵循「`openviking_code_outline` ➔ `openviking_grep` ➔ `openviking_code_expand`」三级渐进展开；
3. **绝对禁止伪造虚拟数据**：无数据时优雅显示 `--` 或明确告知，禁止 mock 假数据。

## 三、战地武器清单与调用规范 (34 Tools SSOT)

### 1. 核心长程记忆与资源读写
- `openviking_find(query: str, target_uri: str = "viking://", limit: int = 10)`: 语义检索体外大脑中的知识、架构偏好与踩坑经验；
- `openviking_search(query: str, target_uri: str = "viking://", limit: int = 10)`: 关键字/混合快速检索；
- `openviking_read(uri: str)`: 深度读取指定 viking:// 资源或长文本事实；
- `openviking_write(uri: str, content: str, mode: "replace"|"append"|"create" = "replace")`: 物理持久化落盘至 VikingFS；
- `openviking_edit(uri: str, old_string: str, new_string: str)`: 精准替换指定 viking:// 文件的局部文本；
- `openviking_remember(text: str, role: "user"|"assistant" = "user")`: 沉淀高价值对话或上下文事实至记忆中枢；
- `openviking_tree(uri: str = "viking://resources/", max_depth: int = 3)`: 递归查看 VikingFS 资源目录树；
- `openviking_grep(pattern: str, uri: str = "viking://resources/")`: 在 VikingFS 资源中执行正则检索；
- `openviking_glob(pattern: str, uri: str = "viking://resources/")`: 文件通配符路径检索；
- `openviking_add_resource(path: str)`: 导入本地文件至 VikingFS。

### 2. 代码感知与符号深潜
- `openviking_code_outline(target_uri: str)`: 秒级提纯代码文件的类、函数与结构大纲；
- `openviking_code_search(query: str, target_uri: str = "viking://")`: 全局检索代码符号（类名、函数名、常量）；
- `openviking_code_expand(target_uri: str, symbol_name: str)`: 紧凑展开单个符号的具体实现，保护上下文。

### 3. 经验沉淀与活态工单
- `openviking_record_evolution_lesson(category: str, title: str, lesson_learned: str, root_cause: str, trigger_context: str, verification_evidence: str, tags: list[str])`: 根治重大 Bug 或突破死锁后，持久化沉淀至 Master Memory；
- `openviking_file_task_card(task_id: str, title: str, acceptance_criteria: list[str])`: 登记原子化任务卡片；
- `openviking_task_cards_summary()`: 统计当前待办与已完成卡片概览；
- `openviking_list_pending_cards()`: 列出当前未完成任务卡片；
- `openviking_resolve_task_card(task_id: str, commit_hash: str)`: 验收变绿后闭环完成卡片。

### 4. 运行时治理与上下文加速
- `openviking_tokenshift_compress(text: str, mode: "aggressive"|"balanced"|"lossless")`: 上下文高密压缩脱水；
- `openviking_valet_handover(session_summary: str, next_steps: list[str])`: 会话总结与无缝交接；
- `openviking_audit_skills()`: 扫描并审计当前技能合规性；
- `openviking_auto_onboard_skills()`: 自动纳管并激活待处理技能；
- `openviking_health()`: 核心通信链路健康存活探测。

## 四、经典作战 SOP
1. **开局检索**：面临复杂任务时，第一时间调用 `openviking_find(query="...")` 召回历史最佳经验；
2. **代码探索**：先调 `openviking_code_outline` 查看文件大纲，再调 `openviking_code_expand` 精准展开特定函数；
3. **闭环留痕**：攻坚变绿后，调用 `openviking_record_evolution_lesson` 写入体外大脑，实现跨会话智力复利。
