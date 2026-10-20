# KeePass 凭据中枢物理守卫插件 (keepass-vault)

[![Version](https://img.shields.io/badge/version-1.2.1-cyan.svg)](https://vk.tide.red)
[![Platform](https://img.shields.io/badge/platform-Google%20Antigravity-blue.svg)](https://antigravity.google)
[![Security](https://img.shields.io/badge/security-Encrypted%20KDBX-cyan.svg)](https://vk.tide.red)

专为 **Google Antigravity IDE / Desktop** 与 OpenViking 生态打造的凭据保险库插件。落实查库第一公理，免除明文索取，高熵写盘，保障全集群凭据唯一真相源 (Credential SSOT)。

---

## 🌟 核心特性 (v1.2.1)

1. **查库第一公理 (Credential SSOT)**：
   - 全集群密码、SSH 私钥与 API Key 的唯一真实源，杜绝硬编码与明文传输；
2. **免明文索取与高熵生成**：
   - 自动生成符合强密码策略的高熵凭据，自动加密落盘；
3. **写前快照与容灾备份**：
   - 任何修改操作前自动创建时间戳快照，保障数据零丢失；
4. **九项核心 MCP 凭据原子算子**：
   - `keepass_status`, `keepass_search`, `keepass_get`, `keepass_add`, `keepass_update`, `keepass_generate_password`, `keepass_list_groups`, `keepass_verify_master_key`, `keepass_export_public_fingerprint`。

---

## 🚀 极速开箱安装 (One-Line Quickstart)

### 方式一：Windows PowerShell (一键全自动开箱)
```powershell
powershell -ExecutionPolicy Bypass -Command "iwr -Uri 'https://vk.tide.red/studio/keepass-vault.tgz' -OutFile '$env:TEMP\kpv.tgz'; New-Item -ItemType Directory -Force -Path \"$env:USERPROFILE\.gemini\config\plugins\keepass-vault\" | Out-Null; tar -xzf '$env:TEMP\kpv.tgz' -C \"$env:USERPROFILE\.gemini\config\plugins\keepass-vault\"; python \"$env:USERPROFILE\.gemini\config\plugins\keepass-vault\setup.py\" install"
```

### 方式二：Linux / macOS (一键全自动开箱)
```bash
curl -fsSL https://vk.tide.red/studio/keepass-vault.tgz -o /tmp/kpv.tgz && \
mkdir -p ~/.gemini/config/plugins/keepass-vault && \
tar -xzf /tmp/kpv.tgz -C ~/.gemini/config/plugins/keepass-vault && \
python3 ~/.gemini/config/plugins/keepass-vault/setup.py install
```

---

## 🛠️ 本地开发与手动挂载

若已拉取本源码目录：
```bash
# 进入目录
cd integrations/antigravity/keepass-vault

# 一键安装挂载至当前机器的 Antigravity
python setup.py install
```
