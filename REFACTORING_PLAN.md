# OpenViking Studio — 唯一活跃原子工单看板 (REFACTORING_PLAN.md)

> **三层治理体系说明**：
> 1. **历史交付记录** ➔ 归档至 [DELIVERY_ARCHIVE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)（已交付 `v1.1.0` ~ `v1.1.23b`）
> 2. **远期愿景与 Epic 路线图** ➔ 移入 [ROADMAP.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/ROADMAP.md)（按 Epic 拆解管理）
> 3. **本文档 (REFACTORING_PLAN.md)** ➔ **唯一活跃原子工单看板**（仅保留当前可调度、数据契约明确、验收标准量化的最小原子工单）

---

## 📅 当前迭代原子工单看板 (Scheduled Atomic Tasks)

### 📌 P1-1: [ ] v1.1.23c：检索测试台 `/retrieval` 页 L0/L1 白盒检索轨迹树与得分渲染

**类型**：Feature  
**优先级**：P1  
**来源**：用户指导 ("去进行终验... 23c 23d 继续开发")  
**负责人**：Agent (Antigravity)  
**预计规模**：S (1 个迭代)

#### 1. 问题描述
当前 `/retrieval` 检索测试台仅能展示检索匹配到的最终文档列表，无法直观查验 Viking 1933 在匹配过程中到底是命中 L0 意图抽象层还是 L1 SOP 规约层，且缺少相似度得分（如 `0.985`）与 Trace 节点树结构。

#### 2. 目标
在 `/retrieval` 页面为每次检索结果渲染可折叠的 **L0/L1 白盒检索轨迹树**，可视化展示 Viking 向量匹配路径与相似度分值。

#### 3. 非目标
- 本卡片不修改后端向量检索逻辑或 SQLite 底层存储。
- 本卡片不改动 `/skills` 或 `/monitoring` 页面。

#### 4. 数据与接口契约 (Data Contract)
- **API 接口**：`POST /api/v1/search/find` 或 `GET /api/v1/system/status`
- **关键字段**：
  - `uri`: string (匹配到的资源/技能 URI)
  - `score`: number (相似度分值，保留 3 位小数，如 `0.985`)
  - `level`: `'L0' | 'L1' | 'L2'` (命中层级)
  - `trace_node`: `{ id: string, label: string, children?: trace_node[] }`
- **异常处理**：若后端未返回 `trace_node`，优雅收缩轨迹树并标注 `单节点直连`。

#### 5. 实施边界 (Domain Scope)
- 仅影响 `Retrieval` 页面功能域。
- 允许在 `src/routes/retrieval/` 目录下新增子组件、Hook 或类型定义文件（如 `src/routes/retrieval/components/TrajectoryTree.tsx`）。

#### 6. 量化验收标准
- [ ] **功能验收**：检索响应后，列表项右侧展现 `Level (L0/L1)` 极客徽章与相似度分值 Tag（如 `Score: 0.985`）。
- [ ] **树状交互**：展开轨迹树节点可层层查看 URI 继承关系。
- [ ] **空/异常状态**：查无结果或接口异常时，正确显示 `--` 哑光灰色提示，不发生崩溃。
- [ ] **视觉规范**：遵循 NO GREEN EVER 规则，高亮使用 `cyan-500` 冰青与 dark glassmorphism 风格。
- [ ] **构建验证**：`npm run build` 无 TypeScript / Vite 编译报错。

#### 7. 验证命令
```bash
npm run build && cp -r dist/* /home/skloxo/.local/lib/python3.12/site-packages/openviking/web_studio/dist/
```

---

### 📌 P1-2: [ ] v1.1.23d：监控页 `/monitoring` Token 节省率与 SLA 时延对比折线图

**类型**：Feature  
**优先级**：P1  
**来源**：Harness 观测降本增效指标诉求  
**负责人**：Agent (Antigravity)  
**预计规模**：S (1 个迭代)

#### 1. 问题描述
当前 `/monitoring` 页缺少将“开启 Harness 避坑拦截”与“传统全量代码塞入”两种模式下的 Token 消耗与 SLA 响应时延进行对比展示的动态图表。

#### 2. 目标
在 `/monitoring` 页新增双折线对比图，动态渲染有无 L0/L1 避坑拦截机制下的 Token 节省率及 P95 响应时延变化趋势。

#### 3. 数据与接口契约 (Data Contract)
- **API 接口**：`GET /api/v1/system/status`
- **关键字段**：
  - `timestamp_series`: string[]
  - `token_saved_rate`: number (如 `82.4`)
  - `latency_p95_ms`: number
- **异常处理**：数据缺失时折线图平滑过渡，无数据点处显示虚线。

#### 4. 实施边界 (Domain Scope)
- 仅影响 `Monitoring` 页面功能域 (`src/routes/monitoring/*`)。

#### 5. 量化验收标准
- [ ] **图表渲染**：在 Monitoring 页面成功绘制对比折线图。
- [ ] **视觉体验**：符合 `cyan-500` 冰青主题与响应式自适应宽度。
- [ ] **构建验证**：`npm run build` 成功。

---

## 📋 待调度后续原子工单 (Backlog Queue)

### 📌 P0-1: [ ] v1.1.33b：技能中心待规范技能探针与人机协同标准化上架流程

**类型**：Feature  
**优先级**：P0  
**来源**：用户指导 ("当发现有些技能不符合规范的时候，显示出来让用户选择要不要实施某种流程，让这个技能规范起来并加入到技能中心")  
**负责人**：Agent (Antigravity)  
**预计规模**：S (1 个迭代)

#### 1. 问题描述
当前技能中心为纯只读展示页面。当探针扫描到本地存在缺失 `SKILL.md` 或缺 YAML Header 的非标准技能目录时，用户无法在 UI 上察觉，且缺少一键触发人机协同“标准化规范补全”并上架到技能中心的功能。

#### 2. 目标
在 `/skills` 技能中心新增 **`⚠️ 待规范技能` 分栏与审计清单**，并提供 **`⚡ 一键规范化上架` 流程**，由 AI 自动根据目录结构推导标准的 YAML Header (`name`, `description`) 框架，提交用户确认后一键补全 `SKILL.md` 并向量化上架至 OpenViking。

#### 3. 实施边界 (Domain Scope)
- 仅影响 `Skills` 页面功能域 (`src/routes/skills/*`) 与 MCP 网关探针。

#### 4. 量化验收标准
- [ ] **物理探针**：可清晰列出本地缺失 `SKILL.md` 的待规范技能文件夹清单及缺件诊断。
- [ ] **交互流程**：提供“预览规范”与“一键生成并上架”按钮，完成补全后技能计数动态 +1。
- [ ] **构建验证**：`npm run build` 成功。

---

### 📌 P0-2: [ ] v1.1.36a：核心服务心跳采集与健康探针模型
### 📌 P0-3: [ ] v1.1.36b：首页健康状态徽章与 CLI 降级告警
### 📌 P1: [ ] v1.1.35：图谱节点性能 Spike 探查与 LOD 优化
### 📌 P2: [ ] v1.1.34：任务时间范围过滤能力
