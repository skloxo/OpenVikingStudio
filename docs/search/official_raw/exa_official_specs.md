
# Exa 官方搜索引擎核心事实与标准协议规范 (v2.x 最新)

1. API 端点全景:
   - POST https://api.exa.ai/search (语义嵌入与神经意图搜索)
   - POST https://api.exa.ai/findSimilar (基于相似 URL 或文本发现竞品)
   - POST https://api.exa.ai/contents (批量获取清洗正文与高亮摘要)
   - POST https://api.exa.ai/answer (生成式直接回答与引用来源)
   - POST https://api.exa.ai/agent/runs (⚠️ 官方最新 Agent 自主多步调研任务，原 /research 报 410 已彻底废弃)

2. 鉴权与请求头:
   x-api-key: <key>
   Content-Type: application/json

3. 核心参数矩阵:
   - /search:
     query (string), numResults (int), useAutoprompt (bool),
     type ("neural" | "fast" | "auto"),
     category ("github" | "tweet" | "company" | "pdf" | "research paper" | "news"),
     contents: {"text": true, "highlights": true, "summary": true}
   - /agent/runs:
     query (string, 调研主题与指令),
     effort ("auto" | "low" | "medium" | "high")
   - /findSimilar:
     url (string), numResults (int), excludeSourceDomain (bool)

4. 计费与 Credits:
   标准检索: $0.004 / 次
   Answer 回答: $0.005 / 次
   每月每个免费账户赠送 $10.00 额度 (9 个账号累计每月 $90.00 额度)
