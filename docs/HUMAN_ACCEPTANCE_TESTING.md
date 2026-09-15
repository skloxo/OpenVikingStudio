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

### 📌 [v1.5.19 待交付] HG-RAG 分层指南针拓扑与父子漫游检索 (`Card-Knowledge-HG-RAG-HierarchicalCompass`)
- **对应页面**：`/studio/retrieval` ➔ 第 5 块卡片 `HGRAGCompassCockpit`
- **功能预览**：
  - 四象限指南针漫游（北：大类上浮；南：子块下钻；东/西：同级兄弟横向漫游）；
  - 全路径血缘回填：彻底解决多跳实体丢失与大类上下文断层。
