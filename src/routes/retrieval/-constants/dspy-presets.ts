/**
 * Stanford DSPy (MIPO) 强类型提示词编译器预设案例库 (SSOT)
 */

import type { BootstrapExample } from "../-types/dspy-compiler";

export interface DSPyPreset {
  id: string;
  name: string;
  category: string;
  description: string;
  signatureName: string;
  taskObjective: string;
  rawPrompt: string;
  candidateExamples: BootstrapExample[];
}

export const DSPY_PRESETS: DSPyPreset[] = [
  {
    id: "text-to-sql",
    name: "Text-to-SQL 工业级强类型查询编译器",
    category: "Data Engineering",
    description: "将松散业务自然语言查询精确编译为受控 PostgreSQL 方言与防注入规约",
    signatureName: "TextToPostgreSQLCompiler",
    taskObjective: "根据用户的自然语言业务诉求和数据库结构，生成经过语法验证的只读 SQL 查询",
    rawPrompt: `你是一个资深数据库架构师与 SQL 专家。
输入参数:
- Query: 用户自然语言查询诉求 (例如 "统计过去7天活跃交易账户总成交额")
- Schema: 数据库表结构定义与索引详情
输出结果:
- SQL: 生成的 PostgreSQL 合规查询语句
- TargetTables: 涉及的表名列表
- Explanation: 业务逻辑推导解释
- IsSafeReadOnly: 是否满足只读防注入约束 (boolean)

严格业务约束:
1. 严禁生成 DROP, DELETE, UPDATE, INSERT, ALTER 等具有写副作用的破坏性语句。
2. 严禁引用 Schema 中不存在的幻觉字段或表。
3. 若用户查询模糊不明确，禁止脑补猜测，必须主动要求补充约束。`,
    candidateExamples: [
      {
        example_id: "ex_sql_1",
        inputs: {
          Query: "统计 2026 年 8 月份成交量最大的前 5 只标的",
          Schema: "trades(trade_id, symbol, volume, executed_at)",
        },
        outputs: {
          SQL: "SELECT symbol, SUM(volume) as total_vol FROM trades WHERE executed_at >= '2026-08-01' AND executed_at < '2026-09-01' GROUP BY symbol ORDER BY total_vol DESC LIMIT 5;",
          TargetTables: ["trades"],
          Explanation: "按时间区间过滤后按 symbol 聚合求和并取 Top 5",
          IsSafeReadOnly: true,
        },
        quality_score: 0.98,
        verified: true,
        source: "synthetic_gold",
      },
      {
        example_id: "ex_sql_2",
        inputs: {
          Query: "查询没有任何交易记录的账户清单",
          Schema: "accounts(account_id, name), trades(trade_id, account_id, amount)",
        },
        outputs: {
          SQL: "SELECT a.account_id, a.name FROM accounts a LEFT JOIN trades t ON a.account_id = t.account_id WHERE t.trade_id IS NULL;",
          TargetTables: ["accounts", "trades"],
          Explanation: "通过 LEFT JOIN 关联 trades 表并筛选 trade_id 为 NULL 的账户",
          IsSafeReadOnly: true,
        },
        quality_score: 0.95,
        verified: true,
        source: "synthetic_gold",
      },
    ],
  },
  {
    id: "tool-dispatch",
    name: "Agent 智能体高精工具调度决策器",
    category: "Agentic Workflow",
    description: "将用户多跳复杂工程指令编译为确定性 Tool Calling 路由与参数签名",
    signatureName: "AgentToolDispatcher",
    taskObjective: "精准研判用户真实工程意图并映射至系统已注册的特定工具集，输出参数字典",
    rawPrompt: `你是一个精密的智能体战地指挥官与工具调度总线。
输入参数:
- UserInstruction: 用户的任务指令
- ToolRegistry: 当前可用工具契约与功能列表
输出结果:
- SelectedTool: 选定的工具函数名称 (例如 run_command, replace_file_content)
- ToolArguments: 强类型调用参数字典
- Confidence: 调度置信度得分 (0.0 ~ 1.0)
- ReasoningRationale: 工具选取的第一性原理决策理由

不可变边界:
1. 严禁调度未在 ToolRegistry 中声明的虚假工具。
2. 严禁在参数中使用占位符或未解析的变量名。
3. 若无合适工具，输出 SelectedTool 为 "NONE" 并说明缺失能力。`,
    candidateExamples: [
      {
        example_id: "ex_tool_1",
        inputs: {
          UserInstruction: "排查一下当前后台运行的所有任务状态",
          ToolRegistry: "manage_task(Action: str), run_command(CommandLine: str)",
        },
        outputs: {
          SelectedTool: "manage_task",
          ToolArguments: { Action: "list" },
          Confidence: 0.99,
          ReasoningRationale: "manage_task 专用于管理和查看后台任务列表，优于裸跑 shell",
        },
        quality_score: 0.99,
        verified: true,
        source: "teacher_rollout",
      },
    ],
  },
  {
    id: "risk-audit",
    name: "量化交易风控合规熔断判官",
    category: "Quantitative Finance",
    description: "对实时下单委托请求实施强类型风控规则审计与零幻觉审批决策",
    signatureName: "TradeOrderRiskAuditor",
    taskObjective: "对进入撮合系统的交易订单做强约束合规扫描，输出放行、驳回或降额裁决",
    rawPrompt: `你是一个高频量化交易系统的一级风控判官。
输入参数:
- OrderPayload: 包含 symbol, side, qty, price, account_id 的订单请求
- PortfolioSnapshot: 当前账户持仓、净值与可用保证金
- DailyLimitRules: 当日最大回撤与单笔限额阈值
输出结果:
- Decision: 裁决结果 (APPROVED | REJECTED | THROTTLED)
- AdjustedQty: 调整后的允许申报数量
- ViolationRule: 触犯的风控规则代号 (若通过则为空)
- AuditChecksum: 审计哈希校验码

严禁放行任何超保证金限额的杠杆头寸！必须捍卫资金绝对物理安全。`,
    candidateExamples: [
      {
        example_id: "ex_risk_1",
        inputs: {
          OrderPayload: { symbol: "BTC-USDT", side: "BUY", qty: 10.0, price: 65000 },
          PortfolioSnapshot: { equity: 500000, margin_available: 400000 },
          DailyLimitRules: { max_single_order_value: 300000 },
        },
        outputs: {
          Decision: "THROTTLED",
          AdjustedQty: 4.6,
          ViolationRule: "ERR_SINGLE_ORDER_VALUE_EXCEEDED",
          AuditChecksum: "chk_9f81a20",
        },
        quality_score: 0.96,
        verified: true,
        source: "synthetic_gold",
      },
    ],
  },
];
