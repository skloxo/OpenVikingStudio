// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export interface ContextRouterPreset {
  id: string
  name: string
  category: string
  description: string
  content: string
}

export const CONTEXT_ROUTER_PRESETS: ContextRouterPreset[] = [
  {
    id: 'quant_trading',
    name: '智能量化交易多智能体决策 Prompt',
    category: '量化金融 / Python 核心',
    description: '包含交易身份前缀、深度市场分析研判、Python 风控引擎代码及 YAML 仓位管理技能规约',
    content: `<identity>
You are an expert AI trading strategist operating on OpenViking infrastructure.
Strictly adhere to the maximum drawdown limit and position sizing invariant.
Never approve naked short transactions without collateral verification.
</identity>

# 市场深度流动性研判
近期宏观经济数据发布后，顶级加密永续合约市场呈现高频流动性分层特征。
主要做市商在现货与衍生品间实施跨期统计套利，导致盘口微观价差在非农数据窗口出现脉冲式扩张。
对于高频订单薄，智能体必须避免在价差突变超过基线 3 倍时连续下达限价撮合单，以防止滑点损失侵蚀 alpha 收益。

\`\`\`python
import math
import time
from typing import Dict, List, Optional

class RiskEngine:
    """Enterprise risk control barrier for algorithmic order execution."""

    def __init__(self, max_drawdown: float = 0.05, max_leverage: float = 3.0):
        self.max_drawdown = max_drawdown
        self.max_leverage = max_leverage
        self.positions: Dict[str, float] = {}
        self.peak_equity: float = 100000.0

    def check_spread_invariants(self, bid: float, ask: float) -> bool:
        if bid <= 0.0 or ask <= 0.0:
            return False
        spread_ratio = (ask - bid) / bid
        if spread_ratio > 0.0035:
            return False
        return True

    def calculate_kelly_fraction(self, win_rate: float, reward_risk: float) -> float:
        if reward_risk <= 0.0:
            return 0.0
        kelly = (win_rate * (reward_risk + 1.0) - 1.0) / reward_risk
        return max(0.0, min(kelly * 0.5, 0.25))
\`\`\`

---
name: position_sizing
description: Dynamic volatility-based position sizing skill.
---
# Rules
1. Calculate ATR for 14 periods on 15m candle stream.
2. Limit risk per trade to 1% of total portfolio equity.
3. Automatically halt execution if drawdown exceeds max_drawdown limit.
`,
  },
  {
    id: 'fullstack_api',
    name: '全栈工程脚手架与 API 客户端 Prompt',
    category: '全栈开发 / TypeScript',
    description: '包含前端工程系统角色、REST API 架构设计说明、TypeScript 客户端类与部署规范',
    content: `SYSTEM: You are the Antigravity Fullstack Lead Engineer.
Strictly enforce TypeScript strict-mode, zero-any typing, and cockpit density standards.

# 核心架构与端点流转说明
全系统客户端收口于单一持久连接池，所有网络请求必须携带调用方身份凭证与租户鉴权头。
遇到网络异常或服务端 503 拥塞时，客户端必须通过带抖动的指数退避算法进行自愈重试，同时避免在热循环中阻塞主线程渲染。

\`\`\`typescript
import { useState, useEffect } from 'react'

export interface ClusterNode {
  id: string
  hostname: string
  ip: string
  status: 'active' | 'degraded' | 'offline'
  vram_allocated_gb: number
}

export class ClusterManagerClient {
  private endpoint: string

  constructor(endpoint: string = 'http://127.0.0.1:1933') {
    this.endpoint = endpoint
  }

  async fetchActiveNodes(): Promise<ClusterNode[]> {
    const res = await fetch(\`\${this.endpoint}/api/v1/fleet/nodes\`, {
      headers: { 'Content-Type': 'application/json' },
    })
    if (!res.ok) {
      throw new Error(\`Failed to fetch nodes: \${res.statusText}\`)
    }
    return res.json()
  }
}
\`\`\`

# 部署与交付门禁
1. 运行 \`npm run build\` 确保 Vite 生产包 0 报错通过；
2. 执行 \`security_check.py\` 确认 0 密钥泄露；
3. 挂载浏览器走查人工核验清单。
`,
  },
  {
    id: 'cluster_fleet_ops',
    name: '全集群多节点故障自愈运维 Prompt',
    category: '集群运维 / Shell & JSON',
    description: '包含运维调度身份、节点网络中断复盘分析、Shell 自愈脚本与节点配置 JSON',
    content: `<identity>
You are the Viking Cluster Operations Controller.
Maintain continuous health monitoring across all satellite nodes (2080Ti, 3070, Mac Studio).
</identity>

# 故障诊断与网络抖动分析
监测到 3070 节点在进行长文本向量化时发生 TCP 连接偶发重置。
FRP 穿透隧道心跳偶发丢包导致管理进程暂时脱离集群协调者。
我们通过执行轻量检测脚本重置 FRP 会话并重新校验端口连通性。

\`\`\`shell
#!/usr/bin/env bash
set -euo pipefail

TARGET_NODE="3070"
PORT=13389

echo "[$(date)] Checking FRP tunnel connection to node $TARGET_NODE..."
if nc -z -w 3 127.0.0.1 "$PORT"; then
    echo "[OK] Tunnel is healthy on port $PORT."
else
    echo "[WARN] Tunnel down, restarting satellite service..."
    systemctl --user restart openviking-satellite.service
fi
\`\`\`

\`\`\`json
{
  "node_id": "rtx3070_satellite",
  "role": "inference_worker",
  "frp_remote_port": 13389,
  "heartbeat_interval_sec": 5,
  "active_models": ["Qwen3-VL-Reranker-2B", "WeMM-Embedding-9B"]
}
\`\`\`
`,
  },
]
