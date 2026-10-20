# OpenViking 核心记忆反重力官方标准插件 (openviking-memory)

> **版本**：`v2.0.16`  
> **适用宿主**：Google Antigravity IDE (VS Code / Theia Agent 运行时)  
> **开源协议**：AGPL-3.0

---

## 📖 插件概述

`openviking-memory` 是 OpenViking 体外大脑专为 **Antigravity IDE** 打造的一等公民原生插件。它将语义向量记忆检索、执行意图先验注入、会话结晶与交接、以及经验教训持久化完全内聚，彻底替代了传统的外部散装配置。

---

## ⚡ 10 秒开箱即用安装步骤

### 1. 挂载/复制插件至 Antigravity 插件目录
```bash
# 方式 A：软链接（推荐开发调试）
ln -s /path/to/OpenVikingStudio/integrations/antigravity/openviking-memory ~/.gemini/config/plugins/openviking-memory

# 方式 B：直接复制
cp -r /path/to/OpenVikingStudio/integrations/antigravity/openviking-memory ~/.gemini/config/plugins/
```

### 2. 执行快速配置脚本
```bash
cd ~/.gemini/config/plugins/openviking-memory

# 支持命令行参数一步到位：
python3 setup.py --api http://127.0.0.1:1933 --key <你的专属API_KEY>

# 或直接交互式运行（根据终端提示输入）：
python3 setup.py
```

执行完毕后，脚本会自动完成网络探针验真、验证用户身份并生成只读受控凭据 `config.json`（权限 0600）。
**无需重启 IDE，智能体即刻获得全量核心记忆能力！**

---

## 🧩 插件内聚能力矩阵

| 组成部分 | 作用与功能 |
| :--- | :--- |
| **`plugin.json`** | 反重力官方插件清单，声明版本号 `2.0.16`、图标、作者及建议提示词 |
| **`hooks.json`** | 声明式 Hook：在推理前自动注入先验记忆，在会话结束时轻量心跳归档 |
| **`skills/openviking-memory`** | 核心记忆生命周期技能：指导智能体按需召回、阅读切片与写回事实 |
| **`skills/session-handover`** | 会话脱水结晶技能：三阶交接 SOP，生成供新会话秒级启动的 Handover Prompt |
| **`rules/memory-ssot.md`** | 记忆隔离准则：区分空间公共层与专属私有层，严格遵守凭据零泄密 |
