# OpenViking 集群同频治理插件 (fleet-mesh)

专为 **OpenViking 多节点算力集群** 打造的独立自内聚集群巡检与拓扑同频插件。面向卫星工位机（如 RTX 3070 / MacBook）与算力中枢（2080Ti / 云端网关），提供节点连通巡检、版本漂移侦测与动态身份对齐能力。

---

## 核心特性

1. **多节点网络自适应 (`127.0.0.1:1933` ➔ `https://vk.tide.red`)**：
   - 优先探测本机环回中枢健康度，离线时自动切换至环境变量或 `https://vk.tide.red`；
   - 自动依据宿主主机名推导 `antigravity@{hostname}` 节点标识，消除跨机身份碰撞。
2. **纯自内聚 Stdio 驱动 (`server.py`)**：
   - 零外部工作区桌面路径硬编码，精准托管 `openviking_fleet_check` 与 `openviking_fleet_sync` 两项工具；
   - 自动清洗全局 `mcp_config.json` 中历史残留的 `fleet` / `openviking-fleet` 幽灵别名。
3. **对称生命周期管理**：
   - 支持 `--install`、`--inspect` 巡检与 `--uninstall` 清理卸载，凭证文件以 `0600` 权限独立落盘。

---

## 快速安装

### Windows PowerShell
```powershell
powershell -ExecutionPolicy Bypass -Command "iwr -Uri 'https://vk.tide.red/studio/fleet-mesh.tgz' -OutFile '$env:TEMP\fleet.tgz'; New-Item -ItemType Directory -Force -Path \"$env:USERPROFILE\.gemini\config\plugins\fleet-mesh\" | Out-Null; tar -xzf '$env:TEMP\fleet.tgz' -C \"$env:USERPROFILE\.gemini\config\plugins\fleet-mesh\"; python \"$env:USERPROFILE\.gemini\config\plugins\fleet-mesh\setup.py\" --install"
```

### Linux / WSL2
```bash
curl -fsSL https://vk.tide.red/studio/fleet-mesh.tgz -o /tmp/fleet.tgz && \
mkdir -p ~/.gemini/config/plugins/fleet-mesh && \
tar -xzf /tmp/fleet.tgz -C ~/.gemini/config/plugins/fleet-mesh && \
python3 ~/.gemini/config/plugins/fleet-mesh/setup.py --install
```
