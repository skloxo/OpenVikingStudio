# DeepSeek Harness (DSH) 原生插件工程架构与开发准则 (SSOT)

本规范基于 DeepSeek Harness 官方 Cordis 微内核架构与火山引擎 OpenViking 官方上游实战经验总结，确立全团队在开发、适配与重构 DSH 插件时的统一工程准则与防坑底线。

---

## 一、DSH 插件物理本质与三层结构

DeepSeek Harness (DSH) 插件体系基于 **Cordis 微内核与依赖注入框架** 构建，采用双轨运行架构：

```
┌────────────────────────────────────────────────────────┐
│               DeepSeek Harness 客户端宿主               │
├──────────────────────────┬─────────────────────────────┤
│   1. 视图层 (Client GUI)  │    2. 运行时层 (Runtime)     │
│  - client.js (Vue/Slot)  │  - index.js (Cordis Plugin) │
│  - 抽屉配置面板与连通性测试 │  - 会话拦截器 / 上下文注入  │
├──────────────────────────┴─────────────────────────────┤
│             3. 元数据契约层 (package.json)               │
│  - npm 规范命名、版本、入口定义与依赖声明               │
└────────────────────────────────────────────────────────┘
```

1. **运行时层 (`index.js`)**：
   - 服务端/Node.js 运行时，接收 Cordis 上下文 `ctx`；
   - 监听核心生命周期事件（如 `session.before-chat-completion`），在 Agent 思考与推理前完成体外上下文召回并精准注入 Prompt。
2. **视图层 (`client.js`)**：
   - 通过 `ctx.slots.inject('plugins.bundle.config', ...)` 挂载到 DSH 插件抽屉面板；
   - 负责凭据输入（API Base / API Key）、连通性测试探针以及状态反馈。
3. **元数据层 (`package.json`)**：
   - 遵循 npm 标准规范，定义 `name`（如 `dsh-plugin-openviking-ops`）、`version` 与 entry。

---

## 二、六大核心开发铁律与避坑防线

### 1. 零信任单轨鉴权铁律 (Zero-Trust Single Track)
- **物理封杀本地免密**：严禁在服务端使用 `127.0.0.1` 白名单绕过鉴权，绝不给反向代理留下安全漏洞；
- **前端输入硬门禁**：在 `client.js` 点击“连通性测试”时，**必须强制前置校验用户 API Key**；未填写时立即阻断并弹红告警，严禁向服务端发起无密或虚假测试请求；
- **标准认证头**：所有 API 交互统一采用 `Authorization: Bearer <API_KEY>`。

### 2. 上下文注入脱水与信噪比保护
- **严禁全量倾倒**：从 OpenViking 召回的知识、记忆或运维状态，注入 Prompt 前必须先进行**脱水处理**（移除冗余 JSON 结构、内部 ID 与调试追踪）；
- **Token 预算受限**：单次注入 Prompt 的字符数严格受控（通常 $\le 1000$ 字符），防止挤占用户上下文与模型推理注意力；
- **语义分块清晰**：注入格式统一使用 Markdown 引用块或标准 XML 标签（如 `<openviking_context>`）。

### 3. 生命周期安全注销与零泄漏 (Lifecycle Disposal)
- **定时器与监听清理**：在 `index.js` 中创建的任何 `setInterval`、长轮询任务或事件订阅，必须在 Cordis 插件的 `ctx.on('dispose', () => { ... })` 钩子中完全清除；
- **禁止全局变量挂载**：严禁在 `global` 或宿主 `window` 对象直接挂载全局状态，所有服务必须挂载在 `ctx` 容器上。

### 4. 反向代理与网络穿透适应性
- **兼容双端协议**：DSH 客户端可能运行在浏览器端或 Electron 桌面端。请求 OpenViking 时必须同时支持绝对 URL 与相对网关反代路径；
- **超时与熔断保护**：所有网络请求必须设置明确的超时时间（连通性测试 $\le 3\text{s}$，普通查询 $\le 10\text{s}$），严禁发起无超时的挂起请求。

### 5. 单一真相源 (SSOT) 与自动化打包流水线
- **禁止手工改包**：插件修改后，版本号在 `package.json` 递增；
- **打包流水线收敛**：统一运行 `python scripts/pack_all_plugins.py`，流水线自动以 `is_npm=True` 将包结构包裹为 `package/` 并在 `public/` 与 `dist/` 生成不可变的 `.tgz` 分发包；
- **杜绝幽灵断层**：严禁只改源码不重新生成 `.tgz`，确保分发中心下载的内容与源码 100% 字节同频。

### 6. 渐进式降级与 Fail-Safe 原则
- **体外中枢异常不阻塞核心对话**：当 OpenViking 服务端未启动、网络离线或接口超时时，`index.js` 必须捕获异常并静默放行，绝不可导致 DSH 整个对话流程报错崩溃。

---

## 三、标准 DSH 插件结构模板

```
integrations/deepseek-harness/dsh-plugin-<name>/
├── package.json          # 插件元信息 (name, version, entry)
├── index.js              # Cordis 运行时插件核心 (拦截器与事件注入)
├── client.js             # 客户端抽屉 GUI 与连通性测试 (Vue3/Slot)
├── server.js (可选)      # 本地代理中转服务 (若有复杂协议桥接)
└── README.md             # 部署与配置说明
```

---

## 四、连通性测试最佳实践 (client.js 模式)

```javascript
// 连通性测试防空跑标准范例
async testConnection() {
  const api = (this.apiUrl || '').trim();
  const key = (this.userKey || '').trim();
  
  if (!key) {
    this.statusMessage = '❌ 请先填写用户专属 API 密钥 (User Key)，严禁无密测试！';
    this.statusType = 'error';
    return;
  }
  
  this.testing = true;
  try {
    const res = await fetch(`${api}/api/v1/health`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${key}`,
        'Accept': 'application/json'
      },
      signal: AbortSignal.timeout(3000)
    });
    if (res.ok) {
      this.statusMessage = '✔ 连通性测试通过！';
      this.statusType = 'success';
    } else {
      this.statusMessage = `❌ 鉴权失败: HTTP ${res.status}`;
      this.statusType = 'error';
    }
  } catch (err) {
    this.statusMessage = `❌ 网络连接异常: ${err.message}`;
    this.statusType = 'error';
  } finally {
    this.testing = false;
  }
}
```
