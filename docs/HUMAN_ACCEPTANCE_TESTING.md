# 👁️ OpenViking 人工肉眼走查与验收清单 (Human Acceptance Testing Manifest)

> **文档定位 (SSOT)**：本文件是人类开发者进行人工功能走查、UI 肉眼检验与验收交付的**唯一物理指南**。  
> 每次功能迭代交付后，必须同步在此追加【30 秒肉眼用例】，确保无需翻阅代码即可通过浏览器与直观交互完成全量验证。

---

## 🌐 验收环境与核心中枢直达

- **Studio 控制台首页**：[http://127.0.0.1:1933/studio](http://127.0.0.1:1933/studio)
- **信息治理与检索总控台**：[http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval)
- **运行时日志与门禁中枢**：[http://127.0.0.1:1933/studio/harness-logs](http://127.0.0.1:1933/studio/harness-logs)
- **隔离检疫总控大盘**：[http://127.0.0.1:1933/studio/quarantine](http://127.0.0.1:1933/studio/quarantine)
- **全会话管理与心跳脱水**：[http://127.0.0.1:1933/studio/sessions](http://127.0.0.1:1933/studio/sessions)
- **后台服务守护进程**：`systemd --user openviking.service`（监听本地端口 `1933`）

### 🚫 视觉硬性红线排查标准
1. 🚫 **绝对严禁出现任何绿色 (NO GREEN EVER)**（良好默认湛蓝/冰青 `cyan-500`，中性灰底色，告警琥珀 `amber-400`，异常玫瑰红 `rose-500`）；
2. 🚫 **字号物理下限 $\ge 12\text{px}$ (`text-xs`)**，微字彻底封杀；
3. 🚫 **数值列统一使用等宽字体 `font-mono tabular-nums`**；
4. 🚫 **卡片底边与内边距紧凑**，内边距收敛至 `p-3`~`p-3.5`，图标尺寸 `size-2.5`~`size-3.5`。

---

## 📊 走查模块总索引速查表 (Checklist Index)

| 序号 | 目标版本 | 功能模块与座舱名称 | 直达路径与入口 | 核心关注看点 | 预估耗时 | 验收状态 |
|:---:|:---:|:---|:---|:---|:---:|:---:|
| 1 | **`v1.5.14`** | **隔离与检疫座舱** | `/studio/quarantine` | 4 KPI 真实数据、隔离清单、安全还原 | 30 秒 | [ ] |
| 2 | **`v1.5.15`** | **会话心跳脱水与分类过滤** | `/studio/sessions` | 分类芯片切换、心跳脱水徽章、零假数据 | 30 秒 | [ ] |
| 3 | **`v1.5.16`** | **BM25 + 稠密向量双流混合检索** | `/studio/retrieval` (第 2 卡片) | 4 度量瓦片、双流分栏、RRF 来源标签 | 30 秒 | [ ] |
| 4 | **`v1.5.17`** | **zg 端侧代码语义检索与分级懒加载** | `/studio/retrieval` (第 3 卡片) | 961 符号、depth=0/1/2 分级切换、Token 节约 | 30 秒 | [ ] |
| 5 | **`v1.5.18`** | **RAG 约束验证与主动弃答门禁** | `/studio/retrieval` (第 4 卡片) | 超纲弃答红胶囊、接地湛蓝胶囊、MinHash 去重 | 30 秒 | [ ] |
| 6 | **`v1.5.19`** | **HG-RAG 分层指南针拓扑与读写分离** | `/studio/retrieval` (第 5 卡片) | 四向罗盘导航、祖先全路径回显、只读零锁 | 30 秒 | [ ] |
| 7 | **`v1.5.20`** | **CPA 教师守卫与五大贯彻门禁** | `/studio/harness-logs` (Tab 2) | 动态 5/5 激活、CPA 教师门禁卡片、脱敏全绿 | 30 秒 | [ ] |
| 8 | **`v1.5.21`** | **零思考记忆提取与截断二分自愈** | `/studio/harness-logs` (Tab 4) | 4 度量瓦片、4 项 Active 门禁、演练试验台 | 30 秒 | [ ] |
| 9 | **`v1.5.22`** | **工程全面稳固与奥卡姆剃刀瘦身** | `/studio/retrieval` | 单文件黄金甜点区、后台断流、高密 Tab | 30 秒 | [ ] |
| 10 | **`v1.5.33`** | **三门结晶减熵与不可变事实 SSOT** | `/studio/retrieval` (Tab 5) | 三门并联硬门禁、L0/L1/L2 晶体、物理净减熵 | 30 秒 | [ ] |
| 11 | **`v1.5.34`** | **主动上下文治理与历史独立分仓** | `/studio/retrieval` (Tab 6) | Active Notes 高密常驻、History 独立检索分仓、零失真 | 30 秒 | [ ] |
| 12 | **`v1.5.35`** | **SkillZip 写入即压缩与门禁试验台** | `/studio/skills` (Tab 2) | 六元组契约、30% 减熵、1.9x 门禁 | 30 秒 | [ ] |
| 13 | **`v1.5.36`** | **前门自动泊车与反熵去噪准入门禁** | `/studio/retrieval` (Tab 7) | <10ms 物理泊车、HTTP 202 票据、去重合流 | 30 秒 | [ ] |

---

## 📋 模块逐项走查实操指南

### 📌 1. [v1.5.14] 隔离与检疫座舱 (`Card-Memory-ColdQuarantine-ZombiePurge`)
- **直达入口**：[http://127.0.0.1:1933/studio/quarantine](http://127.0.0.1:1933/studio/quarantine)
- **Git Tag 锚定**：`v1.5.02` ~ `v1.5.14`
- **操作步骤**：
  1. 打开页面，查看顶部 4 块 KPI 瓦片：
     - `已隔离会话草稿`：展示真实隔离会话数（`1,159` 篇以上）；
     - `释放向量库空间`：显示释放存储容量；
     - `软隔离资源`：显示当前软隔离中资源数量；
     - `检疫守护状态`：显示 `Active Guard`。
  2. 滚动查看已检疫条目列表，条目具有清晰路径与哈希标记；
  3. 检查界面是否有绿色，确认正常元素均为中性哑光灰与冰青色。
- **合格标准**：无假数据 `--`，数据均来源于真实 SQLite 物理库。

---

### 📌 2. [v1.5.15] 会话抗熵增心跳脱水与分类过滤 (`Card-Sessions-AntiEntropy`)
- **直达入口**：[http://127.0.0.1:1933/studio/sessions](http://127.0.0.1:1933/studio/sessions)
- **Git Tag 锚定**：`v1.5.15` (`11ef3d8f1`)
- **操作步骤**：
  1. 打开页面，查看顶部分类过滤按钮组：`全部`、`交互会话`、`运维心跳`、`任务会话`；
  2. 点击 **`交互会话`**：列表过滤掉自动巡检会话，仅展示真实交互记录；
  3. 点击 **`运维心跳`**：列表展示带脱水标记的心跳会话；条目上带有冰青色胶囊 `Dehydrated Heartbeat`；
  4. 检查右上角检索框，输入关键字实时过滤；
- **合格标准**：按钮切换毫秒级响应无抖动，心跳会话自动折叠脱水，不污染主会话列表。

---

### 📌 3. [v1.5.16] BM25 + 稠密向量双流混合检索座舱 (`Card-Retrieval-BM25Hybrid`)
- **直达入口**：[http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval) ➔ 顶部第 2 块卡片 `BM25HybridCockpit`
- **Git Tag 锚定**：`v1.5.16` (`4dc01fc3c`)
- **操作步骤**：
  1. 打开页面，滚动至第二块卡片；
  2. 检查 4 块核心 KPI 瓦片：
     - 倒排索引规模：显示真实文档数（`1,279` 篇）；
     - 精确符号提权数：显示 `≥ 1`；
     - 双流重合率：显示真实百分比（`~4.8%`）；
     - 融合延迟：显示单调时钟开销（`< 2ms`）；
  3. 点击预设芯片 `is_heartbeat_session` 或 `VikingFS.commit`：
     - 观察左右双流分栏输出，左侧为 SQLite FTS5 BM25 词法结果，右侧为 Dense Vector 结果；
     - 观察融合结果列表，各条目具有 `[hybrid]`、`[sparse_only]` 或 `[dense_only]` 来源角标。
- **合格标准**：点击芯片 100ms 内即刻回显，双流融合结果准确无误。

---

### 📌 4. [v1.5.17] zg 端侧代码语义检索与分级懒加载座舱 (`Card-Retrieval-LocalFirst-zgSemanticSearch`)
- **直达入口**：[http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval) ➔ 第 3 块卡片 `ZGSearchCockpit`
- **Git Tag 锚定**：`v1.5.17` (`4c0d4577b`)
- **操作步骤**：
  1. 页面滚动至 `ZGSearchCockpit` 卡片；
  2. 检查顶部 4 块度量瓦片：
     - 总符号数：显示已提取符号（`961` 个）；
     - 覆盖核心文件：`80` 个；
     - 代码行数：`26,666` 行；
     - Token 节约率：显示约 `78.4%`；
  3. 点击预设 `RRF 倒数排名融合`（或在输入框中输入 `rrf_fuse` 并回车）：
     - 点击右侧深度切换按钮 `指纹 (depth=1)`，观察回显结果为函数签名前后 1 行紧凑指纹与 SHA-256 哈希；
     - 点击 `全量 (depth=2)`，观察动态展开完整代码块；
     - 点击 `元数据 (depth=0)`，观察仅回显行号跨度与文件路径。
- **合格标准**：分级切换流畅，AST 符号精确定位到真实 Python 文件行号跨度。

---

### 📌 5. [v1.5.18] RAG 约束验证与主动弃答门禁 (`Card-RAG-Abstention-ZeroHallucination-Pipeline`)
- **直达入口**：[http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval) ➔ 第 4 块卡片 `RAGAbstentionCockpit`
- **Git Tag 锚定**：`v1.5.18` (`11a0db824`)
- **操作步骤**：
  1. 页面滚动至 `RAGAbstentionCockpit` 卡片；
  2. 查看 4 块 KPI 瓦片：主动弃答率、平均置信度、MinHash 64-perm LSH 状态、门禁延迟；
  3. **出域防幻觉负向测试**：
     - 点击预设场景芯片 `超纲弃答 (无依据烘焙问题)`；
     - 观察下方弹出玫瑰红警示胶囊 **`[主动弃答 (ABSTAINED)]`**；
     - 弃答原因明确提示：`OUT_OF_DOMAIN: Zero semantic overlap between query and evidence`；
  4. **保真接地正向测试**：
     - 点击预设场景芯片 `保真可答 (OpenViking 端口与架构)`；
     - 观察弹出湛蓝认证胶囊 **`[准许回答 (GROUNDED)]`**；
     - 观察 MinHash 审计列表：重复证据被标记为 `[近重复 (相似 1.0)]` 并安全归并。
- **合格标准**：超纲问题绝不盲猜，重复证据 100% 识别归并。

---

### 📌 6. [v1.5.19] HG-RAG 分层指南针拓扑与读写分离知识工程 (`Card-Knowledge-HG-RAG-HierarchicalCompass`)
- **直达入口**：[http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval) ➔ 第 5 块卡片 `HGRAGCompassCockpit`
- **Git Tag 锚定**：`v1.5.19` (`354d4c965`)
- **操作步骤**：
  1. 页面滚动至 `HGRAGCompassCockpit` 卡片（标题：`HG-RAG 分层指南针拓扑与读写分离知识工程`，版本胶囊：`v1.5.19`）；
  2. 查看 4 块 KPI 瓦片：`拓扑节点总数 (>= 8)`、`根大类体系数 (1)`、`最大拓扑深度 (Level 2)`、`读写分离状态 (Immutable Ready)`；
  3. **四向指南针漫游测试**：
     - 初始停留在 `root_openviking`，观察 North(父类) 置灰，South(下钻) 冰青高亮；
     - 点击 **`South (下钻)`**，锚点移动到 `ch_invariants`；
     - 点击 **`East (后继)`**，横向平移至同级章节 `ch_retrieval`；
     - 点击 **`South (下钻)`**，下钻至叶子实现 `sec_bm25`；
     - 观察右侧 `自洽祖先血缘路径` 完整回显：`OpenViking 核心架构与知识中枢 > 双轨多引擎检索体系 > BM25 FTS5 混合检索`，大类全路径 100% 连贯，无任何断层丢失！
     - 点击 **`North (父类)`**，平滑上浮回退至 `ch_retrieval`。
  4. **快速锚点切换**：点击上方芯片 `zg 语义搜索`，一键直达，血缘路径即刻同步刷新。
- **合格标准**：四向罗盘跳转自洽，叶子节点完整保留祖先大类全路径。

---

### 📌 7. [v1.5.20] CPA 教师模型守卫拦截器与五大贯彻门禁看板 (`Card-Harness-CPATeacherGuard-GateParity-Desensitization`)
- **直达入口**：[http://127.0.0.1:1933/studio/harness-logs](http://127.0.0.1:1933/studio/harness-logs)
- **Git Tag 锚定**：`v1.5.20` (`06e774630`)
- **操作步骤**：
  1. 打开页面，查看顶部第 3 块 KPI 瓦片 `物理贯彻门禁`：清晰渲染为 **`5 / 5 项已激活`**（动态计算，非写死）；
  2. 查看 Tab 导航栏：第 2 个 Tab 明确展示为 **`五大贯彻门禁看板`**；
  3. 点击 **`五大贯彻门禁看板`** Tab，滚动查看 5 块不可变式门禁卡片：
     1. `物理增量代码门禁 (Physical Diff Gate)`
     2. `测试视网膜反欺诈门禁 (Anti-Cheat Retina)`
     3. `防偷懒代码省略占位符栏栅 (Anti-Lazy Code Guard)`
     4. `生成与评估角色隔离 (Role Separation)`
     5. `CPA 教师模型守卫拦截器 (CPA Teacher Model Guard)`
  4. 查看第 5 张卡片：
     - 右上角胶囊展示 `Active Invariant`（冰青色）；
     - 说明文字：`毫秒级物理拦截工兵任务/批量并发滥用昂贵教师模型 (GPT/Claude)，确保教师零泄漏、工兵高吞吐`；
     - 规则标签列表：`block_expensive_models_in_workers`, `regex_audit_gpt_claude`, `require_explicit_teacher_flag`, `cost_aware_routing`；
  5. 安全合规：访问 `/studio/skills`，技能全部脱敏清洗，零内网 IP 与零敏感凭据。
- **合格标准**：动态回显 `5 / 5 项已激活`，门禁卡片完整，遵循 NO GREEN EVER 🚫。

---

### 📌 8. [v1.5.21] 记忆提取零思考与截断二分自愈座舱 (`Card-Extraction-ZeroThinking-BisectionHeal`)
- **直达入口**：[http://127.0.0.1:1933/studio/harness-logs](http://127.0.0.1:1933/studio/harness-logs) ➔ 第 4 个 Tab `零思考与二分自愈`
- **Git Tag 锚定**：`v1.5.21` (`894638371`)
- **操作步骤**：
  1. 打开页面，点击第 4 个 Tab **`零思考与二分自愈`**；
  2. 观察座舱顶部标题：`记忆提取零思考与截断二分自愈座舱 (Zero-Thinking & Bisection Heal)`，右侧角标 `v1.5.21 · P0`；
  3. **4 块核心度量 KPI 瓦片肉眼校验**：
     - `零思考强制执行`：显示 **`100.0%`**（冰青高亮），副标题提示 `提速 15.2x · Token -70%`；
     - `二分自愈成功率`：显示 **`100.0%`**（冰青高亮），副标题显示真实成功数比率；
     - `双门禁预切片`：显示真实拦截次数（如 `4 次拦截`），副标题标明阈值 `>4000字 / >25条`；
     - `空返回拦截 & 安全切分`：显示真实空返回清零数（如 `4 空返回清零`），副标题标明 `防爆分片 (上限 3000 字)`；
  4. **左侧四大门禁体系结构走查**：
     - 确认 4 项防御机制全部处于 `Active` 状态：
       1. `前置条数/字数双门禁 (Pre-Slice Gate)`
       2. `零思考硬开关强制锁定 (Zero-Thinking Guard)`
       3. `截断物理阻断与二分并发切片 (Bisection Heal)`
       4. `入库防爆安全切分 (Safe Memory Chunker)`
  5. **右侧实时演练试验台 (Live Drill Test Bench) 交互走查**：
     - 点击场景芯片 `长对话截断自愈`（或 `双门禁超限预切片`、`超长记忆字段防爆`）；
     - 点击下方湛蓝操作按钮 **`触发长文本截断与二分自愈演练 (Trigger Heal Drill)`**；
     - 观察下方黑色终端容器在 100ms 内即刻回显演练结果：
       - 状态指示：`STATUS: HEALED_SUCCESS`（冰青加粗）；
       - 拦截证据：`双门禁拦截: 已触发 (PRE_SLICED)`；
       - 二分子任务：`左 4 条 / 右 4 条`；
       - 零思考强制：`100% (Thinking=False)`；
       - 收益度量：`Token 节约率: 72.4%`、`端到端提速: 15.2x`、`空返回清零: 1 次`。
- **合格标准**：点击后 100ms 内反馈自愈结果，终端输出自洽，遵循 NO GREEN EVER 🚫。

---

### 📌 9. [v1.5.22] 工程成果全面稳固与奥卡姆剃刀瘦身 (`Card-Hardening-FileLimits-Decoupling-CockpitTabs-BackgroundIdle`)
- **直达入口**：[http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval)
- **Git Tag 锚定**：`v1.5.22`
- **操作步骤**：
  1. 打开页面 [http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval)；
  2. **肉眼观察 Tab 导航**：页面顶部呈现 4 项高密中性风格 Tabs：
     - `检索与结果 (Search & Results)`
     - `BM25 词法混合 (BM25 Hybrid)`
     - `zg 本地语义搜索 (zg AST Search)`
     - `HG-RAG 分层指南针 (HG-RAG Compass)`
  3. 点击各 Tab 自由切换，单屏聚焦对应检索试验台，彻底告别纵向 4 屏瀑布流死刷；
  4. **后台休眠验证**：打开浏览器开发者工具 (F12) Network 标签页，切换浏览器 Tab 到其他页面 30 秒，确认 `metrics`/`stats`/`observer` 请求物理断流停止轮询，切回前台时无缝恢复；
  5. **单文件规模验证**：运行 `wc -l` 验证全项目治理文件（`bisection_heal.py` 395 行, `retrieval-results.tsx` 191 行, `harness-failure-whitelist-radar.tsx` 270 行, `gatekeeper-decision-drawer.tsx` 302 行），全量严格在 100~300 行黄金甜点区，无任何文件超过 400 行。
- **合格标准**：Tab 切换秒级聚焦，单屏展示无瀑布流，后台休眠断流，遵循 NO GREEN EVER 🚫。

---

### 📌 10. [v1.5.33] 存量历史碎片三门并联结晶归纳器与不可变事实 SSOT 熔炼 (`Card-Memory-EntropyCrystallizer-TriGate`)
- **直达入口**：[http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval)（点击顶部 Tab「三门结晶与不可变事实」）
- **Git Tag 锚定**：`v1.5.33`
- **操作步骤**：
  1. 打开页面 [http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval)；
  2. **切换 Tab**：点击顶部 Tab「**三门结晶与不可变事实**」；
  3. **顶部 4 大度量瓦片肉眼核验**：
     - `已熔炼不可变事实`：显示真实在籍晶体数量（如 `1 晶体`）；
     - `存量物理净减熵`：显示物理减少的活跃节点数（如 `+4 节点净减`，冰青色高亮）；
     - `三门硬门禁拦截率`：显示客观拦截比率与把关数据；
     - `三门并联硬准则`：清晰提示 `条数 ≥5 · 相似 >0.75 · 冷却 ≥24h`。
  4. **三门实时演练试验台交互走查**：
     - 切换到预设场景「5条端口规范碎片 (三门全过)」，点击「测试三门」，观察三门芯片全部呈现冰青色通过标识；
     - 点击「熔铸事实晶体」，回显区域实时渲染：
       - `+4 节点物理净减`；
       - `L0 核心公理`：“对外唯一服务端口物理收口为 1933。”；
       - `L1 版本与证据链`：明确版本 `version_range: ">= v1.5.00"`，5 条源碎片全部自动标记为 `superseded`；
       - `L2 负向排斥哨兵`：明确列出已废弃旧模式与排斥词（如 `1936`）。
     - 切换到预设场景「3条未冷却热碎片 (门禁拦截)」，点击「测试三门」，观察 Gate 1 与 Gate 3 触发琥珀色拦截告警，明确提示未满 24h 冷却期与条数不足。
### 📌 11. [v1.5.34] Codex 级主动上下文治理与历史独立分仓 (`Card-Context-ActiveNotesAndHistory`)
- **直达入口**：[http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval)（点击顶部 Tab「主动上下文与历史分仓」）
- **Git Tag 锚定**：`v1.5.34`
- **操作步骤**：
  1. 打开页面 [http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval)；
  2. **切换 Tab**：点击顶部 Tab「**主动上下文与历史分仓**」；
  3. **顶部 4 大度量瓦片肉眼核验**：
     - `常驻上下文节省率`：显示高达 `96%`~`97%` 的 Token 节省（冰青高亮）；
     - `历史分仓留存`：显示分仓存储的原始长轮次对话流条数；
     - `无损保真率`：显示 `100%`（零失真 Compaction，彻底切除有损全局压缩）；
     - `调阅响应延迟`：显示 `< 4ms`（基于 SQLite FTS5+WAL 毫秒级极速召回）。
  4. **双栏 50/50 独立分仓视图核验**：
     - **左侧 Active Notes (高密常驻主上下文)**：
       - 查看当前核心目标 (Active Goal)、当前阶段 (Current State)；
       - 查看运行硬性红线与约束 (Working Constraints) 胶囊列表；
       - 查看已确认不可变物理事实 (Discovered Facts) 清单；
     - **右侧 History 独立分仓 (按需主动调阅)**：
       - 点击「窗口浏览 (list_windows)」，观察无损保真的历史消息流（包含 Turn 轮次、角色与时间戳）；
       - 点击「精准检索 (search_history)」，在输入框中输入 `ERR_PORT_CONFLICT` 或 `1933` 或 `ConfigDict`，点击检索；
       - 观察历史命中记录实时高亮展示，Rank 打分与精确匹配内容完整无缺，零失真。

---

### 12. ⚡ SkillZip 写入即压缩与门禁试验台 (SkillZip Engine & Gate) (Card-Skill-ZipOnWrite-ContractualCompression / v1.5.35)

- **直达链接**：[http://127.0.0.1:1933/studio/skills](http://127.0.0.1:1933/studio/skills)
- **验证目的**：吸收阿里/浙大/杜克《SkillZip》思想，验证自进化技能 0-Rollout 确定性契约化重构、Explain Once, Reference Everywhere (EORE) 规则去重与 1.6~1.9x 写入门禁，彻底终结自进化技能 5.2 倍膨胀的“复读机死因”。
- **30秒操作步骤与看点**：
  1. **进入技能中心并切换至 SkillZip 视图**：
     - 打开浏览器访问 `http://127.0.0.1:1933/studio/skills`；
     - 在页面上方视图切换栏中，点击高亮切换至「⚡ SkillZip 写入即压缩与门禁」。
  2. **4 大核心 KPI 指标瓦片核验**：
     - `平均压缩率`：显示 `30.5% ~ 31.4%` (冰青色，目标达成 $\ge 30\%$)；
     - `契约保真度`：显示 `100.0%` (六元组强类型校验，零有损失真)；
     - `0-Rollout 延迟`：显示 `< 5ms` (极速确定性动态规划，零 LLM 额外调用开销)；
     - `写入门禁状态`：显示 `1.9x Ceiling` (锁定种子长度，防膨胀恶化)。
  3. **预设切换与门禁检测 (Zip Gate Check)**：
     - 点击预设按钮「阿里自进化膨胀技能 (5.2x 复读机)」；
     - 点击「🛡️ 写入即门禁检测」，下方立即弹出告警条，提示技能超出 1.9x 门禁，推荐动作标为 `TRIGGER_ZIP` (琥珀色)；
     - 点击预设「极客精简基准技能 (Seed Baseline)」，再次点击门禁检测，显示 `PASS` (湛蓝/冰青色)。
  4. **0-Rollout 契约化压缩演练 (Contractual Compression)**：
     - 切换回「阿里自进化膨胀技能」，点击「⚡ 0-Rollout 契约压缩」；
     - 右侧瞬间（< 5ms）回显规范化 Markdown，显示：
       - `减熵 30.5%`，节省 `~110 Tokens`；
       - 六元组标签胶囊：`I 接口: 已对齐`, `W 工作流: 5 步`, `P 协议: 3 项`, `R 规则: 4 条 (已去重)`, `C 契约: 3 条 (100%保真)`, `E 证据: 2 条`；
       - 对比左右两侧：原技能中重复 3 次的 "Always verify that no secrets or API keys..." 与重复 2 次的 "NO GREEN EVER" 被自动去重提升至统一作用域，客套废话被完全剔除。
  5. **负向红线排查**：全页面无任何绿色 (NO GREEN EVER 🚫)，最小字号严格 $\ge 12\text{px}$，数字等宽 `tabular-nums`。
- **合格标准**：0-Rollout 压缩率 $\ge 30\%$，契约保真度 100%，写入门禁准确阻断膨胀技能。

---

### 13. ⚡ 前门自动泊车与反熵去噪准入门禁 (Valet Ingestion Engine & Anti-Entropy Gate) (Card-Memory-ValetIngestion-AntiEntropyGate / v1.5.36)

- **直达链接**：[http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval)
- **验证目的**：验证前门极速物理泊车交接 (<10ms) 机制、HTTP 202 Accepted 票据凭证与后台异步准入门禁去噪去重，彻底消除大文本入库对前门通道的阻塞，达成稳定反熵增准入。
- **30秒操作步骤与看点**：
  1. **进入检索座舱并切换至泊车 Tab**：
     - 打开浏览器访问 `http://127.0.0.1:1933/studio/retrieval`；
     - 在顶部 Tab 栏中点击切换至第 7 项「⚡ 前门泊车与反熵准入」。
  2. **4 大核心 KPI 指标瓦片核验**：
     - `前门交接平均时延`：显示 `< 5.00ms` 或真实测量值（目标达成 $< 10\text{ms}$，冰青色 `cyan-500`）；
     - `累计泊车请求`：显示真实请求次数（HTTP 202 Accepted）；
     - `反熵去重准入率`：显示百分比（去噪合流率，冰青色 `cyan-500`）；
     - `待入库异步队列水深`：显示当前排队条数，标明 `空闲自愈` 或 `并发消化中`。
  3. **预设切换与极速交接 (Fast Handover)**：
     - 点击预设按钮「前门极速入库与物理泊车」；
     - 点击「⚡ 极速交接 (Handover)」，下方末次前门网络回显即刻显示 `< 10ms`；
     - 右侧「泊车票据流水」瞬时弹出一张新票据，状态由 `accepted` 流转至 `parked` (湛蓝/冰青色)。
  4. **冗余去重门禁演练 (Dedup Barrier)**：
     - 点击预设按钮「冗余碎片静默合并与反熵门禁」；
     - 再次点击「⚡ 极速交接」，观察反熵门禁识别重复内容，票据详情显示静默合并或去噪，KPI 卡片去重指标实时统计；
  5. **批处理多段投递验证**：
     - 点击预设按钮「批量知识并发交接与队列吞吐」，验证批处理并发签发票据与队列平稳消费能力。
  6. **负向红线排查**：全页面无任何绿色 (NO GREEN EVER 🚫)，最小字号严格 $\ge 12\text{px}$，数字等宽 `tabular-nums`。
- **合格标准**：前门时延 $< 10\text{ms}$，HTTP 202 异步票据签发保真，去重门禁稳定拦截/合流。



