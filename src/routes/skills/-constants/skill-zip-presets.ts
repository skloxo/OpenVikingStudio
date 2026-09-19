// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0
/**
 * Presets for SkillZip 0-Rollout Contractual Compression Engine.
 * (Card-Skill-ZipOnWrite-ContractualCompression / v1.5.35)
 */

export interface SkillZipPreset {
  id: string
  name: string
  description: string
  seedLength: number
  content: string
}

export const SKILL_ZIP_PRESETS: SkillZipPreset[] = [
  {
    id: 'alibaba-evolved-bloat',
    name: '阿里自进化膨胀技能 (5.2x 复读机)',
    description: '模拟自进化闭环中多次积累特例与重复代码、过度膨胀的典型复读机技能。',
    seedLength: 350,
    content: `---
name: git-pr-automation-bloated
description: Automated Git PR submitter with accumulated repetitive rules
---
# Interface
- Input: branch_name: str, commit_message: str, reviewers: list[str]
- Output: pr_url: str, merge_status: bool
- Tools: git_push(), gh_api_create_pr(), gh_api_check_status()

# Workflow
1. Please ensure that you check the git status first before doing anything.
2. In this step, the user will expect that you run the test suite using pytest.
3. Always verify that no secrets or API keys are leaked into the code repository.
4. Next, push the branch to remote origin using the proxy if available.
5. Create the PR using gh_api_create_pr() with the commit message.
6. Poll the CI check status every 5 seconds until it completes.
7. Always verify that no secrets or API keys are leaked into the code repository.
8. In this step, please ensure that you do not add unnecessary external dependencies.

# Protocol
- State FSM: INIT -> TESTING -> PUSHING -> PR_OPENED -> MERGED
- Timeout: 600s
- Retry: 3 times with exponential backoff

# Rules
- Always verify that no secrets or API keys are leaked into the code repository.
- NO GREEN EVER: Use cyan-500 for good and rose-500 for errors.
- Never propose a cd command directly to the shell.
- Please make sure that you do not add unnecessary external dependencies.
- NO GREEN EVER: Use cyan-500 for good and rose-500 for errors.
- Always verify that no secrets or API keys are leaked into the code repository.

# Contracts
- Invariant: Single file size must not exceed 500 lines.
- Invariant: Zero plaintext credentials in source code.
- Invariant: Contract fidelity must remain 100%.

# Evidence
- Test: pytest tests/unit/test_pr_flow.py must pass 100%.
- Assertion: PR URL must match regex https://github.com/.+/pull/\\d+.
`,
  },
  {
    id: 'long-range-pipeline-bloat',
    name: '长程工单流水线技能 (冗余特例堆叠)',
    description: '包含多步冗长客套描述与重复约束条件的长程工单执行技能。',
    seedLength: 420,
    content: `---
name: database-migration-pipeline
description: Production database schema migration and snapshot runner
---
# Interface
- Input: migration_id: str, target_version: str, dry_run: bool
- Output: status: str, applied_steps: int
- Tools: db_snapshot(), alembic_upgrade(), run_health_check()

# Workflow
1. Please ensure that you take a database snapshot first before doing anything.
2. In this step, the user will expect that you inspect the pending migrations.
3. Always remember to check that the database lock is released.
4. Next, execute the migration using alembic_upgrade() carefully.
5. In this step, run the health check suite to verify zero connection loss.
6. Always remember to check that the database lock is released.

# Protocol
- Protocol: WAL mode enabled, monotonic version tracking
- Timeout: 180s
- Retry: 3 times with exponential backoff

# Rules
- Always remember to check that the database lock is released.
- Never run destructive DDL without prior snapshot.
- Please make sure that you do not add unnecessary external dependencies.
- NO GREEN EVER: Status displays cyan-500 for active, rose-500 for fail.

# Contracts
- Invariant: Zero data loss during migration.
- Invariant: Maximum rollback duration <= 30s.

# Evidence
- Test: pytest tests/integration/test_migration.py must pass.
- Verification: Schema version must match target_version.
`,
  },
  {
    id: 'seed-baseline',
    name: '极客精简基准技能 (Seed Baseline)',
    description: '长度在 1.6x 门禁以内的极简高密度技能原型。',
    seedLength: 350,
    content: `---
name: code-review-seed
---
# Interface
- Tools: git_diff(), linter_run()
# Workflow
1. Fetch git diff against main.
2. Run linter with strict rules.
3. Submit review comments.
# Protocol
- Timeout: 120s
# Rules
- NO GREEN EVER: cyan-500 for pass, rose-500 for fail.
- Zero secrets in diff.
# Contracts
- Invariant: Single file <= 500 lines.
# Evidence
- Test: verify zero lint errors.
`,
  },
]
