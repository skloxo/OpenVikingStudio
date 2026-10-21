# OpenViking 核心长程记忆与代码战地插件 (openviking-memory)

专为 **Google Antigravity IDE / Desktop** 打造的一等公民原生体外大脑插件。将跨会话语义记忆检索、代码 AST 符号感知、工作区拓扑、会话结晶归档与经验反思完全内聚，彻底替代传统的外部散装配置。

---

## 🌟 核心特性

1. **体外大脑全息记忆中枢**：
   - 跨会话统一持久化存储与双向图谱关联，智能体长线重构与多轮对话记忆永不丢失；
   - 预设 `PreInvocation` 先验自动召回预取，零额外 Token 损耗注入上下文。
2. **三十六项战地核心武器库**：
   - **长程记忆**：`find`, `search`, `read`, `write`, `store`, `link`, `get_relations`, `unlink`；
   - **代码与工作区 AST**：`ls`, `tree`, `grep`, `glob`, `code_outline`, `code_search`, `code_expand`, `diff`, `smart_read`, `tag`；
   - **技能中枢联动**：`skills`, `audit_skills`, `auto_onboard_skills`, `get_onboard_queue_status`, `fix_skill`, `record_evolution_lesson`；
   - **多会话协同**：`list_sessions`, `get_session`, `create_session`；
   - **运行态传感与遥测**：`health`, `system_status`, `privacy`, `consistency`, `ping`, `harness_stats`, `usage_stats`, `observer`, `metrics`。
3. **会话无缝交接 (Handover)**：
   - 内置标准化三阶交接规约，一键输出供新会话秒级启动的接力提示词。

---

## 🚀 极速开箱安装 (One-Line Quickstart)

### 方式一：Windows PowerShell (一键全自动开箱)
```powershell
powershell -ExecutionPolicy Bypass -Command "iwr -Uri 'https://vk.tide.red/studio/openviking-memory.tgz' -OutFile '$env:TEMP\ov-mem.tgz'; New-Item -ItemType Directory -Force -Path \"$env:USERPROFILE\.gemini\config\plugins\openviking-memory\" | Out-Null; tar -xzf '$env:TEMP\ov-mem.tgz' -C \"$env:USERPROFILE\.gemini\config\plugins\openviking-memory\"; python \"$env:USERPROFILE\.gemini\config\plugins\openviking-memory\setup.py\" --install"
```

### 方式二：Linux / WSL2 (一键全自动开箱)
```bash
curl -fsSL https://vk.tide.red/studio/openviking-memory.tgz -o /tmp/ov-mem.tgz && \
mkdir -p ~/.gemini/config/plugins/openviking-memory && \
tar -xzf /tmp/ov-mem.tgz -C ~/.gemini/config/plugins/openviking-memory && \
python3 ~/.gemini/config/plugins/openviking-memory/setup.py --install
```

> **其他客户端生态适配说明**：
> 若在 **DeepSeek Harness (Cordis)** 客户端中使用，请由 DSH 插件市场安装对应桥接包 `dsh-plugin-openviking-memory`。


---

## 🛠️ 本地开发与手动挂载

若已拉取本源码仓库：
```bash
# 进入目录
cd integrations/antigravity/openviking-memory

# 自动自举安装至当前宿主 Antigravity
python setup.py --install
```
向导将自动完成端侧健康巡检、验证用户身份并生成只读受控凭据 `config.json`（权限 0600）。无需重启 IDE，智能体即刻获得全量核心记忆能力！
