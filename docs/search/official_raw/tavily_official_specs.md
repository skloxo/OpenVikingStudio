
# Tavily 官方搜索引擎核心事实与标准协议规范

1. API 端点全景:
   - POST https://api.tavily.com/search (基础/深度多源搜索)
   - POST https://api.tavily.com/extract (批量正文免爬虫抽取)
   - POST https://api.tavily.com/map (站点拓扑测绘树生成)
   - POST https://api.tavily.com/crawl (自动化整站爬行管线)

2. 鉴权铁律 (SSOT):
   - 核心请求头: Authorization: Bearer <key> (⚠️ 强制要求！/map 和 /crawl 缺失 Header 必报 401 Unauthorized)
   - 请求体兼容字段: api_key (双重保险注入)

3. 详细参数矩阵:
   - /search:
     query (string), search_depth ("basic" | "advanced"), include_answer (bool),
     max_results (int), include_images (bool), include_raw_content (bool),
     include_domains (list), exclude_domains (list)
   - /extract:
     urls (list[string]), extract_depth ("basic" | "advanced")
   - /map:
     url (string), max_results (int), instructions (string, 语义指令过滤)
   - /crawl:
     url (string), max_depth (int), limit (int)

4. 权威记账 (Credits):
   Response Body 包含:
   "credits": 1.0 (basic search) / 2.0 (advanced search) / 1.0 per 5 URLs (extract)
