
# Keenable 官方搜索引擎核心事实与标准协议规范

1. API 基础端点:
   POST https://api.keenable.ai/v1/search
   Header 鉴权:
   X-API-Key: <key>
   Content-Type: application/json

2. 请求参数体 (JSON Body):
   - query (string, 必需): 检索关键词或自然语言问题
   - max_results (int, 可选, 默认 10): 返回结果数量 (⚠️ 绝对禁止使用 num，否则 100% 报 400 Bad Request)
   - mode (string, 可选, 默认 "fast" | "pro"): "fast" 极速返回, "pro" 高精度语义提权
   - snippet_max_length (int, 可选): 摘要片段字符上限
   - domains (list[string], 可选): 限制搜索域名
   - exclude_domains (list[string], 可选): 排除域名

3. 官方 NEEDLE 基准体系:
   NEEDLE (Needle In A Haystack Dynamic Evaluation) 是官方研发的 5 大垂直领域评估集:
   - Scholar (学术与长尾论文)
   - Finance (财报、宏观指标与行情)
   - Legal (法规法条与合规案例)
   - News (突发热点与时间敏感新闻)
   - Rare (冷门小众知识与长尾技术问题)
   在调用时，通过 mode="pro" 并注入垂类指令，可激活 NEEDLE 顶格召回能力。

4. 响应结构与权威记账:
   Response Header 携带:
   x-credit-cost: 1.0 (或实际消耗点数)
   Response Body:
   {
     "results": [
       {"title": "...", "url": "...", "content": "...", "score": 0.95}
     ]
   }
