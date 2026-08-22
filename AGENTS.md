# AGENTS.md - OpenViking Studio Project Instructions

## Mandatory First Step & Standard Iteration SOP (全流程迭代铁律)

所有研发迭代必须 100% 严格遵守以下标准化 SOP：
1. **源码开发与 1936 测试验证**：所有修改必须在 Monorepo 源码上进行，通过 Vite HMR 实时热更新至 1936 端口进行调试，跑通全量白盒自动化测试 (`pytest`)。
2. **输出人肉验收指南并等待用户 Sign-off 🛑**：向用户输出包含 UI 走查路径、curl 测试命令、pytest 测试集与预期输出的《人肉验收清单》。**严禁在用户明确回复“通过/执行发布”前私自部署 1933 或发布 Git Tag**！
3. **用户 Sign-off 后构建 1933 生产并发布 Tag**：在用户确认验收通过后，方可从源码执行生产构建 (`npm run build`) 并部署至 1933 正式环境，自动自增 Patch 版本号 Z (`x.y.Z` ➔ `x.y.Z+1`) 并打标推送 Git Tag。
4. **任务卡片即时闭环与体外大脑归档**：在 `REFACTORING_PLAN.md` 中将其状态更新为 `[x] 已验收通过 ✅`，并自动调用 `openviking_record_evolution_lesson` 归档至体外大脑。
5. **模型拓扑解耦 SSOT 守则**：严格区分几何维度 (4096)、上下文 n_ctx (4096) 与切片窗口 (1500)，唯一真相源收口于 `docs/MODEL_ARCHITECTURE_SPEC.md`。
6. **严禁在 `server.js` 中写入命令式 DOM 注入脚本**。
---

## 🏛️ OpenViking 全局设计与工程哲学 (7 大核心柱石)

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

4. **绝对数据真实性 (Absolute Data Integrity)**：
   - 100% 真实后端数据驱动，**绝对禁止**伪造假数字或硬编码 mock。无 API 时优雅显示 `--`。

5. **三态语义色彩与 NO GREEN EVER 铁律**：
   - 严禁在全系统 UI 中使用任何绿色 (`emerald` / `green`)；
   - 采用极简“性冷淡风”掌控冷静观测视角，全界面严格限定三态语义色彩：
     - **正向 / 良好** ➔ 冰青 / 湛蓝 (`cyan-500/10 text-cyan-600 dark:text-cyan-400`)
     - **负向 / 异常** ➔ 玫瑰红 (`rose-500/10 text-rose-600 dark:text-rose-400`)
     - **中性 / 静态** ➔ 沉静哑光灰 (`bg-muted/40 text-muted-foreground`)

6. **全局高密紧凑排版与字体规范 (High-Density Compact Layout & Typography Standard)**：
   - **最高信息密度原则**：在尽可能少的屏幕垂直与水平空间内，展示尽可能多、高结构化、高对比度的有效信息，绝对拒绝无意义的上下大留白与松散 Padding。
   - **绝对封杀 `< 11px` 微字**：全系统 **100% 物理禁用 `< 11px` 微字**（如 `text-[8px]`, `text-[9px]`, `text-[10px]` 彻底禁用）。字号下限锁定为 **`11px` (`text-[11px]`)**，高密正文与按钮基准字号为 **`12px` (`text-xs`)**，数值/哈希/耗时统一使用 **`font-mono tabular-nums text-xs`**。
   - **高密紧凑落地量化指标 (High-Density Metrics SSOT)**：
     - *容器内边距*：基础卡片/面板内边距收敛为 **`p-3` 到 `p-3.5`**（最大不超过 `p-4`），彻底切除 `p-6` / `p-8` 松散膨胀；
     - *列表行与表格行高*：密集数据列表行纵向内边距统一收敛为 **`py-1` 到 `py-1.5`**，行与行间距使用 **`gap-1` 或 `gap-0.5`**；
     - *微胶囊/徽章紧凑贴合*：徽章与工序胶囊强制使用 **`px-1.5 py-px text-[11px] leading-none`**，严禁使用 `px-3 py-1.5` 将单行撑大一倍；
     - *指示性图标与箭头轻量化*：流程箭头、状态圆点、辅助图标尺寸精准控制在 **`size-2.5` 到 `size-3.5`**，严禁大图标撑破单行高度；
     - *左右 50/50 独立卡片底边对齐*：左右并排卡片通过 **`mt-auto`** 确保底边汇总行 100% 物理绝对平齐，消除长短脚高差。

7. **站在巨人的肩膀上 — 组件化嵌入与非侵入式适配原则 (Upstream Wheel Reuse & Adapter Principle)**：
   - **敬畏第一性原理 (Respect Upstream Core)**：拒绝闭门造车手搓劣质轮子；对开源社区最高 Trust 组件的核心数学算法与推理模型保持敬畏，不乱改其核心第一性逻辑；
   - **专精适配层 (Dedicated Viking Adapter)**：绝不机械裸用第三方开源包，必须在其外层封装针对当前项目的专用 Adapter 适配器，强制保护业务 Schema（如 YAML Header、代码块、系统约束）；
   - **硬核超参数固化保护 (Hardcoded Model Tuning Safeguard)**：针对引入的特定模型组件（如微软 LLMLingua-2），必须将调优后的超参数（`rate=0.50` 兼顾命令与压缩, `threshold=0.35` 保护否定词/控制词, 正则物理冻结 YAML 头部 `^---[\s\S]*?---` 与代码块 ```` ```[\s\S]*?``` ````）硬编码固化至项目源码与默认配置中，防止任何人拉取代码后用泛化默认参数搞坏技能；
   - **编排与优雅自愈 (Orchestration & Fallback)**：将第三方开源轮子作为解耦组件融入系统统一生命周期（同启动、同关闭）；编排层必须设置异常熔断兜底，一旦组件报错自动降级，保障主服务 100% 稳如磐石。

---

## 🔄 自动化双大脑评估与模型调度规则 (Dual-Brain Auto-Evaluation Rule)

当用户发出「换个模型评估」或请求对产出物/任务方案进行评估时：
1. **零繁琐 Prompt 驱动**：严禁要求用户手动输入重复的评估提示词。
2. **自动子代理调度**：自动并发分发独立的 `evaluator` 评估子代理，指定选用 **Claude Sonnet 4.6** 深度思考大模型。
3. **双视角/双大脑碰撞**：形成「主 Agent 实施视角 + Sonnet 4.6 独立评估视角」双大脑交叉验证。
4. **物理留痕**：评估结果自动生成并更新至 `docs/TASK_CARD_EVALUATION_REPORT.md`，并立即提交 Git Tag / Commit 留痕。
