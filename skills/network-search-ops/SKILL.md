---
name: network-search-ops
description: OpenViking 标杆插件 network-search v1.1.0 认知导轨。涵盖 3 家在线厂商 (Keenable 80万次、Exa $90、Tavily 9,000分共 26 个 Key) 与 2 家本地服务 (SearXNG 8888、Crawl4AI 18789) 统一调度、权威 Credits 记账、26-Key Round-Robin 轮询分摊与 45 天滚动归档物理清理规范。
---

# 联网搜索与网页采集聚合中枢认知导轨 (network-search v1.1.0)

## 一、五路引擎物理矩阵与底牌全景 (SSOT)

| 引擎 | 账号与配额池 | 核心物理特长 | 权威计费规则 (Credits) | 保底与降级次序 |
|:---|:---|:---|:---|:---|
| **Keenable** | 8 账号 / 每月 800,000 次 | NEEDLE 动态评测、垂直学术/财经/法条检索 | 响应头 `x-credit-cost`，标准 1.0 次/调用 | 第一梯队 (海量宽幅检索) |
| **Exa** | 9 账号 / 每月 $90.00 额度 | 语义嵌入意图检索、GitHub 代码上下文、findSimilar | 响应体/头 `cost`，标准 $0.004/搜，$0.005/答 | 第二梯队 (意图与开源反查) |
| **Tavily** | 9 账号 / 每月 9,000 积分 | Advanced 交叉核验、Map 站点测绘、Extract 脱水 | 响应体 `credits`，基础 1.0，高级 2.0，提取 1.0/5url | 第三梯队 (深度交叉与测绘) |
| **SearXNG** | 本地 `:8888` 常驻服务 | 45+ 引擎聚合、免翻高速、百度去广告 | 物理免费 (0.0 credits) | 第四梯队 (本地保底) |
| **Crawl4AI** | 本地 `:18789` Playwright | 无头动态渲染、JS 执行、CSS 选择、长文脱水 | 物理免费 (0.0 credits) | 重型动态无头渲染 |

---

## 二、运行态三大核心物理铁律

1. **绝对切除 KeePassXC 导入依赖**：
   - 运行态绝不依赖 KeePassXC，Key 矩阵通过服务端安全配置文件（`~/.openviking/data/search/search_keys.json`）加载；
   - 严禁向人类索要明文 API Key，代码中仅回显 8 位 SHA256 脱敏指纹（如 `kb_899872a3`, `exa_d0fd541d`, `tv_1lQI1jVY`）。

2. **调用必落地 search_key_usage 流水账**：
   - 每次调用优先从官方响应体/响应头捕获权威 credits；
   - 若官方未回传，按官方发布基准计费，杜绝粗糙毛估；
   - 日志标准化脱敏打标：`[SEARCH_KEY_USAGE] fp={key_fp} engine={engine} tool={tool} status={code} credits={credits}`。

3. **数据库防爆炸与 45 天滚动归档物理清理**：
   - 45 天以内的调用记录保留实时明细流水；
   - 超过 45 天的明细记录自动按日聚合归档写入 `search_key_daily_summary`；
   - 归档后**物理删除 45 天前明细**（`DELETE FROM search_key_usage WHERE created_at < datetime('now', '-45 days')`）；
   - 前端大盘直出月度真实汇总时，联合查询明细表与日度归档表，确保历史数据 100% 连贯准确。

---

## 三、12 项原子 MCP 工具 (Tools) 目录

1. `web_search`: 多路宽幅自适应检索 (Keenable ➔ Tavily ➔ SearXNG)；
2. `search_neural`: Exa 语义嵌入神经网络意图检索；
3. `search_qna`: Tavily QnA / Exa 权威解答与引用生成；
4. `search_deep`: Tavily Advanced 深度多源交叉检索；
5. `search_code_context`: Exa GitHub 开源上下文与仓库定位；
6. `search_similar_repos`: Exa findSimilar 竞品与同类反查；
7. `map_site`: Tavily Map 站点拓扑树测绘 (支持 instructions 过滤)；
8. `extract_urls`: Tavily/Exa 免爬虫快速正文脱水抽取；
9. `tavily_crawl`: Tavily Map + Extract 整站自动化爬行流水线；
10. `crawl_local`: 本地 Crawl4AI 18789 Playwright 动态无头渲染；
11. `deep_research`: Exa Agent 多步自主调研长报告；
12. `benchmark_needle`: Keenable NEEDLE 自建基准校验。

---

## 四、四大标准实战工序 SOP

### SOP-1：学术文献与突发事实核查
1. 优先调用 `web_search` 或 `search_deep`；
2. 若涉及长尾论文或残缺标题，调用 `benchmark_needle(category="Scholar")`；
3. 提取权威结论，结论沉淀入 OpenViking 体外大脑 `master_memory`。

### SOP-2：开源代码与生态选型反查
1. 调用 `search_code_context(query="FastMCP python streamable http")` 快速定位 GitHub 开源实现；
2. 若需寻找同类竞品，调用 `search_similar_repos(url="https://github.com/...")` 进行生态横评。

### SOP-3：整站拓扑测绘与免爬虫清洗
1. 调用 `map_site(url=..., instructions="find api documentation pages")` 获取整站结构；
2. 批量调用 `extract_urls(urls=[...])` 由云端免翻突破 Cloudflare 盾提取清洗后 Markdown。

### SOP-4：重型动态 JS 网页抓取
1. 遇到需要等待 DOM 渲染或执行特定 JS 的页面，调用 `crawl_local(url=..., wait_for="#app", css_selector="main")`；
2. 返回纯净 `fit_markdown`，内容强制截断 $\le 8\text{KB}$ 防爆上下文。
