---
name: keepass-vault
description: KeePass 本地密码保险库凭据管理与自动化中枢专用技能。涵盖查库第一公理、免明文索取、写前快照容灾、高熵密码入库与条目全生命周期管理。
---

# 🔐 KeePass Vault 凭据中枢工程规范与操作指南

## 一、核心物理契约与第一性原理

1. **查库第一公理 (Lookup First Axiom)**：
   - 凡涉及 API Key、服务器 SSH 密码/密钥、数据库连接串、第三方凭据时，**严禁向用户直接索要明文**；
   - 必须优先调用 `keepass_search` 搜索本地保险库。

2. **灾难恢复优先 (Disaster Recovery First)**：
   - 任何针对密码库的写入操作（`keepass_add`, `keepass_edit`, `keepass_rm`），系统必须在写入前自动在同级目录生成物理安全备份（如 `Key.kdbx.YYYYMMDD_HHMMSS.bak`）；
   - 保留最近 10 个滚动备份，防范物理写坏。

3. **免明文与高密保护 (Zero-Plaintext Defense)**：
   - 读取凭据时，默认仅查看非敏感元数据（`title`, `username`, `url`）；
   - 仅在确需注入运行时连接时声明 `show_protected=True`，并在交互输出中对密码进行星号或脱水脱敏。

---

## 二、标准工具调用矩阵 (9 Tools)

| 阶段 | 工具名称 | 核心用途与参数 |
| :--- | :--- | :--- |
| **状态巡检** | `keepass_status` | 检查本地数据库路径、连通性及主密钥配置状态 |
| **检索查询** | `keepass_search` | `query`: 模糊或精确搜索条目，获取 entry_path |
| **凭据读取** | `keepass_get` | `entry_path`: 读取条目属性；`show_protected=True` 读取密码 |
| **安全写入** | `keepass_add` | `entry_path`, `username`, `password`, `url`, `notes` |
| **凭据更新** | `keepass_edit` | `entry_path`, 更新指定字段，自动写前备份 |
| **安全删除** | `keepass_rm` | `entry_path`, 物理删除条目，强制写前备份 |
| **分组遍历** | `keepass_list_tree` | `group="/"`, `recursive=True` 遍历分组结构 |
| **安全体检** | `keepass_analyze` | 审计弱密码、重复口令与密码过期状态 |
| **附件导出** | `keepass_export_attachment` | 导出 SSH 私钥、PEM 证书或配置文件至本地隔离目录 |

---

## 三、配置与自愈规程

插件配置统一由私有 `config.json` 托管：
- `kdbx_path`: 本地数据库文件绝对路径（如 `C:/Users/Skl/Desktop/Key.kdbx`）；
- `password_env`: 密码环境变量名称（默认 `KPXC_MASTER_KEY`）；
- `master_key`: 可选直接配置访问密钥。
