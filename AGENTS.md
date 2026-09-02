# 🤖 OpenViking (VK) Agent 研发开局第一法则与通用规范 (AGENTS.md SSOT)

> **"The Single Source of Truth for Any Agent Entering This Codebase."**  
> 本文档是接手此项目的所有 Agent（主 Agent、子代理、跨会话 Agent）的**唯一开局入口与物理规则真相源**。

---

## 📌 一、 唯一真相源 3 大主文档矩阵 (Master SSOT Matrix)

全项目所有开发规范、演进蓝图与任务卡片物理收口在以下 3 个 Master 文档中，彻底禁止多头散落：

| 物理主文档 | 存放内容与功能 | 关联路径 |
|:---|:---|:---|
| 🤖 **`AGENTS.md`** | **唯一研发法则**：开发哲学、UI 视觉规范、绝对红线 | `.agents/AGENTS.md` |
| ��️ **`BLUEPRINT.md`** | **唯一研发大蓝图**：课题演进蓝图、多引擎压缩白皮书、基准测试 SOP | `.agents/BLUEPRINT.md` |
| 📋 **`REFACTORING_PLAN.md`**| **唯一任务卡片总看板**：所有活跃工单、课题卡片、已交付版本履历 | `REFACTORING_PLAN.md` |

---

## ⚡ 二、 研发四大绝对红线 (Non-Negotiable Baseline Rules)

1. **绝对禁止盲目修改代码 (Disaster Recovery First)**：
   - 任何敏感数据/记忆/架构重构，必须先做可行性与安全性评估；
   - 必须先调用 `VikingFS.commit` 物理快照，确保可通过 `snapshot/restore` 100% 回滚还原后再推进。

2. **奥卡姆剃刀 (Occam's Razor) 与极简降维**：
   - 切除一切过度工程；如无必要，勿增实体；
   - 拒绝复杂的动态定时器与冗余逻辑，优先采用极简入口拦截与离线后台蒸馏。

3. **性冷淡视觉克制铁律（详见第四节）**：
   - UI 中颜色是信号，不是装饰；默认一切中性，异常/告警才上色。

4. **全局最小字号硬性下限 (>= 11px)**：
   - 物理封杀禁用 text-[8px], text-[9px], text-[10px] 等微小字体；
   - 任何 Badge、属性说明字号硬下限为 11px (text-[11px])，高密正文统一使用 12px (text-xs)。

---

## 📜 三、 核心工程与设计哲学 (Engineering & Design Philosophy)

### 核心纲领一：站在巨人的肩膀上 —— 官方轮子优先

- **官方原生优先**：100% 优先基于官方底层原生 API 与算子。
- **按需补充构建**：官方没有提供时，才编写 Adapter 适配器。

### 核心纲领二：全生命周期"信、达、雅"

- **【信】准确严谨**：逻辑严谨，尊重物理契约；绝不掩盖异常、绝不返回虚假 fallback；专有名词全盘统一不混用。
- **【达】自解释通顺**：变量名/函数名见名知意；UI 文案契合开发者直觉，无拗口晦涩。
- **【雅】极客雅致无赘**：架构高内聚低耦合，遵循 DRY/KISS；UI 性冷淡克制，颜色有且仅有语义价值。

### 核心纲领三：代码复用与深度整合优先 (Reuse & Deep Consolidation Principle) ⭐

- **能复用必复用**：能复用的代码尽量复用，能复用的函数尽量复用，能复用的数据尽量复用，能复用的方法尽量复用。绝不换个写法随意创造新轮子，防止系统陷入紊乱。
- **深度对比后合并整合**：重构治理绝非盲目、匆忙、草率地删，而是必须**对比两套代码与方法的差异，取其精华深度整合**，收口为单一真相源 (SSOT)。
- **统一通信层与协议**：全前端统一收口 `ovClient`，严禁散落裸 `fetch` 和幽灵废弃客户端，杜绝 401 鉴权失效与伪造假数据 fallback。
- **双模态 MCP 智体桥梁物理收口 Monorepo (Dual-Mode MCP Architecture)**：
  - MCP 是各个 Agent 连接 Wiki 的唯一物理桥梁，必须物理收口在 Git Monorepo 仓库内与 Wiki 源码一同版本化迭代；
  - **1. 核心 MCP (Core MCP - 本地模式)**：用于本地主 Agent，全量 30+ 接口（全量记忆存储/检索、VikingFS 底层控制、技能生命周期治理、图谱拓扑、服务端快照与灾备）；
  - **2. 卫星 MCP (Satellite MCP - 远程模式)**：用于 3070 / Mac Studio 等远程卫星节点，精简安全模式（专注远程知识召回 `find`/`search`、经验提纯上报 `record_lesson`、网络抖动自愈与超时容错），物理隔离危险的底层运维与文件写指令。

### 核心纲领四：数据治理第一性原理与合并防丢铁律 (Data Governance SSOT Rule) ⭐

- **数据绝对安全（合并防丢）**：系统重构、升级或迁移过程中，**必须进行物理数据合并，绝对禁止删除数据**；
- **唯一物理真相源 (SSOT)**：彻底切除“内存单例 + 磁盘数据库”双轨割裂模型，全生命周期统一收口 SQLite 物理数据库；
- **绝对数据真实性**：100% 真实后端数据驱动，严禁伪造假数字或硬编码 Mock；接口缺失或异常时优雅展示 `--` 占位符。

### 核心纲领五：彻底切除 Agent 代码堆叠与掩盖式补丁 (Anti-Layering & Clean Codebase SSOT) ⭐⭐⭐⭐⭐

> **背景教训**：Agent 编写代码极易陷入“无脑代码叠代码”与“用新方法掩盖旧隐患”的恶性循环，导致代码库越来越脏、发包失效、深坑积聚。必须用以下四条硬核哲学彻底根治：

1. **绝对严禁无脑代码叠代码 (No Nested Layering)**：
   - 需求变更或新增功能时，**绝对禁止在原有臃肿代码外层无脑再套一层 Wrapper / Adapter**；
   - 必须深入原有逻辑，精简、重构并消除中间冗余层，让调用链路直截了当。
2. **绝对严禁写新方法掩盖旧隐患 (Root-Cause Fix, No Patching Over Flaws)**：
   - 遇到 Bug、异常或接口失效，**绝对禁止新写一个旁路函数/fallback 逻辑来“绕过”或“掩盖”原有问题**；
   - 必须直击物理根因，彻底修复或重写底层有缺陷的模块，根治隐患，严禁埋下隐蔽定时炸弹。
3. **公用组件与现成轮子四法则 (Shared Utilities & Wheel-First Logic)**：
   - **(a) 能用公用方法组件的，100% 优先使用公用方法组件**；
   - **(b) 有成熟现成轮子的，100% 优先使用成熟现成轮子与官方 API**；
   - **(c) 能复用的坚决复用，不能复用的寻找成熟轮子，严禁闭门造野生新轮子**；
   - **(d) 极致简洁（KISS 原则）**：能用 10 行写清楚的逻辑绝不写 50 行，代码必须自解释、干净利落、零杂质。

### 辅助工程原则

1. **第一性原理**：剥离表象假象，直击物理根因。
2. **奥卡姆剃刀**：如无必要，勿增实体；切除装饰噪音。
3. **$X / Y$ 物理进度度量与工序流转铁律 (Strict Completed/Total Progress Contract)**：
   - **$X$ 与 $Y$ 的唯一物理语义**：$X$ 严格代表【已完成数 (Completed Count)】，$Y$ 严格代表【总数 (Total Count)】；
   - **完成才 $+1$，进行中严禁预支 $+1$**：只有当某项计算/处理真正物理完成落地后，$X$ 才会 $+1$；在执行中 (Running) 阶段，$X$ 必须严格展示当前真实的已完成量（从 0 开始累计，如 1 节点任务在执行中严格展示 `0/1 节点`，严禁预支写成 `1/1 节点` 产生已完成假象）；
   - **$X = Y \iff 100\%$ 完成**：当且仅当 $X = Y$ 时，才代表该工序 100% 结束；
   - **自动流转下一工序**：当一道工序 $X = Y$ 结束时，系统必须立即自动流转到下一道未完成工序并展示下一工序的 $0/N$ 进度，严禁死卡在已完成工序名下。

---

## �� 四、 UI/UX 视觉规范 —— 性冷淡克制美学 SSOT

> **核心世界观**：界面是数据的容器，不是画布。颜色是信号，不是装饰。  
> 克制不是死气沉沉，而是把有限的视觉冲击力留给真正值得注意的事。

### 4.1 第一性原理：颜色的物理意义

```
颜色 = 信息 / 位置
```

- **颜色出现 = 用户需要注意** → 不需要注意的信息，绝不上色
- **正常运行的数据默认中性** → `text-foreground` + `bg-muted/20`，素净如纸
- **异常/告警才赋予颜色** → 颜色是例外，不是规则

### 4.2 色彩四态语义（偏离基线才上色）

核心判断：**颜色出现 ⟺ 指标偏离正常基线（无论正向还是负向）**

| 状态 | 判断条件 | Dark Mode | Light Mode |
|:---|:---|:---|:---|
| 🔵 **正向异常** | 指标超预期好（成功率极高、延迟极低、命中率亮眼） | `text-primary` | `text-primary` |
| ⚠️ **负向告警** | 指标劣化但可接受（延迟偏高、零结果率偏高） | `text-amber-400` | `text-amber-600` |
| 🔴 **负向异常** | 指标严重异常（错误、失败、宕机） | `text-destructive` | `text-destructive` |
| ⬜ **正常态（默认）** | 在预期范围内平稳运行 | `text-foreground`（无色） | `text-foreground`（无色） |

**严禁**：用颜色区分不同数据维度（如调用次数用蓝、token 用紫）。这是分类标签，不是偏差信号。  
**严禁**：给所有数字上色，不管是否偏离基线。颜色是偏差信号，不是装饰。

### 4.3 数据瓦片默认规范

```tsx
// 正确：中性，数据本身说话
<div className="flex flex-col rounded-lg border bg-muted/20 px-3 py-2">
  <span className="text-[11px] text-muted-foreground font-medium">标签</span>
  <span className="font-mono text-base font-bold text-foreground tabular-nums">值</span>
</div>

// 正确：有异常时才上色
<span className={cn(
  'font-mono text-base font-bold tabular-nums',
  isAbnormal ? 'text-amber-600 dark:text-amber-400' : 'text-foreground'
)}>

// 错误：把所有重要数字都染色（装饰噪音）
<span className="text-violet-700 dark:text-violet-400 font-bold">26,586</span>
```

### 4.4 明暗双主题容器规范

| 层级 | Dark Mode | Light Mode |
|:---|:---|:---|
| 页面画布 | #0d1117 (bg-background) | #f6f8fa |
| 一级卡片 | #161b22 | #ffffff |
| 数据瓦片/行悬停 | bg-muted/20 -> bg-muted/40 | 同 |
| 描边 | 1px solid #30363d (border) | 1px solid #d0d7de |
| 主文本 | #e6edf3 (text-foreground) | #1f2328 |
| 次级标签 | #8b949e (text-muted-foreground) | #656d76 |

完全扁平，无脏阴影，小微圆角统一 4px~6px (rounded-md)。

### 4.5 全局高密紧凑排版与字体规范 (High-Density Compact Layout & Typography Standard)

> **最高信息密度原则 (Maximum Information Density)**：界面是高吞吐量的数据仪表盘。在尽可能少的屏幕垂直与水平空间内，呈现尽可能多、高结构化、高对比度的有效信息，绝对拒绝无意义的大留白与过度 Padding。

| 内容类型 | 字体家族 | 字号规范 | 适用场景 |
|:---|:---|:---|:---|
| **微胶囊/紧凑徽章/辅助标注** | `font-sans` | **`11px` (`text-[11px]`)** (系统绝对硬下限，严禁 `<11px`) | 状态徽章、工序微胶囊、次级元数据 |
| **高密正文/数据行/按钮** | `font-sans` | **`12px` (`text-xs`)** (高密开发基准字号) | 列表行文案、操作按钮、卡片正文 |
| **数值/哈希/耗时/UUID** | `font-mono tabular-nums` | **`12px` (`text-xs`)** (等宽防抖动) | 计数、Token 数量、执行耗时、哈希指纹 |
| **卡片与区块标题** | `font-sans font-semibold` | **`14px` (`text-sm`)** | 一级/二级卡片标题、表头主标题 |

#### 高密紧凑落地量化指标 (High-Density Metrics SSOT)：
1. **容器内边距收敛**：基础卡片/面板内边距统一收敛为 **`p-3` 到 `p-3.5`**（最大不超过 `p-4`），彻底封杀 `p-6` / `p-8` 松散留白；
2. **列表行与表格行高压缩**：密集数据列表行纵向内边距统一收敛为 **`py-1` 到 `py-1.5`**，行与行间距统一使用 **`gap-1` 或 `gap-0.5`**；
3. **微胶囊/徽章紧凑贴合**：徽章与工序胶囊强制使用 **`px-1.5 py-px text-[11px] leading-none`**，严禁用 `px-3 py-1.5` 导致行高膨胀一倍；
4. **指示性图标与箭头轻量化**：流程箭头、状态圆点、辅助图标尺寸精准控制在 **`size-2.5` 到 `size-3.5`**，严禁 `size-5`/`size-6` 大图标撑破单行高度。

### 4.6 允许使用颜色的例外清单

以下场景且仅以下场景允许使用非中性颜色：

1. **语义三态着色**（告警/异常，见 4.2）
2. **交互焦点**：按钮 primary CTA，hover 状态，focus 环
3. **状态 Badge**：系统健康/不健康，一个小圆点 + 文字，bg-primary
4. **图表系列色**：多条折线/柱状图区分不同系列时，允许多色但需成套、有序
5. **代码语法高亮**：编辑器内的 token 着色

**任何不在此清单内的颜色使用，视为装饰噪音，必须删除。**

### 4.7 布局原则与空间吞吐量

- **50/50 独立卡片并排**：`grid grid-cols-1 md:grid-cols-2 gap-3` 或 `gap-4`，拒绝 Tab 遮盖关键数据；
- **mt-auto 物理平齐**：并排卡片通过 `mt-auto` 实现底边汇总行 100% 物理绝对平齐，消除因单侧行高膨胀产生的长短脚高差；
- **拒绝 Tab 折叠**：核心运行态数据严禁折叠隐藏，放不下则 50/50 并排一目了然。

---

## 🔄 五、 干活必留痕流转 SOP

每完成一个迭代版本，必须完成以下三步，缺一不可：
1. **物理更新 package.json 版本号**；
2. **立即打 Git Tag 并推送**：`git tag -a v1.x.y -m "..." && git push origin v1.x.y`；
3. **物理更新 REFACTORING_PLAN.md**：标记 `[x] 已验收通过 ✅`，记录 Commit Hash 和交付清单。

---

## 🌐 六、 标准服务端口与极速运维矩阵 (SSOT Service Matrix)

| 端口/节点 | 角色与功能 | 常驻方式 | 极速管理指令 |
|:---|:---|:---|:---|
| **`1933`** | OpenViking 生产核心 (FastMCP / REST / `/studio`) | `systemd --user openviking.service` | `systemctl --user restart openviking` |
| **`1936`** | OpenVikingStudio Vite 热更开发测试环境 | `systemd --user openviking-studio-dev.service` | **`vk1936 restart`** / `vk1936 status` |
| **`13100`** | Mac Studio (M3 Ultra 256G) 远程算力节点 | FRP 穿透 (`8.129.0.26`) | `ssh -p 13100 fsk@8.129.0.26` |

---

## 🔬 七、 大模型准入与适配评估标准规范 (OpenViking Model Evaluator SSOT)

> **核心原则**：全系统严格禁止脱离真实工况的空泛评测，统一收口标准技能 [`openviking-model-evaluator`](file:///home/skloxo/aho/openclaw/project/.agents/skills/openviking-model-evaluator/SKILL.md)。

1. **统一思考分离契约**：所有候选大模型统一在“思考分离模式（Thinking Separation Mode）”下进行全量 5 场景评测（内部深度推导 + 外部 100% 裸 JSON / YAML 纯净正文）；
2. **标准答案（Ground Truth）与物理断言链**：
   - **S1 资源分级提纯 (L0/L1/L2)**：必须检出 3 大隐藏架构安全风险（MITM下载、暴力替换、时间戳缓存失效）；
   - **S2 检索意图推导与语义重写**：必须精准捕获 8 大核心系统实体与 3 路正交重写 Query；
   - **S3 跨会话主记忆提纯**：必须 100% 还原 5 大不可变工程事实（NO GREEN、429降级、Priority降序、别名分级展示、Git Tag）；
   - **S4 知识图谱关联推导**：必须推导出标准因果拓扑与耦合维度（`depends_on` + `traffic_routing`）；
   - **S5 技能规范审计与修复**：必须覆盖 4 大硬性配置参数并输出标准 YAML Frontmatter；
3. **官方基准线 (Golden Baseline)**：
   - **欧尼 (Ornith 1.5 35B 本地实机)**：综合得分 **`94.0 分`**（格式 25/25，标准答案命中 40/40 满分，纯净度 15/15 满分，总耗时 63.32s）。


