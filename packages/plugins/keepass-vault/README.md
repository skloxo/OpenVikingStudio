# KeePass 凭据中枢物理守卫插件 (keepass-vault)

[![Version](https://img.shields.io/badge/version-1.2.6-cyan.svg)](https://vk.tide.red)
[![Platform](https://img.shields.io/badge/platform-Google%20Antigravity-blue.svg)](https://antigravity.google)
[![Security](https://img.shields.io/badge/security-Encrypted%20KDBX-cyan.svg)](https://vk.tide.red)

专为 **Google Antigravity IDE / Desktop** 与全集群智能体打造的本地凭据保险库插件。落实查库第一公理，免除明文索取，高熵写盘，保障全集群凭据唯一真相源 (Credential SSOT)。

---

## 🌟 核心特性 (v1.2.6)

1. **查库第一公理 (Credential SSOT)**：
   - 全集群密码、SSH 私钥与 API Key 的唯一真实源，坚决杜绝硬编码与明文传输；
2. **免明文索取与高熵生成**：
   - 读取密码支持脱敏查看；新增凭据时强制自动生成 $\ge 16$ 位高熵密码；
3. **写前防抖物理快照 (Disaster Recovery First)**：
   - 任何修改操作（add/edit/rm）前由 Hook 与底层自动创建 `*.bak` 时间戳快照，保障数据零丢失；
4. **九项核心 MCP 凭据原子算子**：
   - `keepass_status`: 数据库连通性、主密钥及解锁状态体检；
   - `keepass_search`: 模糊与关键词检索匹配条目路径；
   - `keepass_get`: 安全提取用户名、密码（受保护）、URL 与 TOTP；
   - `keepass_add`: 新增凭据条目（递归创建分组，高熵随机口令）；
   - `keepass_edit`: 更新现有条目元数据或密码；
   - `keepass_rm`: 安全删除或归档条目；
   - `keepass_list_tree`: 树状或扁平列出指定分组结构；
   - `keepass_analyze`: 数据库安全性体检（弱口令与重复密码审计）；
   - `keepass_export_attachment`: 提取 SSH 私钥、证书或配置文件。

---

## 🚀 极速开箱使用 (Agent Natural Language First)

直接在 Antigravity 对话框中发送一句话，由 Agent 自动全权托管安装与测试：
> *“帮我配置好 KeePass 插件，数据库在桌面 Key.kdbx，密码是 `xxxxxx`。”*

---

## 🛠️ 本地命令行向导 (setup.py)

```powershell
# 1. 带参一键静默安装并配置
python setup.py --install --kdbx "~/Desktop/Key.kdbx" --key "你的密码"

# 2. 真实物理健康度体检
python setup.py --inspect

# 3. 卸载与清理注册表
python setup.py --uninstall
```
