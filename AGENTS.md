# AGENTS.md - OpenViking Studio Project Instructions

## Mandatory First Step
Before making ANY modification, analysis, or feature iteration in this workspace, you MUST:
1. Read `REFACTORING_GUIDE.md` completely.
2. Read `docs/USER_DESIGN_RULES.md` completely.
3. Follow the **Native React Source Build** workflow (`src/` ➡️ `pnpm run build` ➡️ `./dist`).
4. NEVER write imperative DOM injection scripts in `server.js`.
5. **1933 生产环境绝对隔离与锁定 (STRICT PORT 1933 PROD LOCK - 铁律)**：
   - 研发迭代中的所有代码修改、样式调试与功能验证，**100% 只能在 1936 端口 (Vite Dev Server) 进行**。
   - **绝对禁止**在开发测试期间私自跑 `build` 覆盖 1933 端口（OpenViking Web Studio dist 目录）。
   - **只有当用户显式下达「验收完成」、「更新 1933」或「封板发版」命令时**，AI 才有权限执行打包并更新 1933！未获显式指令擅自动用 1933 属于严重违规！
6. **全局字体排版与最小字号硬性下限 (Global Typography Rule)**：
   - 全系统 **100% 物理禁用 `< 11px` 微字**（如 `text-[8px]`, `text-[9px]`, `text-[10px]` 彻底禁用）。字号下限锁定为 **`11px` (`text-[11px]`)**，高密基准字号为 **`12px` (`text-xs`)**。
7. **站在巨人的肩膀上 — 优先复用与持续跟进开源顶级轮子 (Upstream Wheel Reuse Rule)**：
   - **拒绝盲目手搓**：复杂需求（如技能压缩提炼、Prompt 自动优化、意图消歧等）必须优先检索与集成开源最高 Trust 成熟轮子（如 Microsoft `LLMLingua-2`、Stanford `DSPy`）；
   - **绝非一锤子买卖**：以依赖库形式引入，建立版本跟踪机制，长效吸收上游开源社区的算法演进成果。
6. **NO GREEN EVER & 冷静性冷淡三态配色铁律**：
   - 严禁在全系统 UI 中使用任何绿色 (`emerald` / `green`)；
   - 采用极简“性冷淡风”掌控冷静观测视角，全界面严格限定三态语义色彩：
     - **正向 / 良好** ➔ 冰青 / 湛蓝 (`cyan-500/10 text-cyan-600 dark:text-cyan-400`)
     - **负向 / 异常** ➔ 玫瑰红 (`rose-500/10 text-rose-600 dark:text-rose-400`)
     - **中性 / 静态** ➔ 沉静哑光灰 (`bg-muted/40 text-muted-foreground`)

---

## 🏛️ 三大底层工程哲学 (Three Core Philosophies)

1. **第一性原理 (First Principles)**：
   - 回归事物最基础的物理与逻辑真理，剥离表面假象，直击核心物理根因。
   - **因果与视角次序**：物理逻辑上主控/上层视角在前（左），下层拆分解构视角在后（右）。如先有【任务队列】后由其拆分解构出【工序队列】。

2. **奥卡姆剃刀 (Occam's Razor)**：
   - 如无必要，勿增实体。切除一切人类认知与系统架构中不需要的冗余后缀、复杂包装与多余抽象。
   - **切除视觉杂质与伪状态**：无信息增量的装饰 Icon 与伪状态 Badge（如已有“错误数”列就不另贴“正常”标签）一律切除。
   - **拒绝 Tab 切来切去**：高密观测面板拒绝切 Tab，优先采用双卡片并排一目了然。

3. **代码与 UI 系统的全生命周期“信达雅” (Faithfulness, Expressiveness, Elegance)**：
   - **【信】(Correctness & Domain Precision / 准确严谨)**：
     - *代码层*：逻辑严谨，尊重物理契约与类型系统，绝不掩盖异常或返回虚假 fallback；
     - * UI / 文案层*：领域专有名词 100% 连贯统一（如统一使用“任务”，绝不与“工单”混用），CPU/RAM/Token/Vector 等专有名词绝不机械硬翻。
   - **【达】(Clarity & Expressiveness / 通顺自解释)**：
     - *代码层*：变量名、函数名与接口设计见名知意，自解释如流利的文学作品；
     - * UI / 文案层*：100% 契合人类开发者直觉与自然语言交互习惯。
   - **【雅】(Elegance & Clean Architecture / 极客雅致)**：
     - *代码层*：架构高内聚低耦合，遵循 DRY/KISS 原则，充满数学美与架构美；
     - * UI / 文案层*：极客精炼，底边对齐与并排卡片通过 `mt-auto` 实现物理级底边平齐，拒绝随意与死板。

---

## 🔄 自动化双大脑评估与模型调度规则 (Dual-Brain Auto-Evaluation Rule)

当用户发出「换个模型评估」或请求对产出物/任务方案进行评估时：
1. **零繁琐 Prompt 驱动**：严禁要求用户手动输入重复的评估提示词。
2. **自动子代理调度**：自动并发分发独立的 `evaluator` 评估子代理，指定选用 **Claude Sonnet 4.6** 深度思考大模型。
3. **双视角/双大脑碰撞**：形成「主 Agent 实施视角 + Sonnet 4.6 独立评估视角」双大脑交叉验证。
4. **物理留痕**：评估结果自动生成并更新至 `docs/TASK_CARD_EVALUATION_REPORT.md`，并立即提交 Git Tag / Commit 留痕。
