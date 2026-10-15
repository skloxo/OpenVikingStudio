# dsh-plugin-keepass-vault

> KeePass Vault 本地私有化凭据插件 (DeepSeek Harness / Cordis 规范)

## 核心设计哲学 (第一性原理)

1. **本地私有凭据与零云端依赖 (Local Private Vault & Zero Cloud Custody)**：
   本插件定位为纯本地私有化插件。OpenViking (VK) 仅作为官方展厅展示曝光与不可变安装包托管下载源，**绝不从云端集中存储或远程下发密码保险库**！智能体在本地直接挂载由 KeePassXC 管理的加密数据库文件 (`.kdbx`)。
2. **凭据单一真相源 (Credential SSOT)**：
   智能体在本地读取由用户本地安全保存的 `.kdbx` 数据库，彻底终结代码硬编码与向人类索要明文密码。
3. **查库第一公理**：
   任何第三方服务外呼鉴权、SSH 登录或 API Key 获取前，强制优先调用 `keepass_search` 与 `keepass_get` 检索本地库。
4. **物理快照容灾**：
   任何新增或修改条目操作前，底层强制自动创建 `*.bak` 本地物理快照备份。

## 客户端一键安装

在 DeepSeek Harness (DSH) 或 Cordis 环境中执行：

```bash
npm install https://vk.tide.red/studio/dsh-plugin-keepass-vault.tgz
```

## 配置项 (cordis.yml)

> ⚠️ **重要**：`kdbxPath` 必须修改为您本机实际存放 `.kdbx` 文件的绝对路径！

```yaml
plugins:
  dsh-plugin-keepass-vault:
    # 填入您本机本地的 KeePass .kdbx 数据库绝对路径 (切勿假设云端下发)
    # Linux/Mac 例如: ~/.openviking/vault.kdbx
    # Windows 例如: C:/Users/YourName/.openviking/vault.kdbx
    kdbxPath: ~/.openviking/vault.kdbx
    # 主密码所在的环境变量名 (推荐在系统或 shell 环境变量中配置)
    passwordEnv: KEEPASS_VAULT_PASSWORD
    autoSnapshot: true
```
