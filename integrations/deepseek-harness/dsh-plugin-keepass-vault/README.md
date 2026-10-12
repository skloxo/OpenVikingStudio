# dsh-plugin-keepass-vault

> KeePass Vault 独立凭据中枢与保险箱插件 (DeepSeek Harness / Cordis 规范)

## 核心设计哲学 (第一性原理)

1. **零后端依赖 (Zero Backend Dependency)**：
   本插件与 OpenViking 服务端核心无运行时强依赖，所有凭据读取在智能体本地执行。OpenViking 仅作为官方展厅展示、统一发布与版本托管下载源。
2. **凭据单一真相源 (Credential SSOT)**：
   智能体在本地读取由 KeePassXC 管理的加密数据库文件 (`.kdbx`)，彻底终结代码硬编码与向人类索要明文密码。
3. **查库第一公理**：
   任何第三方服务外呼鉴权、SSH 登录或 API Key 获取前，优先调用 `keepass_search` 与 `keepass_get`。
4. **物理快照容灾**：
   任何新增或修改条目操作前，底层强制自动创建 `*.bak` 物理快照备份。

## 客户端一键安装

在 DeepSeek Harness (DSH) 或 Cordis 环境中执行：

```bash
npm install https://vk.tide.red/studio/dsh-plugin-keepass-vault.tgz
```

## 配置项 (cordis.yml)

```yaml
plugins:
  dsh-plugin-keepass-vault:
    kdbxPath: ~/.openviking/vault.kdbx
    passwordEnv: KEEPASS_VAULT_PASSWORD
    autoSnapshot: true
```
