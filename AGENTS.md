# AGENTS.md - OpenViking Studio Project Instructions

## Mandatory First Step
Before making ANY modification, analysis, or feature iteration in this workspace, you MUST:
1. Read `REFACTORING_GUIDE.md` completely.
2. Read `docs/USER_DESIGN_RULES.md` completely.
3. Follow the **Native React Source Build** workflow (`src/` ➡️ `pnpm run build` ➡️ `./dist`).
4. NEVER write imperative DOM injection scripts in `server.js`.
5. Keep port 1933 (Production) 100% untouched until explicit user release approval.
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
