# 👁️ OpenViking 人工肉眼走查与验收清单 (Human Acceptance Testing Manifest)

> **文档定位 (SSOT)**：本文件是人类开发者进行人工功能走查、UI 肉眼检验与验收交付的**唯一物理指南**。  
> 每次功能迭代交付后，必须同步在此追加【30 秒肉眼用例】，确保无需翻阅代码即可通过浏览器与直观交互完成全量验证。

---

## 🌐 验收环境与核心中枢直达

- **Studio 控制台地址**：[http://127.0.0.1:1933/studio](http://127.0.0.1:1933/studio)
- **信息治理与检索总控台**：[http://127.0.0.1:1933/studio/retrieval](http://127.0.0.1:1933/studio/retrieval)
- **后台服务守护进程**：`systemd --user openviking.service`（监听本地端口 `1933`）
- **视觉硬性红线排查**：
  - 🚫 **绝对严禁出现任何绿色 (NO GREEN EVER)**（良好默认湛蓝/冰青 `cyan-500`，中性灰底色，告警琥珀 `amber-400`，异常玫瑰红 `rose-500`）；
  - 🚫 **字号物理下限 $\ge 12\text{px}$ (`text-xs`)**，微字彻底封杀；
  - 🚫 **数值列统一使用等宽字体 `font-mono`**。

---

## 📋 模块走查用例清单 (逐版本汇总)

### 📌 [v1.5.16] BM25 + 稠密向量双流混合检索座舱 (`Card-Retrieval-BM25Hybrid`)
- **对应页面**：`/studio/retrieval` ➔ 顶部第 2 块卡片 `BM25HybridCockpit`
- **Git Tag 锚定**：`v1.5.16` (`4dc01fc3c`)
- **操作步骤**：
  1. 打开 `/studio/retrieval`，观察第二块卡片；
  2. 检查 4 块核心 KPI 瓦片：
     - 倒排索引规模：显示真实文档数（`1,279` 篇）；
     - 精确符号提权数：显示 `≥ 1`；
     - 双流重合率：显示真实百分比（`~4.8%`）；
     - 融合延迟：显示单调时钟开销（`< 2ms`）；
  3. 点击预设芯片 `is_heartbeat_session` 或 `VikingFS.commit`：
     - 观察左右双流分栏输出，左侧为 SQLite FTS5 BM25 词法结果，右侧为 Dense Vector 结果；
     - 观察融合结果列表，各条目具有 `[hybrid]`、`[sparse_only]` 或 `[dense_only]` 来源角标。
- **合格标准**：无假数据 `--`，无控制台报错，无绿色元素，点击芯片 100ms 内即刻回显。

---

### 📌 [v1.5.17] zg 端侧代码语义检索与分级懒加载座舱 (`Card-Retrieval-LocalFirst-zgSemanticSearch`)
- **对应页面**：`/studio/retrieval` ➔ 第 3 块卡片 `ZGSearchCockpit`
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
     - 点击 `全量 (depth=2)`，观察动态加载展开完整代码块；
     - 点击 `元数据 (depth=0)`，观察仅回显行号跨度与文件路径，Token 消耗大幅降低。
- **合格标准**：分级切换流畅无抖动，AST 符号精确定位到真实 Python 文件行号跨度。

---

### 📌 [v1.5.18] RAG 约束验证与主动弃答门禁 (`Card-RAG-Abstention-ZeroHallucination-Pipeline`)
- **对应页面**：`/studio/retrieval` ➔ 第 4 块卡片 `RAGAbstentionCockpit`
- **Git Tag 锚定**：`v1.5.18` (`11a0db824`)
- **操作步骤**：
  1. 页面滚动至 `RAGAbstentionCockpit` 卡片；
  2. 查看 4 块 KPI 瓦片：主动弃答率、平均置信度、MinHash 64-perm LSH 状态、门禁延迟；
  3. **出域防幻觉负向测试**：
     - 点击预设场景芯片 `超纲弃答 (无依据烘焙问题)`；
     - 观察下方立即弹出玫瑰红警示胶囊 **`[主动弃答 (ABSTAINED)]`**；
     - 弃答原因明确提示：`OUT_OF_DOMAIN: Zero semantic overlap between query and evidence`；
  4. **保真接地正向测试**：
     - 点击预设场景芯片 `保真可答 (OpenViking 端口与架构)`；
     - 观察弹出湛蓝认证胶囊 **`[准许回答 (GROUNDED)]`**；
     - 观察 MinHash 审计列表：故意重复的第 3 条证据被高密标记为 `[近重复 (相似 1.0)]`，并剔除出最终上下文，去重率从 3 块物理归并为 2 块。
- **合格标准**：超纲问题绝不盲猜回答（100% 触发弃答门禁），重复证据 100% 识别归并。

---

### 📌 [v1.5.19] HG-RAG 分层指南针拓扑与读写分离知识工程 (`Card-Knowledge-HG-RAG-HierarchicalCompass`)
- **对应页面**：`/studio/retrieval` ➔ 第 5 块卡片 `HGRAGCompassCockpit`
- **Git Tag 锚定**：`v1.5.19`
- **操作步骤**：
  1. 页面滚动至 `HGRAGCompassCockpit` 卡片（标题：`HG-RAG 分层指南针拓扑与读写分离知识工程`，版本胶囊：`v1.5.19`）；
  2. 查看 4 块 KPI 瓦片：
     - `拓扑节点总数`：`>= 8`
     - `根大类体系数`：`1`
     - `最大拓扑深度`：`Level 2`
     - `读写分离状态`：`Immutable Ready` (Serving Desk: 只读零锁)
  3. **四向指南针漫游测试**：
     - 初始停留在 `root_openviking`，观察 North(父类) 按钮置灰不可点击，South(下钻) 按钮呈冰青湛蓝高亮；
     - 点击 **`South (下钻)`**，观察锚点自动移动到 `ch_invariants` (企业级四大不可变式)；
     - 点击 **`East (后继)`**，观察横向平移至同级兄弟章节 `ch_retrieval` (双轨多引擎检索体系)；
     - 点击 **`South (下钻)`**，观察下钻至叶子实现 `sec_bm25` (BM25 FTS5 混合检索)；
     - 观察右侧 `自洽祖先血缘路径` 实时完整回显：`OpenViking 核心架构与知识中枢 > 双轨多引擎检索体系 > BM25 FTS5 混合检索`，大类全路径 100% 连贯，无任何断层丢失！
     - 点击 **`North (父类)`**，观察平滑上浮回退至 `ch_retrieval`。
  4. **快速锚点切换测试**：
     - 点击上方芯片 `zg 语义搜索`，观察一键直达，血缘路径与指针即刻同步刷新。
- **合格标准**：四向罗盘方向跳转自洽，叶子节点自洽挂载完整父级大类全路径，无任何卡顿或假数据。

---

### 📌 [v1.5.20] CPA 教师模型守卫拦截器与五大贯彻门禁看板 (`Card-Harness-CPATeacherGuard-GateParity-Desensitization`)
- **对应页面**：`/studio/harness-logs` ➔ `五大贯彻门禁看板`
- **Git Tag 锚定**：`v1.5.20`
- **操作步骤**：
  1. 打开浏览器访问 `http://localhost:1933/studio/harness-logs`；
  2. **顶部 KPI 总览走查**：
     - 查看第 3 块 KPI 瓦片 `物理贯彻门禁`：清晰渲染为 **`5 / 5 项已激活`**（冰青字号，非写死 4/4）；
     - 查看 Tab 导航栏：第 2 个 Tab 明确展示为 **`五大贯彻门禁看板`**；
  3. **五大门禁卡片走查**：
     - 点击 **`五大贯彻门禁看板`** Tab；
     - 依次向下滚动，逐一查看 5 块不可变式门禁卡片：
       1. `物理增量代码门禁 (Physical Diff Gate)`
       2. `测试视网膜反欺诈门禁 (Anti-Cheat Retina)`
       3. `防偷懒代码省略占位符栏栅 (Anti-Lazy Code Guard)`
       4. `生成与评估角色隔离 (Role Separation)`
       5. `CPA 教师模型守卫拦截器 (CPA Teacher Model Guard)`
     - 观察第 5 张门禁卡片：
       - 右上角状态胶囊展示 `Active Invariant`（冰青色）；
       - 说明文字：`毫秒级物理拦截工兵任务/批量并发滥用昂贵教师模型 (GPT/Claude)，确保教师零泄漏、工兵高吞吐`；
       - 规则标签列表：`block_expensive_models_in_workers`, `regex_audit_gpt_claude`, `require_explicit_teacher_flag`, `cost_aware_routing`；
  4. **全技能同步与安全合规走查**：
     - 访问 `http://localhost:1933/studio/skills`，所有技能卡片正常渲染；
     - `public/all_skills.json` 经 `_desensitize_text` 动态清洗，零 FRP 内网 IP、零密码明文。
- **合格标准**：
  - 顶部 KPI 动态回显 `5 / 5 项已激活`；
  - 5 大物理门禁卡片完整呈现，标签字号 $\ge 12\text{px}$，100% 遵循 NO GREEN EVER 🚫；
  - 安全扫描 4,280 追踪文件零秘钥泄漏。

---

### 📌 [v1.5.21] 记忆提取零思考与截断二分自愈座舱 (`Card-Extraction-ZeroThinking-BisectionHeal`)
- **对应页面**：`/studio/harness-logs` ➔ `零思考与二分自愈` Tab
- **Git Tag 锚定**：`v1.5.21`
- **操作步骤**：
  1. 打开浏览器访问 `http://localhost:1933/studio/harness-logs`；
  2. **Tab 导航走查**：
     - 点击第 4 个 Tab **`零思考与二分自愈`**；
     - 观察座舱顶部标题：`记忆提取零思考与截断二分自愈座舱 (Zero-Thinking & Bisection Heal)`，右侧版本角标 `v1.5.21 · P0`；
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
- **合格标准**：
  - 按钮点击后演练极速自愈并实时反馈，终端数据对齐；
  - 100% 遵循 NO GREEN EVER 🚫（正常中性灰，正向冰青 `cyan-400`）；
  - 字号物理下限 $\ge 12\text{px}$，单调时钟与排版无抖动。


