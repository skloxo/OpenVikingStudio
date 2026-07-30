# AGENTS.md - OpenViking Studio Project Instructions

## Mandatory First Step
Before making ANY modification, analysis, or feature iteration in this workspace, you MUST:
1. Read `REFACTORING_GUIDE.md` completely.
2. Follow the **Native React Source Build** workflow (`src/` ➡️ `pnpm run build` ➡️ `./dist`).
3. NEVER write imperative DOM injection scripts in `server.js`.
4. Keep port 1933 (Production) 100% untouched until explicit user release approval.
5. **NO GREEN EVER & 冷静性冷淡三态配色铁律**：
   - 严禁在全系统 UI 中使用任何绿色 (`emerald` / `green`)；
   - 采用极简“性冷淡风”掌控冷静观测视角，全界面严格限定三态语义色彩：
     - **正向 / 良好** ➔ 冰青 / 湛蓝 (`cyan-500/10 text-cyan-600 dark:text-cyan-400`)
     - **负向 / 异常** ➔ 玫瑰红 (`rose-500/10 text-rose-600 dark:text-rose-400`)
     - **中性 / 静态** ➔ 沉静哑光灰 (`bg-muted/40 text-muted-foreground`)

---

## 🏛️ 三大底层工程哲学 (Three Core Philosophies)

1. **第一性原理 (First Principles)**：回归事物最基础的物理与逻辑真理，剥离表面假象，直击核心物理根因。
2. **奥卡姆剃刀 (Occam's Razor)**：如无必要，勿增实体。切除一切人类认知与系统架构中不需要的冗余后缀、复杂包装与多余抽象。
3. **代码与 UI 系统的全生命周期“信达雅” (Faithfulness, Expressiveness, Elegance)**：
   - **【信】(Correctness & Domain Precision / 准确严谨)**：
     - *代码层*：逻辑严谨，尊重物理契约与类型系统，绝不掩盖异常或返回虚假 fallback；
     - * UI / 文案层*：忠于技术本质与行业惯例，CPU/RAM/Token/Vector 等专有名词绝不机械硬翻。
   - **【达】(Clarity & Expressiveness / 通顺自解释)**：
     - *代码层*：变量名、函数名与接口设计见名知意，自解释如流利的文学作品；
     - * UI / 文案层*：100% 契合人类开发者直觉与自然语言交互习惯。
   - **【雅】(Elegance & Clean Architecture / 极客雅致)**：
     - *代码层*：架构高内聚低耦合，遵循 DRY/KISS 原则，充满数学美与架构美；
     - * UI / 文案层*：极客精炼，视觉美感与文字品味兼备，拒绝死板机器直译。
