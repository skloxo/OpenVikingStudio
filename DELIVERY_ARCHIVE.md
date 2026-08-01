# OpenViking Studio — 历史交付全量归档台账 (DELIVERY_ARCHIVE.md)

> 本文档为 OpenViking Studio 已验收通过的历史版本与任务卡片归档。主计划 `REFACTORING_PLAN.md` 仅保留当前活跃可执行的原子工单。

---

## 🎉 v1.2.0 正式封板 Major Release (前后端一体化中枢)
- **交付时间**：2026-08-01
- **Git Tag**：`v1.2.0`
- **用户验收**：验收通过 ✅ ("24、25 这两个小版本算是验收通过了。现在封板... 版本号定为 1.2.0")
- **核心定位与升级**：
  - **项目定位重构**：从单 Wiki 前端正名为 **OpenViking Studio — 极客 Agent & 技能自演进全栈中枢 (前后端全栈一体化中枢)**。
  - **全链路归环**：包含前端 Web UI (React/TanStack) 与后端网关代理 (`mcp-openviking` / Vite middleware) 的双向深度迭代。
  - **6 大高密度 KPI 观察阵列 (3×2 矩阵)**：隐式自动唤醒率、技能运行成功率、VK 技能统一收敛率、技能资产活跃复用率、Context 提示词压缩率、Harness 技能自演进。
  - **全盘 0 Mock 数据强约束**：所有指标直连 24H 动态链路算子，零伪造假数字，空数据物理优雅显示 `--`。
  - **自动化治理**：感知到新技能/Wiki 后，Harness 后台自动补全 description 描述、自动进行规范标准化与 FastMCP 1933 向量上架，切除冗余手动按钮。

---

## 📌 v1.1.25：技能中心 6 卡片 3x2 KPI 观察阵列 + 布局精简 + 0 Mock 强约束
- **交付时间**：2026-08-01
- **Git Tag**：`v1.1.25` (`f8c3017`, `b22dc97`)
- **用户验收**：验收通过 ✅
- **修改文件**：`vite.config.ts` · `src/routes/skills/route.tsx` · `REFACTORING_PLAN.md`
- **交付内容**：
  1. 扩充技能中心 KPI 观察区为 6 大卡片 (3×2 矩形阵列)，新增 `技能资产活跃复用率` 和 `Context 提示词压缩率`。
  2. 切除 header 冗余分割横线 `border-b`，使用 `items-end` 使 `3小时 Rolling` Badge 与副标题在物理基线上完全齐平。
  3. 移除了 `补全简介` 手动按钮与 `已装载 N 个技能` 重复 Badge，将搜索框右对齐嵌入 Scope 筛选栏同行。
  4. 彻底清洗硬编码 `98.6%` 和假满分 `100.0%`，打通后端真实算子接口，无采样时显示 `--`。

---

## 📌 v1.1.24：技能中心 KPI 24H 滚动窗口 + 零 Mock 清洗 + 崩溃修复
- **交付时间**：2026-08-01
- **Git Tag**：`v1.1.24` (`255ca50`)
- **用户验收**：验收通过 ✅
- **修改文件**：`vite.config.ts` · `src/routes/skills/route.tsx` · `.agents/skills/openviking-studio-dev/SKILL.md`
- **交付内容**：
  1. 4 大 KPI 卡片统计窗口切换至最近 24 小时 (24H Rolling)，API 参数 `?window=24h` 显式传递。
  2. 清洗全部 Mock 假数字初始值。
  3. 修复缺失 `SearchIcon` import 导致的路由崩溃问题（Lesson #29）。

---

## 📌 v1.1.23c：技能中心双门锁合规探针、待规范白盒曝光与一键规范化上架流程
- **交付时间**：2026-08-01
- **Git Tag**：`v1.1.23c` (`25aa83b`, `797a1d4`)
- **用户验收**：⏳ 待用户终验 (开发构建已完成，等待用户在 UI 侧终验)
- **修改文件**：
  - [src/routes/skills/route.tsx](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/src/routes/skills/route.tsx)
  - [mcp-openviking/mcp_openviking_server.py](file:///home/skloxo/aho/openclaw/mcp-openviking/mcp_openviking_server.py)
  - [.agents/skills/openviking-studio-dev/SKILL.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/.agents/skills/openviking-studio-dev/SKILL.md)
  - [REFACTORING_PLAN.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/REFACTORING_PLAN.md)
- **交付内容**：
  1. 实现了 `/skills` 页面双门锁治理面板，白盒展示 `已就绪标准技能` 与 `⚠️ 待规范技能`。
  2. 上线技能来源 Agent 识别徽章（`🤖 OpenClaw`, `🦅 Hermes`, `📈 TideTrading`, `🚀 Antigravity`），极客彩色高亮呈现。
  3. 部署 `openviking_audit_skills` 与 `openviking_fix_skill` 探针，支持在 UI 上一键补全规范要件并向 OpenViking 向量库自动装载上架。
  4. 沉淀多 Agent 生态双门锁治理规范与 Git Tag Changelog SOP 至 Master Memory。

---

## 📌 v1.1.23b：技能中心概览卡片硬核物理指标重构
- **交付时间**：2026-08-01
- **Git Tag**：`v1.1.23b` (`92bd4f8`, `50b5e7a`)
- **用户验收**：验收通过 ✅ ("23A、23B 算验收通过")
- **修改文件**：
  - [src/routes/skills/route.tsx](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/src/routes/skills/route.tsx)
  - [mcp-openviking/mcp_openviking_server.py](file:///home/skloxo/aho/openclaw/mcp-openviking/mcp_openviking_server.py)
- **交付内容**：
  1. 替换静态假文案为 4 张真实底层数据卡片（避坑拦截力、检索/存储结构、Agent 物理调用分布、最热演进技能）。
  2. 实现 `~/.openviking/harness_metrics.json` 全局原子级磁盘持久化，打通 1933 REST API 与 FastMCP 进程隔离。

---

## 📌 v1.1.23a：底层 MCP Harness 监控统计指标接口
- **交付时间**：2026-08-01
- **Git Tag**：`v1.1.23a` (`caafb2c`, `3bc4d87`)
- **用户验收**：验收通过 ✅
- **修改文件**：
  - [mcp-openviking/mcp_openviking_server.py](file:///home/skloxo/aho/openclaw/mcp-openviking/mcp_openviking_server.py)
- **交付内容**：
  1. 建立 `HARNESS_METRICS` 数据存储。
  2. 新增 `openviking_harness_stats` MCP 工具与安全类型校验。

---

## 📌 v1.1.0 ~ v1.1.22 早期历史归档
- **v1.1.22**：路由按需懒加载 (Lazy Load) 与构建 Chunk 优化 (`v1.1.22`)
- **v1.1.21**：界面极客审美精修与 NO GREEN EVER 规则贯彻 (`v1.1.21`)
- **v1.1.20**：双模响应式布局与极简数据透视卡片 (`v1.1.20`)
- **v1.1.19**：i18n 国际化完整覆盖 (`v1.1.19`)
