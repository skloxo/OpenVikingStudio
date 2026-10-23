---
name: network-search-ops
description: OpenViking 标杆插件 network-search v1.1.2 认知导轨。涵盖 3 家在线厂商 (Keenable 80万次、Exa $90、Tavily 9,000分共 26 个 Key) 与 2 家本地服务 (SearXNG 8888、Crawl4AI 18789) 统一调度、权威 Credits 记账、26-Key Round-Robin 轮询分摊、排查避坑铁律与 Search2API 商业化网关架构。
---

# 联网搜索与网页采集聚合中枢认知导轨 (network-search v1.1.2)

## 一、五路引擎物理矩阵与底牌全景 (SSOT)

| 引擎 | 账号与配额池 | 核心物理特长 | 权威计费规则 (Credits) | 保底与降级次序 |
|:---|:---|:---|:---|:---|
| **Keenable** | 8 账号 / 每月 800,000 次 | NEEDLE 5大垂直检索、Scholar/Finance/Legal 深度提权 | 响应头 `x-credit-cost`，标准 1.0 次/调用 | 第一梯队 (海量宽幅与垂类打底) |
| **Exa** | 9 账号 / 每月 $90.00 额度 | 神经语义嵌入、GitHub 开源仓库定位、Agent 调研 | 响应体/头 `cost`，标准 $0.004/搜，$0.005/答 | 第二梯队 (语义意图与代码反查) |
| **Tavily** | 9 账号 / 每月 9,000 积分 | Advanced 交叉核验、Map 站点拓扑测绘、Extract 免爬脱水 | 响应体 `credits`，基础 1.0，高级 2.0，提取 1.0/5url | 第三梯队 (高精交叉与防盾测绘) |
| **SearXNG** | 本地 `:8888` 常驻服务 | 45+ 引擎聚合、免翻高速、百度去广告 | 物理免费 (0.0 credits) | 第四梯队 (本地私有保底) |
| **Crawl4AI** | 本地 `:18789` Playwright | 无头动态渲染、JS 执行、CSS 选择、长文脱水 | 物理免费 (0.0 credits) | 重型动态无头渲染 |

---

## 二、官方协议对齐与四大排查避坑铁律

1. **Keenable 必须使用 `max_results` (严禁使用 `num`)**：
   - 官方端点：`POST https://api.keenable.ai/v1/search`，请求头 `X-API-Key: <key>`；
   - 严禁传入 `num` 参数，否则官方网关 100% 拒绝并报 `400 Bad Request`；必须统一使用 `max_results`；
   - NEEDLE 是官方 5 大垂直评估基准（Scholar, Finance, Legal, News, Rare），已收敛为垂直专家检索 `search_vertical_expert`，使用 `mode="pro"` 配合垂类 Prompt 提权。

2. **Exa 调研长任务必须使用 `POST /agent/runs` (严禁使用 `/research`)**：
   - 旧端点 `https://api.exa.ai/research` 已被官方彻底废除并报 `410 Gone`；
   - 官方最新 Agent 调研端点为 `POST https://api.exa.ai/agent/runs`，入参格式为 `{"query": "...", "effort": "auto"}`；
   - Agent 调研属深度多步长任务，客户端超时必须配置为 $\ge 60\text{s}$。

3. **Tavily 必须强制在 HTTP Header 携带 `Authorization: Bearer <key>`**：
   - 官方端点 `/map` 和 `/crawl` 强制在 HTTP Header 校验 Bearer Token；若仅在 JSON body 传递 `api_key` 会被网关拦截报 `401 Unauthorized`；
   - 客户端所有请求头必须固定注入 `headers["Authorization"] = f"Bearer {key}"`。

4. **Crawl4AI 必须注入 Token 并由 systemd 固化微网关守护**：
   - 本地 Docker 启用了鉴权，请求头必须携带 `Authorization: Bearer <token>`；
   - 微网关通过 `/etc/systemd/system/crawl4ai-search-gateway.service` 监听 18792 端口，设置 `Restart=always` 避免进程退出导致 SearXNG 穿透爬虫瘫痪。

---

## 三、运行态数据安全与资产隔离规范

1. **绝对切除 KeePassXC 导入依赖**：
   - 运行态绝不依赖 KeePassXC，Key 矩阵统一收口于服务端安全配置文件（`~/.openviking/data/search/search_keys.json`，权限 `600`）；
   - 严禁在代码、日志中回显明文 API Key，仅显示 8 位 SHA256 脱敏指纹。

2. **调用必落地 search_key_usage 流水账**：
   - 每次调用优先从官方响应体/响应头捕获权威 credits；
   - 若官方未回传，按官方发布基准计费，杜绝粗糙毛估；
   - 日志标准化脱敏打标：`[SEARCH_KEY_USAGE] fp={key_fp} engine={engine} tool={tool} status={code} credits={credits}`。

3. **数据库防爆炸与 45 天滚动归档物理清理**：
   - 45 天以内的调用记录保留实时明细流水；
   - 超过 45 天的明细记录自动按日聚合归档写入 `search_key_daily_summary`；
   - 归档后物理删除 45 天前明细。

---

## 四、12 项原子 MCP 工具 (Tools) 目录

1. `web_search`: 多路宽幅自适应检索 (Keenable ➔ Tavily ➔ SearXNG)；
2. `search_academic`: 学术论文与专业期刊专项检索；
3. `search_finance`: 财经要闻与上市公司公开信息快搜；
4. `search_code`: GitHub/GitLab 源码与算法实现定位；
5. `search_news`: 实时新闻资讯与突发快讯秒级获取；
6. `search_deep`: 深度推演宽幅搜索 (自动多词并发与交叉验证)；
7. `web_fetch`: 基础网页正文脱水提取 (过滤 HTML 噪音)；
8. `web_fetch_deep`: 深度无头浏览器渲染抓取 (支持动态 SPA 页面)；
9. `search_provider_status`: 检查当前 26 个 Key 矩阵与渠道健康度；
10. `search_accounting_summary`: 查看历史搜索开销与配额流水账；
11. `search_rotate_keys`: 手动触发失效 Key 轮询或权重自愈；
12. `search_key_audit`: 导出各搜索引擎调用明细与响应时延。
