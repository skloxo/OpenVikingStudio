# 智能体自适应熔断断路器 (Agent Adaptive Circuit Breaker)

[![Version](https://img.shields.io/badge/version-1.3.0-cyan.svg)](https://vk.tide.red)
[![Platform](https://img.shields.io/badge/platform-Google%20Antigravity-blue.svg)](https://antigravity.google)
[![Architecture](https://img.shields.io/badge/architecture-Fail--Open%20%26%20Zero--Touch-green.svg)](https://vk.tide.red)

专为 **Google Antigravity IDE / Desktop** 深度定制的物理级断路器插件，通过原生 Hook 神经反射层守护智能体自治链路，彻底终结死循环打补丁、Token 烧尽与失控自嗨。

---

## 🌟 核心特性 (v1.3.0)

1. **自适应弹性预算体系**：
   - **健康常态 (36 步)**：连续 0 报错全绿灯时，授予 36 步充裕预算，支持长线重构与端到端交付；
   - **警戒收敛 (15 步)**：一旦出现写工具或执行报错，立即收窄至 15 步，逼退盲目打补丁；
   - **自适应增量租约 (+15 步)**：人类点击“允许”放行后，系统自动授予增量租约，消除连环夺命弹窗；
   - **收尾归档自动豁免**：对 `REFACTORING_PLAN.md` 等总结归档操作豁免步数护栏，确保交付一气呵成。
2. **`force_ask` 零误杀机制**：
   - 告别粗暴断连 `deny`，通过官方授权弹窗交还控制权，让人类与智能体无缝协作。
3. **只读探针零损耗放行**：
   - 自动穿透 OpenViking、KeePass、view_file、grep 等只读查询工具，不计入报错计数。
4. **工业级 Fail-Open 架构**：
   - 脚本内部全生命周期 `BaseException` 兜底，绝不因护栏故障拖垮 IDE 正常工具流。
5. **Windows 原生高可用防护**：
   - 启用 Python `-E -s -S` 隔离参数，冷启动由 3300ms 骤降至 40ms（提速 80 倍）；
   - stderr 物理静音与 UTF-8 纯净流，彻底杜绝 GBK 字符投毒导致的 IDE 会话白屏。

---

## 🚀 极速开箱安装 (One-Line Quickstart)

### 方式一：Windows PowerShell (一键全自动开箱)
```powershell
powershell -ExecutionPolicy Bypass -Command "iwr -Uri 'https://vk.tide.red/studio/agent-circuit-breaker.tgz' -OutFile '$env:TEMP\acb.tgz'; New-Item -ItemType Directory -Force -Path \"$env:USERPROFILE\.gemini\config\plugins\agent-circuit-breaker\" | Out-Null; tar -xzf '$env:TEMP\acb.tgz' -C \"$env:USERPROFILE\.gemini\config\plugins\agent-circuit-breaker\"; python \"$env:USERPROFILE\.gemini\config\plugins\agent-circuit-breaker\setup.py\" install"
```

### 方式二：Linux / macOS (一键全自动开箱)
```bash
curl -fsSL https://vk.tide.red/studio/agent-circuit-breaker.tgz -o /tmp/acb.tgz && \
mkdir -p ~/.gemini/config/plugins/agent-circuit-breaker && \
tar -xzf /tmp/acb.tgz -C ~/.gemini/config/plugins/agent-circuit-breaker && \
python3 ~/.gemini/config/plugins/agent-circuit-breaker/setup.py install
```

---

## 🛠️ 本地开发与手动安装
若已拉取本源码目录：
```bash
# 进入目录
cd integrations/antigravity/agent-circuit-breaker

# 一键安装挂载至当前机器的 Antigravity
python setup.py install

# 查看测试放行状态
python scripts/circuit_guard.py pre-tool
# 应输出: {"decision": "allow"}
```

---

## 🗺️ 多智能体生态演进展望
- 当前版本（v1.3.0）针对 **Google Antigravity** 进行了原生内核与 Hook 规范深度调优；
- 后续将依托 OpenViking 统一架构，横向拓展支持 **DeepSeek Harness (DSH)** 与 **Claude Code** 代理生态。
