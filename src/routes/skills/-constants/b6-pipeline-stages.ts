// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export interface B6PipelineStage {
  id: string
  number: number
  name: string
  phase: 'ingestion' | 'closed_loop'
  badge: string
  desc: string
  engine: string
  invariants: string[]
  role: string
}

export const B6_PIPELINE_STAGES: B6PipelineStage[] = [
  // ── 前 6 阶：嗅探准入、自愈压缩与接缝裁决 ──
  {
    id: 'queue_claim',
    number: 1,
    name: '准入排队认领',
    phase: 'ingestion',
    badge: 'Atomic Claim',
    desc: '探针发现候选技能或增量场景，进入 SQLite 队列进行原子化无竞争认领。',
    engine: 'SkillIngestionStore',
    invariants: ['status: PENDING -> VALIDATING', 'atomic_sqlite_lock', 'zero_duplicate_enqueued'],
    role: 'Ingestion Daemon',
  },
  {
    id: 'ast_heal',
    number: 2,
    name: '语法校验自愈',
    phase: 'ingestion',
    badge: 'Auto Remediation',
    desc: 'AST 树深度校验 Frontmatter 结构；缺失 triggers、工具链或命名缺陷自动毫秒自愈补齐。',
    engine: 'SkillAutoRemediator & Validator',
    invariants: ['yaml_frontmatter_enforced', 'auto_patch_missing_triggers', 'zero_breaking_repair'],
    role: 'AST Healer',
  },
  {
    id: 'quality_gate',
    number: 3,
    name: '四维质量门禁',
    phase: 'ingestion',
    badge: 'Quality Gate >= 70',
    desc: '四因子加权质量评测（SOP 执行步数、工具契约、I/O 规约、容错机制），低于 70.0 物理拦截打回。',
    engine: 'SkillOptJudge',
    invariants: ['min_score >= 70.0', 'sop_steps >= 3', 'explicit_toolchain', 'anti_lazy_ast_guard'],
    role: 'Quality Judge',
  },
  {
    id: 'contract_zip',
    number: 4,
    name: '六元组契约压缩',
    phase: 'ingestion',
    badge: 'Token Compression',
    desc: 'SkillZip 引擎剥离装饰噪音与低熵文本，固化 6 元组高密契约，实现 40%~60% Token 减负。',
    engine: 'SkillZipEngine',
    invariants: ['freeze_yaml_header', 'freeze_code_blocks', 'lossless_semantic_preservation'],
    role: 'Zip Optimizer',
  },
  {
    id: 'seam_decision',
    number: 5,
    name: 'B6 接缝自适应裁决',
    phase: 'ingestion',
    badge: 'Ante-Gate Routing',
    desc: '计算与现有母包的语义重合与工具链亲和度；高亲和度归入大包 Scenario，低亲和度独立建包。',
    engine: 'SeamDecisionGateB6',
    invariants: ['affinity >= 75% -> MERGE', 'affinity <= 25% -> SPAWN', 'cell_division_at_100_scenarios'],
    role: 'Seam Router',
  },
  {
    id: 'boundary_guard',
    number: 6,
    name: '能力三段式边界排他',
    phase: 'ingestion',
    badge: 'Negative Boundary',
    desc: '腾讯顶会三段式能力档案结构：配置正向触发词与负向排他边界（明确不干什么），物理防技能抢单打架。',
    engine: 'CapabilityPage & BoundaryRouter',
    invariants: ['positive_triggers_min_3', 'negative_boundaries_asserted', 'neighbor_contrast_zero_collision'],
    role: 'Boundary Adjudicator',
  },

  // ── 后 6 阶：视网膜验收、零退化保护、黑匣子留痕与微手术结晶 ──
  {
    id: 'retina_eval',
    number: 7,
    name: '技能视网膜行为验收',
    phase: 'closed_loop',
    badge: 'Retina Sandbox',
    desc: '测试是唯一眼睛：沙箱运行真实 YAML 测试用例，动态断言真实输出、退出码与工具调用参数。',
    engine: 'EvalRunner & SkillEvalEngine',
    invariants: ['passed > 0 && failed == 0', 'false_exit_zero_blocked', 'real_tool_call_asserted'],
    role: 'Retina Gatekeeper',
  },
  {
    id: 'dual_split_guard',
    number: 8,
    name: 'RSI 零退化回归保护',
    phase: 'closed_loop',
    badge: 'Zero Regression',
    desc: '新工序场景并入大包时，执行 Dual-Split 保留集回归校验，确保历史存量场景能力 100% 零退化。',
    engine: 'RSIDualSplitVerifier',
    invariants: ['holdout_pass_rate >= baseline', 'regression_detected == false', 'evolve_block_freeze_surface'],
    role: 'Regression Protector',
  },
  {
    id: 'provenance_commit',
    number: 9,
    name: '黑匣子演变审计留痕',
    phase: 'closed_loop',
    badge: 'Provenance SSOT',
    desc: '记录全生命周期不可变证据（发现、校验、自愈、压缩、路由、落盘），生成前置后置快照 SHA-256。',
    engine: 'SkillProvenanceTracker',
    invariants: ['action: COMMITTED', 'snapshot_sha256_verified', 'immutable_audit_history'],
    role: 'Blackbox Tracer',
  },
  {
    id: 'aliasing_projection',
    number: 10,
    name: '别名透明网关投影',
    phase: 'closed_loop',
    badge: 'Zero-Breaking Gateway',
    desc: '物理落盘至大包 scenarios/ 后，动态别名网关自动重刷缓存，外部 Agent 调用单体名称 100% 零中断无感回退。',
    engine: 'SkillAliasingRouter',
    invariants: ['dynamic_glob_zero_hardcoding', 'is_virtual: true', 'http_200_transparent_alias'],
    role: 'Aliasing Gateway',
  },
  {
    id: 'hermes_micro_patch',
    number: 11,
    name: 'Hermes 经历微手术补丁',
    phase: 'closed_loop',
    badge: 'Micro-Patch <= 30',
    desc: '经历只增不删；副进程 FTS5 复盘真实对话，提议 <=30 行微手术补丁，支持在线审查与秒级一键回滚。',
    engine: 'HermesPatchEngine',
    invariants: ['patch_lines <= 30', 'reversible_one_click_rollback', 'fts5_dialogue_grounding'],
    role: 'Micro Surgeon',
  },
  {
    id: 'lessons_crystallize',
    number: 12,
    name: '事故教训反哺结晶',
    phase: 'closed_loop',
    badge: 'Lessons SSOT',
    desc: '将战地安全装甲拦截与重大事故反思（Evolution Lessons）一键结晶回写为技能铁律，实现终生免疫。',
    engine: 'EvolutionLessons & AutoCrystallizerB6',
    invariants: ['permanent_guideline_extracted', 'reflection_grounded', 'subconscious_reflex_injected'],
    role: 'Crystallizer B6',
  },
]
