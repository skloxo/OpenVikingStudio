# OpenViking Studio — 唯一活跃原子工单看板 (REFACTORING_PLAN.md)

> **三层治理体系说明**：
> 1. **历史交付记录** ➔ 归档至 [DELIVERY_ARCHIVE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)（已交付 `v1.1.0` ~ `v1.1.23b`）
> 2. **远期愿景与 Epic 路线图** ➔ 移入 [ROADMAP.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/ROADMAP.md)（按 Epic 拆解管理）
> 3. **本文档 (REFACTORING_PLAN.md)** ➔ **唯一活跃原子工单看板**（仅保留当前可调度、数据契约明确、验收标准量化的最小原子工单）

---

## 📅 当前正在调度的核心迭代 (Active Scheduled Tasks)

### 📌 P0: [ ] v1.1.23c：技能中心双门锁合规探针、待规范白盒曝光与一键规范化上架流程

**类型**：Feature  
**优先级**：P0 (用户明确指令：提前并集中在当前技能中心迭代中完成)  
**来源**：用户指导 ("关于技能中心进行迭代，往前提一提... 既能显示出合规的又能显示出不合规的... 一键规范化并上架")  
**负责人**：Agent (Antigravity)  
**预计规模**：S (1 个迭代)

#### 1. 问题描述
当前技能中心页面仅展示部分从后端口径读取到的已加载技能（黑盒），缺少对本地所有探针扫描到的“不合规技能（如缺失 `SKILL.md` 或缺 YAML Header）”的白盒曝光，且缺少一键补全规范要件并向 OpenViking 向量库上架的功能。

#### 2. 目标
1. **白盒双 Tab 渲染**：在 `/skills` 页面增加 `已就绪标准技能 (146)` 与 `⚠️ 待规范技能 (12)` 双分栏。
2. **缺件物理诊断**：透明列出待规范技能的名称、绝对路径、及具体缺件原因（如 `❌ 缺失 SKILL.md 文件`）。
3. **一键规范化上架**：提供 `⚡ 一键规范化上架` 交互按钮，自动补充合规 YAML Header 范本并生成 `SKILL.md`，自动建软链接并触发 1933 向量化索引上架！

#### 3. 数据与接口契约 (Data Contract)
- **API 接口**：`GET /api/v1/skills` 及网关本地探针 `_auto_sync_skills()`
- **关键字段**：
  - `name`: string (技能或目录名称)
  - `status`: `'compliant' | 'non_compliant'`
  - `missing_reason`: string (诊断原因，如 `'missing_skill_md' | 'missing_header'`)
  - `path`: string (本地绝对路径)

#### 4. 实施边界 (Domain Scope)
- 仅修改 `src/routes/skills/route.tsx` 及 `mcp-openviking/mcp_openviking_server.py`。

#### 5. 量化验收标准
- [ ] **物理诊断曝光**：技能页清晰展示 `已就绪 (146)` 与 `待规范 (12)` 统计，切换 Tab 能全量透视不合规技能清单与具体缺件原因。
- [ ] **一键规范化上架**：在 UI 点击“⚡ 规范化上架”，自动生成合规 `SKILL.md`，技能状态实时迁移至 `已就绪` 栏。
- [ ] **视觉规范**：遵循 NO GREEN EVER 规则，警告使用 `rose-500/80`，推荐按钮使用 `cyan-500`。
- [ ] **构建验证**：`npm run build` 无 TypeScript / Vite 编译报错。

#### 6. 验证命令
```bash
npm run build && cp -r dist/* /home/skloxo/.local/lib/python3.12/site-packages/openviking/web_studio/dist/
```

---

## 📋 待调度后续原子工单 (Backlog Queue)

### 📌 P1-1: [ ] v1.1.23d：检索测试台 `/retrieval` 页 L0/L1 白盒检索轨迹树与得分渲染
### 📌 P1-2: [ ] v1.1.23e：监控页 `/monitoring` Token 节省率与 SLA 时延对比折线图
### 📌 P2-1: [ ] v1.1.24a：核心服务心跳采集与健康探针模型
### 📌 P2-2: [ ] v1.1.24b：首页健康状态徽章与 CLI 降级告警
