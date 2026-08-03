# OpenViking Studio

[中文](README.md) / English

OpenViking Studio is a context and skill management workstation for multi-agent systems. Connecting to OpenViking engines, it provides shared memory storage, context monitoring, SOP quality gates, and automated skill evolution services for agent systems.

---

## Core Features

- **File System Event Sensing**: Powered by Linux `inotify` event engine, automatically tracking skill file reads and modifications without manual refresh.
- **Live Telemetry & Lesson Logging**: Directly connected to backend data stores. Automatically extracts structured lessons and updates documentation when agents resolve complex tasks.
- **Upstream Architecture Alignment**: Fully integrated with OpenViking 0.4.x/0.5.x native FastMCP interfaces, WorkMemory v2 mechanisms, and `ov dream` incremental sync.
- **Context Token Optimization**: Built-in LLMLingua-2 model reduces prompt token overhead by an average of 35% while preserving YAML header and code block integrity.

---

## Roadmap

```text
  Phase 1: Current Baseline (v1.2.35+)    Phase 2: Near-Term Evolution (v1.3.x)     Phase 3: Long-Term Vision (v2.0)
+------------------------------------+   +------------------------------------+   +------------------------------------+
| Skill Management & Event Sensing   |   | Skill-Loop Lesson Flywheel         |   | Online Skill Creation Sandbox      |
| Telemetry Pipeline                 | ➔ | SkillOpt Quality Gate & Scoring    | ➔ | Monaco Editor Integration          |
| IDE & OpenViking Session Sync      |   | Dynamic Weighting & Ranking        |   | End-to-End Privacy Auth & Scrub    |
+------------------------------------+   +------------------------------------+   +------------------------------------+
```

---

## Quick Start

### 1. Start OpenViking Server
```bash
openviking-server --config ~/.openviking/ov.conf --host 0.0.0.0 --port 1933
```

### 2. Launch Web Studio
```bash
npm install
npm run dev
```
Open `http://localhost:5173` to access the workstation.

---

## License

Apache-2.0 License
