# DeepSeek Harness (DSH) 原生插件特性化规范与实战指南

> **归属中枢**：[openviking-plugin-ops](../SKILL.md)  
> **适用宿主**：DeepSeek Harness (桌面客户端 / Web / CLI)，底层基于 Cordis 微内核。

---

## 1. 宿主特性架构与 Manifest 声明

DSH 采用 Cordis 微内核架构，插件分为宿主半侧（Host Half）与浏览器半侧（Browser Half）。

### 1.1 `package.json` 核心契约
必须显式声明 `dsh.bundle.patch`，否则客户端包管理器会将其判定为普通依赖 (`not-bundle`) 而拒绝作为 profile layer 加载：
```json
{
  "name": "dsh-plugin-openviking",
  "version": "1.4.0",
  "type": "module",
  "main": "index.js",
  "dsh": {
    "bundle": {
      "patch": "./cordis.patch.yml"
    }
  },
  "peerDependencies": {
    "@deepseek-ai/cordis": "*",
    "@deepseek-ai/schemastery": "*"
  },
  "peerDependenciesMeta": {
    "@deepseek-ai/cordis": { "optional": true },
    "@deepseek-ai/schemastery": { "optional": true }
  }
}
```

### 1.2 `cordis.patch.yml` 伴生清单
声明插件在目标 profile 中的默认条目，必须使用 `- insert:` 包裹：
```yaml
- insert:
    - id: openviking
      name: dsh-plugin-openviking
      config:
        apiUrl: "https://vk.tide.red"
        userId: "default"
        apiKey: ""
        enableMcp: true
        enableHook: true
        peer: "deepseek-harness@satellite"
```

---

## 2. Config Schema 与 Volatile GUI 门禁公理

### 2.1 Volatile 过滤门禁（为什么界面会没有输入框）
- **物理底层机制**：DSH 设置服务（`@deepseek-ai/dsh-settings`）在构建前端表单时，执行严格的 `volatileForm(schema)` 门禁：**只有声明了 `.volatile()` 的字段才进入 SettingsForm 渲染，普通未标记字段被完全排除**！
- **防御性默认值铁律**：非必填项必须显式追加 `.default('')`，严禁未设默认值引发启动期 `ValidationError: $.apiUrl missing required value`；
- **安全密码掩码**：敏感凭据通过 `.role('secret')` 声明，前端自动渲染为带小眼睛密码遮罩输入框。

### 2.2 标准 Schema 定义范式 (内联自包含 Single-File Bundle)
```javascript
// 优先使用预编译内联的单文件 schema.js (34KB)，避免脱机环境缺失 @deepseek-ai/schemastery 导致 GUI 表单空白
import Schema from './schema.js'

function v(s) {
  return typeof s?.volatile === 'function' ? s.volatile() : s
}

export const Config = Schema.object({
  apiUrl: v(Schema.string().default('https://vk.tide.red')).description('OpenViking 服务端端点'),
  userId: v(Schema.string().default('default')).description('租户 / 账户身份标识'),
  apiKey: v(Schema.string().role('secret').default('')).description('API Key (带密码遮罩)'),
  enableMcp: v(Schema.boolean().default(true)).description('是否挂载体外 MCP 工具箱 (通过 RPC 动态投影 50 项工具)'),
  enableHook: v(Schema.boolean().default(true)).description('是否启用前置记忆感知 Hook'),
  peer: v(Schema.string().default('deepseek-harness@satellite')).description('调用方节点名称标识')
}).description('OpenViking 通用轻量 RPC 桥梁套件配置')
```

---

## 3. Cordis 上下文注入与运行时取值

### 3.1 安全取值器与动态 Fork 销毁管理 (Dispose-Before-Replugin)
Volatile 字段在运行时由 Cordis 动态包装，必须使用防御性 getter 解析；同时监听 `loader/volatile-update` 保存事件时，必须先比对签名并调用 `currentFork.dispose()` 优雅销毁旧实例，彻底消灭重复挂载与死锁：
```javascript
function getVal(v, fallback = '') {
  if (v === undefined || v === null) return fallback
  const res = typeof v?.get === 'function' ? (v.get() ?? fallback) : v
  return typeof res === 'string' ? res.trim() : res
}

export function apply(ctx, config = {}) {
  let currentMcpFork = null
  let lastMcpSignature = ''

  // 1. 动态安全挂载 MCP 工具箱 (支持配置变更热重载，必须先 dispose 旧 Fork 避免死锁/重复监听)
  function mountMcpIfNeeded() {
    const enableMcp = Boolean(getVal(config.enableMcp, true))
    const apiUrl = getVal(config.apiUrl, 'https://vk.tide.red')
    const userId = getVal(config.userId, 'default')
    const apiKey = getVal(config.apiKey, '')

    // 严格判空：未启用 MCP 或未配置地址时，若已存在挂载则优雅注销
    if (!enableMcp || !apiUrl) {
      if (currentMcpFork) {
        currentMcpFork.dispose()
        currentMcpFork = null
        lastMcpSignature = ''
      }
      return
    }

    const signature = `${apiUrl}|${userId}|${apiKey}`
    if (signature === lastMcpSignature && currentMcpFork) {
      return // 签名无变更，跳过重复挂载
    }

    if (currentMcpFork) {
      currentMcpFork.dispose() // 优雅销毁旧 Fork 实例
      currentMcpFork = null
    }

    const mcpUrl = `${apiUrl}/mcp?plugin_id=openviking-memory&user_id=${encodeURIComponent(userId)}`
    currentMcpFork = ctx.plugin('@deepseek-ai/dsh-mcp-client', {
      serverName: 'openviking',
      transport: 'streamable-http',
      url: mcpUrl,
      headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
      reconnect: { enabled: true, initialDelayMs: 500, maxDelayMs: 15000, maxAttempts: 10 }
    })
    lastMcpSignature = signature
  }

  mountMcpIfNeeded()

  // 2. 响应 GUI 点击【保存】事件 (免重启热生效，优雅销毁旧实例)
  ctx.on('loader/volatile-update', () => mountMcpIfNeeded())

  // 3. 用户消息被动感知 Hook
  ctx.on('session/event', (event) => {
    if (Boolean(getVal(config.enableHook, true)) && event?.type === 'user/message') {
      const text = typeof event.content === 'string' ? event.content : event.content?.[0]?.text
      if (text && text.length >= 2) prefetchMemory(text)
    }
  })

  // 4. SystemPrompt 组装期上下文注入
  if (ctx.systemPrompt) {
    ctx.systemPrompt.context({
      name: 'openviking-memory-prefetch',
      order: 90,
      text: () => lastInjectedMemory || ''
    })
  }
}
apply.inject = ['systemPrompt']
```

---

## 4. 打包分发与宿主工程铁律 (SSOT)

1. **分发端点全局单一公网 SSOT (彻底切除 localhost 动态拼装过度工程)**：
   - 🚫 **绝对禁止前端动态自适应**：严禁在前端使用 `window.location.origin` 拼装下载 URL！若用户在本地通过 `http://localhost:1933` 访问，复制出来的链接若贴入远程 3070 节点或 Windows 宿主机的 DSH 客户端，DSH 请求本地 `localhost` 必然触发 `ECONNREFUSED` 报错失败；
   - **唯一公网真实源**：安装链接必须 100% 统一固定为全局公网地址：`https://vk.tide.red/studio/dsh-plugin-openviking-${VERSION}.tgz`（如 `v1.5.0`）。公网地址全集群可达、免穿透、免环境判断、零歧义。
2. **测试真实性第一公理 (严禁开特权后门)**：
   - 普通用户真实环境是唯一验收视网膜！严禁在任何测试节点（2080/3070）私自建立软链接、私改底层 YAML 或注入私有 Token；
   - 所有联调必须 100% 模拟真实用户交互：通过 Web Studio 复制公网链接 ➔ DSH 客户端添加插件 ➔ DSH 设置面板填入工兵 ID 与 Key。
3. **打包与提交原子绑定铁律 (Pack-Commit Atomic Lock)**：
   - 必须遵循标准流水线：`零密钥审计 ➔ 视网膜门禁 ➔ git commit 源码 ➔ npm pack 打包 ➔ 同步至 public/ & dist/`，杜绝未提交代码被并发冲掉；
4. **不可变版本号与长缓存隔离**：
   - 所有发布包强制携带精确语义版本号，抽屉显式挂载 Badge `v1.5.0`，彻底消灭泛化 URL 带来的浏览器与 pnpm lockfile 长缓存死锁。
