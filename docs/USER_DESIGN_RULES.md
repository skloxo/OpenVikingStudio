# 全局通用第一性原理与 TideTrading 设计/代码哲学 (USER_DESIGN_RULES.md)

> 本文档汇集了用户指导的核心哲思、奥卡姆剃刀原则与 TideTrading 经典工程/视觉设计哲学。所有开发代码与 UI 迭代必须 100% 强制遵循。

---

## 🏛️ 一、第一性原理与代码哲学 (First Principles & Coding Philosophy)

1. **奥卡姆剃刀原则 (Occam's Razor)**：
   - **如无必要，勿增实体**。严禁过度工程化（例如：避免为了简单的状态刷新去搞复杂的 WebSocket/全双工长连接机制）。
   - **优先采用极简黄金平衡解法**：按需焦点感知 + 60s 惰性微拉取，离开视口即 100% 挂起，零无用资源消耗。

2. **数据真实性铁律 🔴 (Absolute Data Integrity)**：
   - 100% 真实后端数据驱动，**绝对禁止**伪造、硬编码 mock 或广播共享假数字。
   - 缺乏拆分 API 时，宁可优雅显示 `--`，也决不乱传假数据。遇到问题必须实查（如进程 `ps aux`）证据。

3. **纯净 i18n 多语言表达**：
   - 切换中文即 **100% 全中文**，切换英文即 **100% 全英文**，严禁中英文夹杂与无意义硬编码英文描述。
   - 主标题精简干练，副标题负责说明备注。

4. **通俗化直白表达案例 (Golden Wording Examples)**：
   - 用 **`本地直连`** 替代 "实时 API 直连"
   - 用 **`网络远程`** 替代 "API 客户端"
   - 用 **`活跃 / 空闲 / 休眠`** 替代 "ACTIVE / SYNCED / IDLE"
   - 用 **`对接通道`** 替代 "VK 连接方式"

---

## 🎨 二、TideTrading 视觉与 UI 哲学 (Visual Identity Contract)

1. **视觉调性 (Theme & Atmosphere)**：
   - **"Hacker Terminal meets Bloomberg Terminal"**：高密数据折叠、硬朗极客质感、极高空间利用率。
   - **零阴影**：完全扁平化，**绝对禁止 `box-shadow`**。
   - **微细低透明度边框**：利用 `1px` 微透明边框分隔面板，而非厚重 Margin。

2. **4px 微圆角 Token (4px Radius Standard)**：
   - 容器/卡片面板：统一收紧为 **4px (`rounded` / `rounded-md`)**
   - 按钮/输入框：收紧为 **3-4px (`rounded-sm`)**
   - 小 Tag/Badge：收紧为 **2px (`rounded-xs`)**

3. **等宽数字与排版 (Tabular Figures Monospace)**：
   - 所有数值、时间戳、百分比列强制开启：
     ```css
     font-variant-numeric: tabular-nums;
     font-family: 'JetBrains Mono', 'Fira Code', monospace;
     ```
   - 保证数据刷新时无任何平移跳动与布局抖动。

4. **微动效约束 (Micro-Interactions)**：
   - 悬停与切换过渡必须在 **100~200ms** 内完成，禁止任何廉价缓动弹跳效果。

---

> 只要是本项目代码开发，必须 100% 遵循上述通用哲学！
