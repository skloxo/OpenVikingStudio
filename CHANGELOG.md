# 📜 OpenViking Studio 更新日志 (Changelog)

All notable changes to OpenViking Studio will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2026-08-06

### 🚀 Major Feature Improvements (次版本升级重大特性)
- **100% i18n Dictionary Coverage**: Completed full Chinese (`zh-CN`) and English (`en`) translation keys for all 9 monitoring cards, navigation components, and task center KPIs. Set default language to `zh-CN`.
- **Markdown Parser CJK Token Estimation Alignment**: Corrected CJK character estimation coefficient from `0.7` to `1.0` in `markdown.py`, matching the Embedder physical batch limit (`-b 2048`).
- **Zero Data Truncation Guarantee**: Removed the dangerous `[:1800]` character truncation fallback in `collection_schemas.py`, ensuring transparent error reporting and accurate re-parsing.
- **Task Center Self-Healing Re-Queue Fix**: Updated re-queue mutation mode to `semantic_and_vectors` to regenerate fresh abstracts and prevent retry deadlocks.
- **Single Source of Truth Agent Entry Point**: Established `.agents/AGENTS.md`, `docs/PHILOSOPHY.md`, `docs/UI_DESIGN_SPEC.md`, `docs/ARCHITECTURE_BLUEPRINT.md`, and unified task cards in `REFACTORING_PLAN.md`.
- **Disaster Recovery & Rollback Protocols**: Documented VikingFS Git-style snapshot (`POST /api/v1/snapshot/commit` & `restore`) and `ovpack` backup specifications for memory entropy governance.

---

## [1.2.42] - 2026-08-06

### Added
- Created Agent entry navigation `.agents/AGENTS.md` and design philosophy docs.
- Added missing tasks KPI `tasksCount` and time filter scope keys.

### Fixed
- Fixed raw key path display in monitoring and tasks cards.
- Restored custom monitoring card translations.

---

## [1.2.41] - 2026-08-06

### Fixed
- Fixed CJK character token count estimation in Markdown parser.
- Removed silent `[:1800]` truncation fallback in `collection_schemas.py`.
- Reindexed all 43 top-level VikingFS resource directories.

---

## [1.2.40] - 2026-08-06

### Added
- Single Source of Truth `task-pipeline.ts` for unified task table and drawer step rendering (`外部解析` ➔ `语义处理` ➔ `嵌入向量`).
