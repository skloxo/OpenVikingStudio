# dsh-plugin-search-gateway

> Search Gateway 独立多引擎联网搜索与采集聚合套件 (DeepSeek Harness / Cordis 规范)

## 核心设计哲学 (双模态单一真相源 SSOT)

底层由统一的搜索微服务 `services/search-gateway` 驱动，维护 26-Key 轮询矩阵 (Keenable 80万次池 + Tavily + SearXNG 本地保底)，对外提供两种正交形态：

### 形态一：原生标准 API 模式 (接口地址 + Key，零插件安装)
**适用场景**：DeepSeek Harness (DSH) 等官方原生支持自定义搜索 API 端点的客户端。
- **无需安装任何插件**；
- 在客户端「联网搜索设置」中填入：
  - **搜索接口地址**：`https://vk.tide.red:18888/v1/search` (公网) 或 `http://127.0.0.1:18888/v1/search` (本地)
  - **搜索鉴权 Key**：在 OpenViking 用户中心签发的 User API Key
- 即刻享受 26-Key 矩阵高并发分摊、429 自动熔断与微秒级换 Key 重试。

### 形态二：定制插件模式 (Cordis 插件 / MCP 工具箱)
**适用场景**：客户端不具备原生搜索配置能力，或需要调用 12 项原子高级工具 (学术搜索、金融行情、Crawl4AI 动态正文渲染抽取等)。
- **一键安装插件**：
  ```bash
  npm install https://vk.tide.red/studio/dsh-plugin-search-gateway.tgz
  ```
- **配置项 (cordis.yml)**：
  ```yaml
  plugins:
    dsh-plugin-search-gateway:
      endpointUrl: http://127.0.0.1:18888/mcp
      apiKey: your-user-api-key
      enableMcp: true
  ```
