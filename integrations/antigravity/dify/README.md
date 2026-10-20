# Dify 工作流编排集成插件 (dify)

[![Version](https://img.shields.io/badge/version-1.0.1-cyan.svg)](https://vk.tide.red)
[![Platform](https://img.shields.io/badge/platform-Google%20Antigravity-blue.svg)](https://antigravity.google)

专为 **OpenViking** 打造的 Dify 平台工作流与知识库无缝对接插件。支持智能体快速调用 Dify 编排好的业务 Pipeline 与特定知识库检索。

---

## 🌟 核心特性 (v1.0.1)

1. **工作流触发调度**：
   - 支持异步或同步触发 Dify 工作流任务；
2. **知识库混合召回**：
   - 跨 Dify 与 OpenViking 知识库联合检索；
3. **会话流式交互**：
   - 适配 SSE 流式输出与会话状态管理。

---

## 🚀 极速开箱安装 (One-Line Quickstart)

### 方式一：Windows PowerShell (一键全自动开箱)
```powershell
powershell -ExecutionPolicy Bypass -Command "iwr -Uri 'https://vk.tide.red/studio/dify.tgz' -OutFile '$env:TEMP\dify.tgz'; New-Item -ItemType Directory -Force -Path \"$env:USERPROFILE\.gemini\config\plugins\dify\" | Out-Null; tar -xzf '$env:TEMP\dify.tgz' -C \"$env:USERPROFILE\.gemini\config\plugins\dify\"; python \"$env:USERPROFILE\.gemini\config\plugins\dify\setup.py\" install"
```

### 方式二：Linux / macOS (一键全自动开箱)
```bash
curl -fsSL https://vk.tide.red/studio/dify.tgz -o /tmp/dify.tgz && \
mkdir -p ~/.gemini/config/plugins/dify && \
tar -xzf /tmp/dify.tgz -C ~/.gemini/config/plugins/dify && \
python3 ~/.gemini/config/plugins/dify/setup.py install
```
