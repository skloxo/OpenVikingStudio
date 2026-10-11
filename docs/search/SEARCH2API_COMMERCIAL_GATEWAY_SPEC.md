# 🚀 Search2API: 多账号聚合商业化搜索网关架构规格书 (Commercial Spec)
> **编制时间**: 2026-10-11 23:10:35 CST  
> **战略定位**: 将全集群 26 个官方免费账号（每月 80万+ 次）聚合转化为高可用、高抗封、标准兼容的对外商业 API 服务。  

---

# Search2API 商业化搜索聚合网关架构与变现方案设计

## 一、 统一协议适配层 (Multi-Protocol Adapter)

本层旨在将 OpenAI ToolCall、SearXNG、Tavily 等异构协议统一转换为 Keenable 官方 API 标准参数，并做响应结构逆向标准化。

### 1. 协议转换映射表
| 源协议 / 格式 | 源参数 | 转换目标 (Keenable 参数) | 备注与严格约束 |
| :--- | :--- | :--- | :--- |
| **OpenAI ToolCall** | `tool_choice.search.args.query` | `query` | 必需字段，提取工具调用参数。 |
| | `tool_choice.search.args.num` / `max_results` | `max_results` | **强校验拦截：** 若检测到 `num` 参数，网关层必须拦截并重命名为 `max_results`，防止触发 Keenable 100% 400 报错。 |
| | `tool_choice.search.args.mode` | `mode` | 默认 `"fast"`，支持 `"pro"`。 |
| **SearXNG API** | `q