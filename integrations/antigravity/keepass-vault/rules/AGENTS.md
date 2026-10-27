# 🔐 KeePass 凭据保险箱法则契约 (Credential SSOT Contract)

本契约是全集群智能体涉及账号、密码、密钥与凭据操作的最高物理法则。

---

## 一、 查库第一公理 (Lookup First Axiom)
1. **免明文索取**：凡遇到 API Key、服务器 SSH 密码/私钥、数据库连接串或第三方凭据时，**绝对禁止向人类直接索要明文**；
2. **第一反射**：开局必须优先调用 `keepass_search` 搜索本地 KeePass 保险库；
3. **查无此人方可求证**：仅在 `keepass_search` 确认返回 `count: 0` 时，方可向人类汇报未找到该凭据并请求授权新建或输入。

---

## 二、 灾难恢复优先与写前快照契约 (Disaster Recovery First)
1. **写前物理快照**：针对密码库的任何写操作（`keepass_add`, `keepass_edit`, `keepass_rm`），系统由底层与 Hook 自动在写入前创建时间戳安全快照 (`Key.kdbx.YYYYMMDD_HHMMSS.bak`)；
2. **滚动保留 10 份**：物理保证数据库零损坏、秒级可还原；
3. **破坏性操作警惕**：`keepass_rm` 属于高危破坏性操作，执行前必须确认条目无其他依赖。

---

## 三、 免明文透传与高熵写盘契约 (Zero-Plaintext Defense)
1. **最小特权读取**：读取条目时，若仅需确认存在性，默认仅查看非敏感元数据 (`title`, `username`, `url`)；
2. **输出脱水脱敏**：对话与日志中输出凭据时，必须进行掩码脱敏（如 `sk-ant-***` 或 `[PROTECTED_PASSWORD]`），严禁在对话气泡中大段贴出明文密码；
3. **高熵生成律**：新增密码条目时，必须强制生成 $\ge 16$ 位包含大小写字母、数字及特殊符号的高熵密码。
