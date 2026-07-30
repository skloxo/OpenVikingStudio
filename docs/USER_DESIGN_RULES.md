# 全局通用第一性原理与 TideTrading 设计/代码哲学 (USER_DESIGN_RULES.md)

> 本文档汇集了用户指导的核心哲思、奥卡姆剃刀原则与 TideTrading 经典工程/视觉设计哲学。所有开发代码与 UI 迭代必须 100% 强制遵循。

---

## 🏛️ 一、第一性原理与代码哲学 (First Principles & Coding Philosophy)

1. **奥卡姆剃刀原则 (Occam's Razor)**：
   - **如无必要，勿增实体**。严禁过度工程化（例如：避免为了简单的状态刷新去搞复杂的 WebSocket/全双工长连接机制）。
   - **优先采用极简黄金平衡解法**：按需焦点感知 + 60s 惰性微拉取，离开视口即 100% 挂起，零无用资源消耗。

2. **业务因果层次与第一性布局 (Hierarchy & Sequence Rule)**：
   - 遵从物理逻辑与因果关系：**上层总领视角在前（左），下层拆分解构视角在后（右）**。
   - 例如：先有上层业务单元 **【任务队列】**，后由其拆分解构出下层具体步骤 **【工序队列】**，因此【任务队列】必须放在左侧，【工序队列】放在右侧。

3. **数据真实性铁律 🔴 (Absolute Data Integrity)**：
   - 100% 真实后端数据驱动，**绝对禁止**伪造、硬编码 mock 或广播共享假数字。
   - 缺乏拆分 API 时，宁可优雅显示 `--`，也决不乱传假数据。遇到问题必须实查证据（如进程 `ps aux`）。

4. **领域通用语言 100% 严谨一致 (Ubiquitous Language Precision)**：
   - 统一领域专有名词，**严禁同义词混用**（例如统一使用“任务 Task”，绝对禁止在同一页面与“工单 Work Order”混用）。
   - 切换中文即 **100% 全中文**，切换英文即 **100% 全英文**，严禁中英文夹杂。

5. **通俗化直白表达案例 (Golden Wording Examples)**：
   - 用 **`本地直连`** 替代 "实时 API 直连"
   - 用 **`网络远程`** 替代 "API 客户端"
   - 用 **`活跃 / 空闲 / 休眠`** 替代 "ACTIVE / SYNCED / IDLE"
   - 用 **`对接通道`** 替代 "VK 连接方式"

---

## 🎨 二、TideTrading 视觉与 UI 哲学 (Visual Identity Contract)

1. **视觉调性与极简主义 (Theme & Atmosphere - Zero Noise)**：
   - **"Hacker Terminal meets Bloomberg Terminal"**：高密数据折叠、硬朗极客质感、极高空间利用率。
   - **零阴影**：完全扁平化，**绝对禁止 `box-shadow`**。
   - **零装饰性杂质**：**严禁放置无信息增量的纯装饰性 Icon**（如 KPI 卡片角标图标）与**伪状态 Badge**（如已有表格“错误数”列，严禁在卡片角标放置无用的“● 正常”标签）。
   - **零切换折叠 (No Tab Switching)**：拒绝对立面板之间搞 Tab 切换（“切来切去”），放不下直接采用 50/50 独立卡片并排放置。

2. **卡片像素级底边对齐铁律 (Pixel-Perfect Alignment & Pinned Bottom)**：
   - 严禁滥用 `justify-between` 人为拉开数据行垂直间距形成空缺；
   - 并排双卡片外层容器统一使用 `items-stretch h-full` 确保物理高度齐平；
   - 底部汇总行（如 `合计 TOTAL`）必须赋予 `mt-auto` 硬性固定于卡片最底端，确保不同数据行数的卡片底部汇总行在同一水平线上平齐。

3. **4px 微圆角 Token (4px Radius Standard)**：
   - 容器/卡片面板：统一收紧为 **4px (`rounded` / `rounded-md`)**
   - 按钮/输入框：收紧为 **3-4px (`rounded-sm`)**
   - 小 Tag/Badge：收紧为 **2px (`rounded-xs`)**

4. **等宽数字与排版 (Tabular Figures Monospace)**：
   - 所有数值、时间戳、百分比列强制开启：
     ```css
     font-variant-numeric: tabular-nums;
     font-family: 'JetBrains Mono', 'Fira Code', monospace;
     ```
   - 保证数据刷新时无任何平移跳动与布局抖动。

5. **极简性冷淡调性与三态色彩铁律 🔴 (Cold Minimalist & Trinary Color Rules)**：
   - **冷静沉稳性冷淡风**：拒绝五彩斑斓的营销风或过载修饰，专注高冷静数据观测。
   - **绝对禁止使用绿色 🚫 (NO GREEN EVER)**：系统全界面严禁出现绿色系列配色。
   - **严格限定三态语义色彩**：
     - **正向 / 良好健康** (`positive`) ➔ 冰青 / 湛蓝 (`cyan-500/10 text-cyan-600 dark:text-cyan-400`)
     - **负向 / 异常问题** (`negative`) ➔ 玫瑰红 (`rose-500/10 text-rose-600 dark:text-rose-400`)
     - **中性 / 静态指示** (`neutral`) ➔ 沉静哑光灰 (`bg-muted/40 text-muted-foreground`)

---

> 只要是本项目代码开发，必须 100% 遵循上述通用哲学！
