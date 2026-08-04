# OpenViking Studio — 唯一活跃原子工单看板 (REFACTORING_PLAN.md)

> **双轨制管理规约 (Dual-Track Management Rules)**：
> 1. **工单 ID 解耦 (Task ID Decoupling)**：卡片使用模块持久化 ID（如 `TASK-SKILL-01` / `TASK-HARNESS-01`），**严禁在排期阶段过早绑定版本号**！插队/新增任务时可无缝创建新工单 ID。
> 2. **阶段封板映射 (Milestone Tag Binding)**：按【阶段目标 Milestone】进行分组管理；只有当用户显式下达“封板/打 Tag 发版”指令时，AI 才有权限根据实际交付按顺序映射物理 Tag（当前基线为 `v1.2.38`）。
> 3. **本地私有留存**：本文件及内部研发记录只在本地管理 (`.gitignore`)，远程仓库保持绝对代码纯净与数据脱敏。

---

# OpenViking Studio 渐进式架构重构路线图 (Single Source of Truth)

> **最新版本**：`v1.2.40` (Tag: `v1.2.40`)  
> **核心原则**：第一性原理 | 奥卡姆剃刀 | 全生命周期信达雅 | 零假数据 | NO GREEN EVER  
> **更新时间**：2026-08-04 18:22:30

---

## 📌 历史版本交付记录 (Delivery History)

### 🚀 [x] v1.2.40 (Tag: `v1.2.40`) - 8 并发感知智能状态分拆与服务重启僵尸任务自动扫除治理 ✅
- **Git Commit**: `237db83` / Tag: `v1.2.40`
- **主要交付内容**：
  1. **物理硬件超参固化**: 锁定 `Qwen3-Embedding-8B` 并发上限为 `8` (`embedding.max_concurrent = 8`)，`lock_timeout = 10.0s` 彻底清除 `tree lock` 超时。
  2. **智能 Active/Queued 状态分拆**: 在前端 Task Route 全局引入 `MAX_CONCURRENT_CAP = 8` 物理有效状态映射，解开 `pending` 永远为 0 的假象，使卡片、下拉筛选、列表 Status Badge (`8 / 1`) 100% 物理完全对齐。
  3. **服务重启僵尸任务清扫**: 运行自动扫除引擎，将 14 个由于服务重启造成的“1h+ 无心跳悬挂僵尸任务”一键 `auto-heal` 标记为中断恢复。
  4. **OpenViking 体外大脑落盘**: 将本轮性能超参与白盒物理规则写入 `viking://resources/master_memory/openviking_concurrency_and_performance_best_practices.md`。

---

## 📅 第一部分：【当前核心执行阶段：Phase 1 — 技能中心与 Harness 引擎双向打通】

---

### 📌 P0: [x] [TASK-RELEASE-v1.2.38] 全线安全门禁防护、锁超时缓冲修复与重新发起 API 路由对齐 ✅

**模块**：OpenVikingStudio 前端 & OpenViking 后端内核  
**工单 ID**：`TASK-RELEASE-v1.2.38`  
**状态**：已完成并终验通过 ✅ (`Tag: v1.2.38`)  
**来源**：用户指导 — 彻底修复锁超时 (Tree Lock Timeout)、任务重新发起 API 路由重定向、零信任安全防泄漏与全线开发环境对齐。

#### 1. 交付改动与技术方案
1. **重新发起任务路由修复 (`route.tsx`)**：重构 `viking://` 资源重新入队分发逻辑，精准路由发往 `/api/v1/content/reindex`，彻底消除误调 `/api/v1/resources` 导致的宿主机路径拦截 500 报错；
2. **后端锁超时缓冲重构 (`lock_manager.py` & `path_lock.py`)**：将底层 `LockManager` 默认的 `lock_timeout` 从 0.0 秒调整为 10.0 秒，并将 `acquire_tree` 的形参默认值重构为 `None`（自动生效 `lock_expire` 300 秒超时轮询保护），彻底瓦解高并发下 `Tree lock timeout` 崩溃；
3. **消除硬编码 Key 泄露与增加全盘门禁 (`use-app-connection.tsx` & `app-shell.tsx`)**：彻底拔除硬编码 Root Key 泄露隐患，在全套数据视图外层包裹 `<AccessRequiredGate />`，未鉴权身份禁止预览任何数据；
4. **并发超参匹配优化 (`ov.conf`)**：针对物理 12 核 CPU 与本地 RTX 2080 Ti 上跑的 `Qwen3-Embedding-8B` (`--parallel 8`) 模型，将 Embedding 并发精密对齐为 `8`，VLM 多模态解析对齐为 `4`；
5. **1936 开发环境与 1933 生产环境 100% 物理对齐**：重新构建生产 Bundle，全量同步刷新并部署至 1933 / 1936，重启 `openviking.service` 生产守护服务。

#### 2. 验证结果
- [x] 重发 Viking 资源正确调用 `/api/v1/content/reindex` 接口；
- [x] 后端 `Tree lock` 在 10 秒缓冲队列中平滑轮询获取写锁，零抛出异常；
- [x] 匿名/无 Key 状态下全站弹出安全验证告警，隐私绝对受控；
- [x] Vite 编译打包 0 报错，已成功生成打 Tag `v1.2.38` 交付并完成 Git 推送。

---

---

### 📌 P0: [ ] [TASK-VERSION-TIMELINE-01] .md 文档资源“查看文件版本”时间轴与“点击回滚版本”功能移植

**模块**：OpenVikingStudio 前端 (`src/routes/resources`)  
**工单 ID**：`TASK-VERSION-TIMELINE-01`  
**优先级**：P0（最高）  
**来源**：用户指导 — 1935 中针对 `.md` 文档的【查看文件版本】历史时间轴（VersionTimeline）及【点击回滚版本】（RotateCcw 版本一键还原）功能移植至 1936

#### 1. 核心功能与交互说明
1. **点开头元数据文件判定 (`.abstract.md` / `.overview.md`)**：在 OpenViking 架构中，系统生成的 `.abstract.md` (L0-L1 摘要) 与 `.overview.md` (L2-L3 概览) 为 Context 演进快照文件。1936 选中以 `.` 开头的元数据文件时，右上方精准唤起【查看历史版本】按钮；
2. **版本历史时间轴 (`VersionTimeline.tsx`)**：展开后，按时间倒序展现版本的快照历史（版本号、更新时间、变更说明、修改人）；
3. **版本快照比对 (Diff Viewer)**：支持选中任意历史版本，高亮展示与当前版本的 Text / Markdown 差异；
4. **“点击回滚版本”动作 (`RotateCcw Rollback`)**：提供极客风格【回滚至此版本】操作按钮，点击后向 OpenViking 后端发送版本还原请求，并同步刷新 1936 资源列表。

![.abstract.md 查看历史版本与回滚界面](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/assets/markdown_versioning_rollback_screenshot.png)

#### 2. 1935 历史参考源码 (1935 Legacy Reference Code)
```tsx
// file:///home/skloxo/openviking-ui-ruansheng8/src/components/resources/version-timeline.tsx
import React from 'react';
import { Clock, RotateCcw } from 'lucide-react';

interface Version {
  id: string;
  timestamp: string;
  message: string;
  author: string;
}

const mockVersions: Version[] = [
  { id: 'v3', timestamp: '2023-10-27 14:30', message: '更新了产品文档', author: 'admin' },
  { id: 'v2', timestamp: '2023-10-26 10:15', message: '修复错别字', author: 'user1' },
  { id: 'v1', timestamp: '2023-10-25 09:00', message: '初始提交', author: 'admin' },
];

export function VersionTimeline({ resourceUri }: { resourceUri: string }) {
  return (
    <div className="space-y-4 p-4 border rounded-lg bg-white">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium flex items-center gap-2">
          <Clock className="w-5 h-5" /> 历史版本
        </h3>
      </div>
      <p className="text-sm text-gray-500 break-all mb-4">目标: {resourceUri}</p>
      
      <div className="relative border-l border-gray-200 ml-3 space-y-6 pb-4">
        {mockVersions.map((v) => (
          <div key={v.id} className="mb-6 ml-6">
            <span className="absolute flex items-center justify-center w-6 h-6 bg-blue-100 rounded-full -left-3 ring-8 ring-white">
               <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
            </span>
            <div className="flex justify-between items-start">
              <div>
                <h4 className="font-semibold text-gray-900">{v.message}</h4>
                <p className="text-sm text-gray-500">{v.timestamp} by {v.author}</p>
              </div>
              <button className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
                <RotateCcw className="w-4 h-4" /> 回滚至此版本
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### 📌 P0: [ ] [TASK-NODE-ACL-01] 节点 NodePermissions 访问控制策略与角色权限配置器

**模块**：OpenVikingStudio 前端 (`src/routes/resources` & `src/routes/users`)  
**工单 ID**：`TASK-NODE-ACL-01`  
**优先级**：P0  
**来源**：用户指导 — 1935 中多账号/多角色的节点级权限 ACL 策略配置移植至 1936

#### 1. 功能定义与技术方案
- **ACL 策略配置面板 (`NodePermissions.tsx`)**：展示当前资源节点针对特定 Account / User 的权限掩码（Read, Write, Delete, Reindex）；
- **角色授权开关**：提供极客风格切换 Switch，动态更新 Viking 节点 ACL 权限规则。

#### 2. 1935 历史参考源码 (1935 Legacy Reference Code)
```tsx
// file:///home/skloxo/openviking-ui-ruansheng8/src/components/resources/node-permissions.tsx
import React, { useState } from 'react';
import { Shield, Plus, X, Save, Check } from 'lucide-react';

interface PermissionEntry {
  entityId: string;
  type: 'user' | 'agent';
  role: 'read' | 'write';
}

export function NodePermissions({ nodeUri }: { nodeUri: string }) {
  const storageKey = `mock_permissions_${nodeUri}`;
  const [permissions, setPermissions] = useState<PermissionEntry[]>(() => [
    { entityId: "agent-001", type: "agent", role: "read" },
    { entityId: "user-alice", type: "user", role: "write" },
  ]);
  return (
    <div className="p-4 border rounded-lg bg-white space-y-4">
      <h3 className="font-medium flex items-center gap-2">
        <Shield className="w-5 h-5" /> 节点访问控制 (ACL)
      </h3>
      {/* 权限规则列表与新增操作 */}
    </div>
  );
}
```

---

### 📌 P0: [ ] [TASK-OUTLINE-OVERVIEW-01] L0-L4 深度 Outline 结构化概览拓扑视图

**模块**：OpenVikingStudio 前端 (`src/routes/resources` & `src/routes/graph`)  
**工单 ID**：`TASK-OUTLINE-OVERVIEW-01`  
**优先级**：P0  
**来源**：用户指导 — 1935 中【显示目录概览】L0-L4 结构化摘要与文本 Outline 全景拓扑图尚未移植至 1936

#### 1. 功能定义与技术方案
- **目录概览拓扑开关**：勾选【显示目录概览】后，读取 `getContentOverview` 接口返回的 L0-L4 深度摘要；
- **全景 Outline 分层折叠图**：按层次展示文档/资源的节点大纲、分类与语义索引概览。

---

### 📌 P0: [x] [TASK-MOBILE-NAV-01] 1936 前端移动端响应式 Drawer 导航菜单适配 ✅

**模块**：OpenVikingStudio 前端 + openviking-server 守护层  
**工单 ID**：`TASK-MONITORING-METRICS-01`  
**状态**：已完成并终验通过 ✅ (`Tag: v1.2.38`)  
**来源**：用户指导 — HTTP 状态码 400/401 被强制推入 500；EMB (Qwen3-Embedding-8B) / Rerank (qwen3-reranker-0.6b) 被误标识为 ollama；1933 随 IDE 关闭断连

#### 1. 交付改动与技术方案
1. **HTTP 状态码多维分拆 (`http-status-chart.tsx`)**：重构错误状态码渲染算法，解除强行 500 归类，精准独立展现 400 (请求参数错误)、401 (未授权)、404 与 500；
2. **llama.cpp 原生供应商标头校准 (`model-monitoring-card.tsx`)**：修正模型监控卡片，将本地 Embedding 8B 与 Reranker 0.6B 的供应商明确显示为 `llama.cpp/local`，并补齐缺省回退展示；
3. **1933 Systemd 用户守护全量接入 (`openviking.service`)**：将 1933 后端引擎交由系统级 `systemctl --user` 托管，具备开机/WSL 自动启动、挂掉 3s 自动自愈重启，与 IDE 生命周期 100% 物理强解耦。

#### 2. 验证结果
- [x] HTTP 状态码 400、401、500 分拆显示 100% 准确；
- [x] 本地 EMB 与 Rerank 模型 Supplier 统一标识为 `llama.cpp/local`；
- [x] 关闭 IDE 或关闭 Terminal 后，1933 生产服务系统级常驻 200 OK 在线；
- [x] Vite 编译打包 0 报错，打 Tag `v1.2.38` 交付。

---

### 📌 P0: [x] [TASK-MOBILE-NAV-01] 1936 前端移动端响应式 Drawer 导航菜单适配 ✅

**模块**：OpenVikingStudio 前端 layout  
**工单 ID**：`TASK-MOBILE-NAV-01`  
**状态**：已完成并终验通过 ✅ (`Tag: v1.2.37`, `Commit: 4394305+`)  
**来源**：用户指导 — 移动端视口下原侧边栏隐藏导致找不到导航菜单；需补齐移动端响应式抽屉菜单与汉堡包按钮

#### 1. 交付改动与技术方案
1. **Zustand 状态库扩展 (`useStudioStore.ts`)**：增加 `isMobileMenuOpen` / `toggleMobileMenu` / `setIsMobileMenuOpen` 移动端抽屉开闭状态控制；
2. **Navbar 汉堡包切换按钮 (`Navbar.tsx`)**：仅在 `< md` 移动端视口展示 `MenuIcon` / `XIcon` 图标按钮；
3. **Sidebar 响应式抽屉 (`Sidebar.tsx`)**：桌面端维持 `hidden md:flex` 64px 侧边栏，移动端提供侧滑 Sheet/Drawer + 黑色半透明 Backdrop 遮罩，点击导航项或背景自动收起。

#### 2. 验证结果
- [x] Vite 编译打包 0 报错；
- [x] 移动端 `< md` 视口下顶部汉堡包按钮显示正常；
- [x] 点击汉堡包滑出抽屉菜单，点击路由切换后自动收起；
- [x] 打包部署至 1933 生产 Web 路径。

---

### 📌 P0: [ ] [TASK-HARNESS-SOP-01] 预制规约检查引擎与全量技能简介自动生成闭环 (Builtin SOP & Description Auto-Gen)

**模块**：Harness 引擎 + 技能中心  
**工单 ID**：`TASK-HARNESS-SOP-01`  
**优先级**：P0（最高）  
**来源**：用户指导 — 36 条预制规约当前仅为 UI 硬编码数组无检查；260+ 技能无简介显示"暂无额外说明"  
**预计规模**：M (2 个迭代)

#### 1. 现状与根因
- `BUILTIN_LESSONS`（36条）在 `harness-logs.tsx` 中为 UI 硬编码静态数组，缺乏后台 Python 逻辑进行真实审计与阻断；
- 大量技能 `SKILL.md` 的 YAML frontmatter 缺少 `description` 字段，后端返回空字符串，前端退化显示"暂无额外说明"；
- 缺乏自动扫描与后台 LLM 提炼无人值守生成管道。

#### 2. 交付目标与技术方案
1. **预制规约静态/动态检查**：建立后台算子 `harness_sop_checker.py`，遍历全量 260+ 技能检查：
   - 是否包含规范 `SKILL.md` (Rule 14)
   - `description` 是否存在且 >10 字 (Rule 31)
   - 检查结果输出至 `harness_metrics.json`，算出真实合规率 (%) 并在 Harness 审计页曝光；
2. **简介后台自动生成**：对无描述的技能，调用 Harness LLM（依赖 `TASK-HARNESS-LLM-01`）提炼 30 字中文自解释，写回 `SKILL.md` YAML frontmatter。

#### 3. 量化验收标准
- [ ] 36 条规约转换为真正可运行的 Python 合规检查器；
- [ ] 260+ 技能卡片中的“暂无额外说明”被自动提炼生成的中文简介替换；
- [ ] Harness 审计页展示全盘技能真实合规率 (%)。

### 📌 P1: [ ] [TASK-UPSTREAM-SYNC-01] 官方上游 (volcengine/OpenViking:main) 渐进式原子合并与 Adapter 兼容验证组 (Progressive Upstream Sync Pipeline)

**模块**：OpenViking 核心引擎 + Upstream 管道  
**工单 ID**：`TASK-UPSTREAM-SYNC-01` (含 A/B/C/D 4 个原子工单)  
**优先级**：P1  
**来源**：用户指导 — 上游领先 1890+ commit，绝对禁止一次性大合并，必须原子化拆解、完成一个验收测试一个，保障主服务绝不崩溃  
**预计规模**：L (4 个渐进式小迭代)

#### 核心防护铁律
> ⚠️ **严禁一次性暴力 Merge 1890+ 提交**！必须按模块层级严格拆分为以下 4 个独立的原子工单，按顺序逐一合并、逐一跑通 API/MCP 自动化回归测试后才允许推进下一阶段！

---

#### 🔹 [ ] [TASK-UPSTREAM-SYNC-01A] 拓扑分析与 Viking Adapter 物理隔离准备
- **目标**：挂载 `git remote add upstream https://github.com/volcengine/OpenViking.git`，分析 1890 个提交的变更分布；
- **操作**：将我们私有的 `inotify` 感应、`file_count` 目录透视、`harness_metrics.json` 写入解耦抽离为干净独立的 Adapter 扩展模块；
- **验收**：建好 `feat/sync-upstream-v0.5.x` 隔离分支，完成私有 Adapter 模块防冲突保护。

---

#### 🔹 [ ] [TASK-UPSTREAM-SYNC-01B] 阶段 1：底层存储层与 WorkMemory v2 增量合并与单体测试
- **目标**：仅合并上游关于 Storage、LevelDB、VectorDB 索引及 WorkMemory v2 的底层提交；
- **操作**：调用 `resolving-merge-conflicts` 解析存储层冲突，进行数据读写与 LevelDB 锁状态单体测试；
- **验收**：[ ] 存储层单元测试 100% 通过，1933 端口数据库启动正常。

---

#### 🔹 [ ] [TASK-UPSTREAM-SYNC-01C] 阶段 2：FastMCP 门禁、RPC 路由与 Session 会话层增量合并
- **目标**：合并上游 FastMCP 服务端、REST Router 及 Session 管理模块提交；
- **操作**：合并路由代码，验证 `/api/v1/skills`、`/api/v1/sessions` 及 FastMCP 工具响应；
- **验收**：[ ] MCP 工具调用及 REST API 契约无断流、无 500 异常。

---

#### 🔹 [ ] [TASK-UPSTREAM-SYNC-01D] 阶段 3：全系统 Viking Adapter 回归与终验闭环
- **目标**：重新挂载 Viking Adapter，进行全系统端到端功能终验；
- **操作**：测试 `file_count` 准确性、`auto_wakeup_rate` 遥测、Harness Logs 持久化等核心能力；
- **验收**：[ ] 全系统测试 100% 跑通，打 Tag `v1.3.0` 封板交付。

---

### 📌 P1: [ ] [TASK-SESSION-SYNC-01] IDE ↔ OpenViking 全量会话与记忆实时自动同步 (Session & Memory Auto-Sync)

**模块**：OpenViking Session Gateway + FastMCP  
**工单 ID**：`TASK-SESSION-SYNC-01`  
**优先级**：P1  
**来源**：用户疑问 — IDE 会话是否自动传给 VK？首页“今日检索次数”为何显示 0 次？  
**预计规模**：M (2 个迭代)

#### 1. 现状与根因
- IDE 与 OpenViking 的交互目前仅在 Agent 主动调用 `memory_store` 时沉淀，会话消息未实时流式写入 `/api/v1/sessions`；
- 首页调用的 `/api/v1/console/dashboard/summary` 依赖 `today_retrievals`，由于未自动捕捉隐式检索，导致数据呈现为 0。

#### 2. 交付目标与技术方案
1. **会话静默实时流转**：在 MCP 服务器 (`mcp_openviking_server.py`) 中增加消息拦截 Hook，在交互过程中自动调用 `openviking.session` 写入会话历史；
2. **检索次数物理统计**：将 MCP 隐式与显式检索统一汇入 `today_retrievals` 统计，使首页“今日检索次数”真实更新。

#### 3. 量化验收标准
- [ ] IDE 会话消息实时同步至 OpenViking Studio `/sessions` 页面；
- [ ] 首页“今日检索次数”随交互真实增加，不再恒定为 0。

---

### 📌 P1: [ ] [TASK-SKILL-CENTER-01] 隐式自动唤醒率真实数据打通 (auto_wakeup_rate via MCP 主动上报)

**模块**：技能中心 全托管感应引擎 + Harness MCP  
**工单 ID**：`TASK-SKILL-CENTER-01`  
**优先级**：P1  
**来源**：`auto_wakeup_rate` 当前缺少 `find_calls` 主动上报数据  
**预计规模**：S (1 个迭代)

#### 1. 交付目标
1. **后端 (`mcp_openviking_server.py`)**：在 `openviking_find` / `openviking_search` MCP 工具内，识别命中的 SKILL.md 路径，将 `skill_name` 写入 `harness_metrics.json` 的 `skill_find_log` 字段；
2. **后端 (`system.py`)**：`get_harness_metrics()` 从 `skill_find_log` 统计 `find_calls` 并派生 `auto_wakeup_rate`。

#### 2. 量化验收标准
- [ ] 调用一次 `openviking_find` 后，`harness_metrics` 返回 `auto_wakeup_rate > 0`；
- [ ] 技能中心“隐式自动唤醒率”显示真实百分比。

---

### 📌 P2: [ ] [TASK-SKILL-CENTER-02] Context 提示词压缩率实现 (context_compression_ratio via LLMLingua-2)

**模块**：技能中心 + Harness 引擎  
**工单 ID**：`TASK-SKILL-CENTER-02`  
**优先级**：P2  
**来源**：`context_compression_ratio` 字段待接入组件化压缩模型  
**预计规模**：M (2 个迭代)

#### 1. 交付目标与技术方案
1. 遵从 Rule 7（组件化嵌入与非侵入式适配原则），在同进程内初始化微型 `LLMLingua-2` 概率筛选模型；
2. 针对注入给 Agent 的 SOP 提示词进行动态 Token 压缩，固化超参数 `rate=0.50`，保护 YAML Header 与代码块；
3. 将实际省下的 Token 比率写入 `harness_metrics.json` 中的 `context_compression_ratio`。

#### 2. 量化验收标准
- [ ] 技能中心 KPI 卡片 5 展示真实 Token 压缩率（如 `35.4%`）；
- [ ] 压缩算法熔断保底，不影响主服务稳定性。

---

### 📌 P2: [ ] [TASK-HARNESS-LLM-01] Harness 配置化 LLM 后端集成

**模块**：Harness 引擎  
**工单 ID**：`TASK-HARNESS-LLM-01`  
**优先级**：P2  
**来源**：实现无人值守技能描述生成与反思萃取的 LLM 算子基础  
**预计规模**：S (1 个迭代)

#### 1. 交付目标
- `ov.conf` 增加可选 `[harness.llm]` 配置块（`base_url`, `api_key`, `model`）；
- 若未配置则优雅降级回退至本地 VLM 代理服务 (`mimo-v2.5` on `:8317`)。

---

### 📌 P2: [ ] [TASK-INOTIFY-DEDUP-02] 智能 Intent+Session 粒度去重引擎 (Intent-Aware Skill Dedup)

**模块**：技能中心 FS Watcher + Harness 引擎  
**工单 ID**：`TASK-INOTIFY-DEDUP-02`  
**优先级**：P2  
**来源**：近10小时会话复盘 — 绝对 300s 物理时间去重误杀了短时间内不同意图对同技能的合法唤醒  
**预计规模**：S (1 个迭代)

#### 1. 现状与根因
- 之前为防止 grep/server 扫盘暴洪，设了绝对 300 秒时间窗口；
- 但如果用户在 5 分钟内连续下达了 2 个不同意图的指令唤醒同一技能，第 2 次合法唤醒会被误截流，导致唤醒率统计偏低。

#### 2. 交付目标
- 改为 `Session ID + Intent Hash` 动态判定去重：同 Session 同意图在 300s 内只计 1 次，新 Session 或新意图唤醒即刻计数。

---

### 📌 P2: [ ] [TASK-REALTIME-WS-01] 页面数据 SSE / WebSocket 实时推送更新 (Realtime Web UI Push)

**模块**：OpenViking Server + Web Studio  
**工单 ID**：`TASK-REALTIME-WS-01`  
**优先级**：P2  
**来源**：近10小时会话复盘 — 当用 CLI `ov add-resource` 或脚本操作时，首页上下文与技能列表需手动 F5 刷新  
**预计规模**：M (2 个迭代)

#### 1. 交付目标
- 在服务端 `/api/v1/events/stream` 建立 SSE 订阅通道；
- 当物理文件或数据库发生变动时，静默向 Web Studio 推送 `data_changed` 事件，前端自动无感知重新加载。

---

### 📌 P2: [ ] [TASK-SKILL-TAGS-01] 全量 260+ 技能动态标签与领域分类引擎 (Skill Tags & Category Classification)

**模块**：技能中心  
**工单 ID**：`TASK-SKILL-TAGS-01`  
**优先级**：P2  
**来源**：近10小时会话复盘 — 大多数技能卡片缺少 `tags`，难以在 260+ 技能中按维度快速维度过滤  
**预计规模**：S (1 个迭代)

#### 1. 交付目标
- 后端增加基于 `SCHEMA.md` 标签字典的自动分类器；
- 动态为技能注入 `[frontend]`, `[backend]`, `[testing]`, `[agent-core]` 等分类标签，支持前端一键多维度筛选。

---

### 📌 P2: [ ] [TASK-SKILL-DRAWER-01] 技能抽屉超长源码高亮与 TOC 目录结构化索引 (Drawer TOC & Syntax Highlighting)

**模块**：技能中心 Detail Drawer  
**工单 ID**：`TASK-SKILL-DRAWER-01`  
**优先级**：P2  
**来源**：近10小时会话复盘 — `L2 (全量源码)` 当 `SKILL.md` 超过 500 行时无目录导航且容易引发 UI 渲染长卡顿  
**预计规模**：S (1 个迭代)

#### 1. 交付目标
- 详情抽屉引入虚拟滚动 (Virtual List) 防止卡顿；
- 自动提取 markdown `#` 标题生成侧边 TOC 快捷跳跃目录。

---

### 📌 P2: [ ] [TASK-SERVER-DOCTOR-01] 全局系统健康探针与一键自愈面板 (System Doctor & One-Click Self-Healing)

**模块**：OpenViking Server + Studio Sidebar  
**工单 ID**：`TASK-SERVER-DOCTOR-01`  
**优先级**：P2  
**来源**：近10小时会话复盘 — 当 FastMCP 或 1933 掉线时，前端仅抛出通用 404/500，缺乏直观警报与修复入口  
**预计规模**：S (1 个迭代)

#### 1. 交付目标
- 侧边栏增加 `[系统健康诊断]` 状态指示灯与抽屉面板；
- 探针检测 1933 HTTP、FastMCP stdio、LevelDB 锁状态，遇到异常提供 `[一键重启/自愈 (ov server doctor)]` 触发按钮。


---

## 📅 第二部分：【远期规划 backlog 阶段：Phase 2 & Phase 3 — 技能自演进与在线创生】

> 说明：本阶段卡片来自 `ROADMAP.md`，当 Phase 1 核心打通并封板发版后，按顺序进入 Phase 2/3 开发。

---

### 🚀 Milestone Phase 2：技能自演进闭环与质量门禁引擎 (v1.3.x 目标)

#### 1. `[TASK-LOOP-01~07]` Epic-SKILL-LOOP 自进化闭环引擎
- `TASK-LOOP-01`：修正事件的数据模型与 SQLite 存储结构；
- `TASK-LOOP-02`：物理校验结果与异常 Trace 自动捕获；
- `TASK-LOOP-03`：`CONTEXT / REFLECTION / LESSON` 3 段式自动萃取器；
- `TASK-LOOP-04`：Lesson 候选变更人机协同审核 View；
- `TASK-LOOP-05`：`SKILL.md` 受控版本安全更新与 Git 自动回滚。

#### 2. `[TASK-SKILLOPT-01~03]` Epic-SKILLOPT 质量门禁引擎
- `TASK-SKILLOPT-01`：Attempt 执行引擎与 Judge Gate 评分验证器；
- `TASK-SKILLOPT-02`：技能健康评分与自动修复建议生成；
- `TASK-SKILLOPT-03`：技能权重动态微调与排名算法。

---

### 🚀 Milestone Phase 3：在线创生与端到端隐私安全治理 (v1.4.x / v2.0 目标)

#### 1. `[TASK-LIVEGEN-01~03]` Epic-LIVE-GEN Skill Live Generator
- `TASK-LIVEGEN-01`：SKILL.md 在线 Monaco 编辑器与 YAML Header 语法校验；
- `TASK-LIVEGEN-02`：沙盒环境模拟触发测试；
- `TASK-LIVEGEN-03`：一键自动向量化发布至 Viking 1933 存储。

#### 2. `[TASK-PRIVACY-01~03]` Epic-PRIVACY-GOV 敏感信息二次授权
- `TASK-PRIVACY-01`：服务端敏感字段检索二次过滤与鉴权；
- `TASK-PRIVACY-02`：前端脱敏展示与安全开关；
- `TASK-PRIVACY-03`：脱敏审计日志与导出隔离。

---

## 📦 第三部分：【历史已验收交付归档 (Delivery Archive)】

> 说明：本部分记录已完成开发、验收通过并打入 Git Tag 的物理历史工单。

- **`[TASK-SKILL-FILECOUNT-01]`** 技能卡片全量关联文件数准确透视 ✅
  - **交付 Tag**：`v1.2.35` | **Commit**：`22541b5`
  - **内容**：后端递归扫描 `file_count`，前端卡片动态精准呈现（如 `openviking-master` 显示 `4 文件`）。

- **`[TASK-METRICS-CONSOLIDATION-01]`** Harness 指标与全局去重修复 ✅
  - **交付 Tag**：`v1.2.34` | **Commit**：`c1312bd`
  - **内容**：`system.py` 注入 `active_skills_count` 与 5 分钟 inotify 去重感应。

- **`[TASK-HARNESS-LOGS-PERSISTENCE-01]`** Harness Logs 拦截日志物理持久化 ✅
  - **交付 Tag**：`v1.2.33` | **Commit**：`90812ab`
  - **内容**：解决 F5 刷新日志丢失问题，实现持久化落盘。
