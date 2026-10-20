# OpenViking 集群同频治理插件 (fleet-mesh)

[![Version](https://img.shields.io/badge/version-1.0.2-cyan.svg)](https://vk.tide.red)
[![Platform](https://img.shields.io/badge/platform-Google%20Antigravity-blue.svg)](https://antigravity.google)

专为 **OpenViking 多节点算力集群** 打造的集群同频与拓扑治理插件。面向卫星工位机与算力中枢，提供节点巡检、配置同频与跨机同步运维能力。

---

## 🌟 核心特性 (v1.0.2)

1. **卫星拓扑巡检**：
   - 跨节点网络延迟与健康状态探针探测；
2. **集群一键同频**：
   - 配置快照同步与版本基线一致性保障；
3. **安全穿透互联**：
   - 内网穿透与安全白名单拓扑管理。

---

## 🚀 极速开箱安装 (One-Line Quickstart)

### 方式一：Windows PowerShell (一键全自动开箱)
```powershell
powershell -ExecutionPolicy Bypass -Command "iwr -Uri 'https://vk.tide.red/studio/fleet-mesh.tgz' -OutFile '$env:TEMP\fleet.tgz'; New-Item -ItemType Directory -Force -Path \"$env:USERPROFILE\.gemini\config\plugins\fleet-mesh\" | Out-Null; tar -xzf '$env:TEMP\fleet.tgz' -C \"$env:USERPROFILE\.gemini\config\plugins\fleet-mesh\"; python \"$env:USERPROFILE\.gemini\config\plugins\fleet-mesh\setup.py\" install"
```

### 方式二：Linux / WSL2 (一键全自动开箱)
```bash
curl -fsSL https://vk.tide.red/studio/fleet-mesh.tgz -o /tmp/fleet.tgz && \
mkdir -p ~/.gemini/config/plugins/fleet-mesh && \
tar -xzf /tmp/fleet.tgz -C ~/.gemini/config/plugins/fleet-mesh && \
python3 ~/.gemini/config/plugins/fleet-mesh/setup.py install
```
