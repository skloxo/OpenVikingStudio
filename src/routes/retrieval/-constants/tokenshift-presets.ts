// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export interface PresetSample {
  id: string
  label: string
  language: 'python' | 'typescript' | 'json'
  code: string
}

export const TOKENSHIFT_PRESETS: PresetSample[] = [
  {
    id: 'python-service',
    label: 'Python 异步量化核心服务 (TradingEngine)',
    language: 'python',
    code: `import asyncio
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Target stock or crypto symbol")
    quantity: float = Field(gt=0, description="Order execution volume")
    order_type: str = Field(default="LIMIT", description="LIMIT or MARKET")

class TradingEngine:
    """Core institutional trading engine orchestrating high-speed execution."""

    def __init__(self, endpoint: str, timeout: float = 5.0):
        self.endpoint = endpoint
        self.timeout = timeout
        self.active_orders: Dict[str, OrderRequest] = {}

    async def submit_order(self, order: OrderRequest) -> bool:
        """Submit a single verified order to the exchange matcher."""
        if not order.symbol:
            logger.error("Empty symbol rejected")
            return False

        try:
            # Simulate low-latency handshake
            await asyncio.sleep(0.01)
            order_id = f"ord_{order.symbol}_{len(self.active_orders) + 1}"
            self.active_orders[order_id] = order
            logger.info("Order %s registered successfully", order_id)
            return True
        except Exception as exc:
            logger.exception("Failed to dispatch order: %s", exc)
            return False

    async def cancel_all(self) -> int:
        """Emergency circuit breaker cancelling all active orders."""
        cancelled = 0
        for oid in list(self.active_orders.keys()):
            try:
                del self.active_orders[oid]
                cancelled += 1
            except KeyError:
                continue
        return cancelled
`,
  },
  {
    id: 'ts-component',
    label: 'TypeScript 状态管理与 API 客户端 (UserSession)',
    language: 'typescript',
    code: `import { create } from 'zustand';

export interface UserSession {
  userId: string;
  accountRole: 'admin' | 'operator' | 'viewer';
  authToken: string;
  expiresAt: number;
}

export interface SessionState {
  currentSession: UserSession | null;
  isLoading: boolean;
  login: (credentials: { username: string; token: string }) => Promise<void>;
  logout: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  currentSession: null,
  isLoading: false,
  login: async ({ username, token }) => {
    set({ isLoading: true });
    try {
      const resp = await fetch('/api/v1/auth/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, token }),
      });
      if (!resp.ok) {
        throw new Error('Authentication rejected');
      }
      const data: UserSession = await resp.json();
      set({ currentSession: data, isLoading: false });
    } catch (err) {
      set({ currentSession: null, isLoading: false });
      throw err;
    }
  },
  logout: () => set({ currentSession: null }),
}));
`,
  },
  {
    id: 'json-config',
    label: 'JSON 集群节点编排契约 (FleetConfig)',
    language: 'json',
    code: `{
  "cluster_id": "viking-fleet-prod-01",
  "version": "1.5.73",
  "nodes": [
    {
      "node_id": "mac-studio-m3",
      "ip": "127.0.0.1",
      "port": 13100,
      "ram_gb": 256,
      "role": "inference_accelerator",
      "active_models": ["ornith-35b-moe", "qwen3.8-27b-vl"]
    },
    {
      "node_id": "rtx-2080ti-local",
      "ip": "127.0.0.1",
      "port": 11432,
      "vram_gb": 22,
      "role": "embedding_and_rerank",
      "active_models": ["wemm-embed-9b", "qwen3-vl-reranker"]
    }
  ],
  "anti_entropy_threshold": 0.88,
  "dreaming_enabled": true
}
`,
  },
]
