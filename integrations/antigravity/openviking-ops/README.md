# OpenViking 系统运维治理插件 (openviking-ops)

专为 **OpenViking (VK) 体外大脑** 打造的系统级运维治理与管控特权插件。面向后台运维智能体、哨兵巡检引擎与系统管理员，提供 16 项高特权物理算子与双 Hook 神经反射守卫。

---

## 🌟 核心特性

1. **三位一体运维特权架构**：
   - **MCP 特权工具层**：直连服务端核心接口，提供数据索引重建、底层文件/目录移动、死信队列自愈、记忆纯度审计与服务启停重载；
   - **Hook 物理安全守卫**：包含 `SessionStart` 巡检心跳与 `PreToolUse` 破坏性操作安全审计，防止误停机；
   - **专家认知导轨**：内嵌系统运维 SOP 与安全护栏，先查后动、原子提交版本快照。
2. **十六项高特权物理算子**：
   - **资源与索引**：`add_resource`, `list_resources`, `delete_resource`, `reindex`, `commit`；
   - **文件与拓扑**：`mv`, `rename`, `webdav_info`；
   - **质量与自愈**：`memory_purity_report`, `retry_dead_letter`；
   - **监听与生命周期**：`list_watches`, `cancel_watch`, `manage_watch`, `server_control`, `server_init`, `server_doctor`。
3. **零信任单轨鉴权**：
   - 严格要求管理员 Bearer 凭据，物理封杀本地未授权访问与虚假测试。

---

## 🚀 极速开箱安装 (One-Line Quickstart)

### 方式一：Windows PowerShell (一键全自动开箱)
```powershell
powershell -ExecutionPolicy Bypass -Command "iwr -Uri 'https://vk.tide.red/studio/openviking-ops.tgz' -OutFile '$env:TEMP\ov-ops.tgz'; New-Item -ItemType Directory -Force -Path \"$env:USERPROFILE\.gemini\config\plugins\openviking-ops\" | Out-Null; tar -xzf '$env:TEMP\ov-ops.tgz' -C \"$env:USERPROFILE\.gemini\config\plugins\openviking-ops\"; python \"$env:USERPROFILE\.gemini\config\plugins\openviking-ops\setup.py\" --install"
```

### 方式二：Linux / WSL2 (一键全自动开箱)
```bash
curl -fsSL https://vk.tide.red/studio/openviking-ops.tgz -o /tmp/ov-ops.tgz && \
mkdir -p ~/.gemini/config/plugins/openviking-ops && \
tar -xzf /tmp/ov-ops.tgz -C ~/.gemini/config/plugins/openviking-ops && \
python3 ~/.gemini/config/plugins/openviking-ops/setup.py --install
```

> **其他客户端生态适配说明**：
> 若在 **DeepSeek Harness (Cordis)** 客户端中使用，请由 DSH 插件市场安装对应桥接包 `dsh-plugin-openviking-ops`。


---

## 🛠️ 本地开发与手动挂载

若已拉取本源码仓库：
```bash
# 进入目录
cd integrations/antigravity/openviking-ops

# 自动自举安装至当前宿主 Antigravity
python setup.py --install
```
自举向导将自动继承当前环境的已认证凭据，并动态绑定自内聚 `server.py` 服务驱动。
