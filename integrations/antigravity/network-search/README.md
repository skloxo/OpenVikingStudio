# 🌐 Search Gateway 独立搜索与采集网关 (Microservice SSOT)

> **解耦声明**：本服务已从 OpenViking 单体大脑中物理剥离解耦，作为独立的搜索与爬虫采集微服务运行 (端口 18888)。

---

## 📌 一、 核心定位与第一性原理

- **正交解耦**：OpenViking 专心做体外大脑（长程记忆、向量库、上下文路由）；Search Gateway 专心做联网搜索、网页爬取与多 Key 轮询分摊。
- **26-Key 负载均衡池**：内置 Keenable（80万次池）、Tavily、SearXNG 本地保底、Crawl4AI 无头采集，自动熔断自愈。
- **标准化多端消费**：
  - 支持作为标准 FastMCP Server 挂载到任何智能体（Antigravity、DSH、Cursor、Claude Desktop、Dify）；
  - 支持作为标准 HTTP/SSE 接口对外提供搜索服务（对标 CPA2API 商业化能力）。

---

## 🛠️ 二、 提供的 12 大标准化 MCP 工具

1. `web_search`: 多路宽幅自适应检索 (Keenable -> Tavily -> SearXNG 本地)
2. `search_academic`: 学术论文与专业期刊专项检索
3. `search_finance`: 财经要闻与上市公司公开信息快搜
4. `search_code`: GitHub/GitLab 源码与算法实现定位
5. `search_news`: 实时新闻资讯与突发快讯秒级获取
6. `search_deep`: 深度推演宽幅搜索 (自动多词并发与交叉验证)
7. `web_fetch`: 基础网页正文脱水提取 (过滤 HTML 噪音)
8. `web_fetch_deep`: 深度无头浏览器渲染抓取 (支持动态 SPA 页面)
9. `search_provider_status`: 检查当前 26 个 Key 矩阵与渠道健康度
10. `search_accounting_summary`: 查看历史搜索开销与配额流水账
11. `search_rotate_keys`: 手动触发失效 Key 轮询或权重自愈
12. `search_key_audit`: 导出各搜索引擎调用明细与响应时延

---

## 🚀 三、 启动与接入方式

### 1. 本地 stdio 模式 (适用于 IDE MCP 客户端):
```bash
python server.py
```

### 2. 独立微服务后台守护模式 (SSE 端口 18888):
```bash
MCP_TRANSPORT=sse SEARCH_GATEWAY_PORT=18888 python server.py
```

---

## 🎯 四、 DeepSeek Harness (DSH) 原生零插件极速接入指南 (最新规范)

> **零客户端插件**：无需安装任何第三方插件包，DSH 原生支持官方 Web 搜索 API。

### 1. DSH 客户端界面设置
1. 打开 DSH 客户端，点击左侧菜单栏 **「插件」➔「网页搜索」**；
2. 勾选开关：**【启用新版 Web 搜索 API】**（开启后自动切换至原生 Search & Fetch 工具模式）；
3. 填写关键配置项：
   - **Search / Fetch API 基础地址**：
     - 本地运行：`http://127.0.0.1:18888/v1/tools`
     - 局域网或公网穿透：`https://sear.tide.red/v1/tools`（程序会自动追加 `/search` 与 `/fetch`）
   - **API Key**：
     - 填入在服务端配置的鉴权 Key（默认支持免密本地环回或通过环境变量 `SEARCH_GATEWAY_API_KEYS` 自定义）；
   - **每次搜索结果数**：
     - 推荐填写 `10`（支持 1~50 条，网关自动限额与重排）；
4. 点击 **「保存」** 按钮。

### 2. 即刻享受的降维超能力
- **100% 免费多 Key 分摊**：免除官方按次扣费，无缝享受 26-Key 轮询矩阵（Keenable 80万次池 + Tavily + SearXNG 本地保底）；
- **动态无头浏览器动态自愈抓取**：当模型阅读特定网页时，网关双速抓取（极速静态流 + 本地 Playwright 18789 动态渲染降级），穿透 SPA 单页应用与反爬；
- **真实重排分与精炼摘要**：严格限制 `snippet` 与 `summary` 上下文预算，保护模型注意力不被噪声污染。
