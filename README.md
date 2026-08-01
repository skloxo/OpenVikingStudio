# 🚀 OpenViking Studio — 极客 Agent & 技能自演进全栈中枢 (v1.2.0 Release)

> **全栈架构重归与正名**：**OpenViking Studio** 过去最初定义为 Wiki 的前端控制台。然而在实际落地与迭代中，前端与后端逻辑深度绑定（包括 MCP 物理探针、FastMCP 1933 路由、`~/.openviking/harness_metrics.json` 磁盘算子及 Vite 网关中间件）。
> **现正式更名与升级为【前后端全栈一体化项目】**——我们不仅持续精修极客 Web UI 界面，同时也对 Python 后端服务与网关中间件进行物理级深度迭代与代码推送，确保系统“数据绝对真实、全自动无干预自演进”。

---

## 🌟 核心功能与全栈能力 (Features)

### 1. 🧠 技能中心与 Harness 自演进中枢 (`/skills`)
- **6 大高密度 KPI 观察阵列 (3×2 矩阵)**：物理绑盘隐式自动唤醒率、技能运行成功率、VK 技能统一收敛率、**技能资产活跃复用率**、**Context 提示词压缩率**与 Harness 技能自演进。
- **全全全全全自动零按钮治理**：感知到 Wiki 或外部新技能入库后，Harness 引擎后台自动补全 `description` 描述、自动进行规范标准化与 FastMCP 1933 向量上架，彻底消灭冗余手动按钮。
- **双门锁极客分类**：微圆角同行 Scope 筛选栏 (`全部` / `🤖 Agent 专用` / `👤 User 偏好`)，嵌套右对齐 `🔍 搜索技能...` 框。
- **白盒反思审计**：点击可直接调阅 `/harness-logs` 物理 Lesson 审计日志，与 OpenViking 跨会话体外大脑 (`viking://resources/master_memory/`) 物理同频。

### 2. 📋 任务中心 Task Center (`/tasks`)
- **全自动消费流转**：后台 Task Consumer 秒级自动拾取，实现 `pending` ➔ `running` ➔ `completed` 无感全流转。
- **队列自愈与滤重**：针对重新入队的 Task 自动做隐去滤重，规避失败列表污染。

### 3. 📁 资源与图谱管理器 Resource Explorer (`/resources` & `/graph`)
- **Viking Graph 图谱可视化**：以图形化方式直观展示 `viking://resources/` 节点拓扑与属性树。
- **文本与片段查看器**：深度调阅任意 L0 / L1 / L2 数据切片及 Embedding 向量关联。

### 4. 📊 物理运行监控监控大盘 (`/monitoring`)
- **零 Mock 绝对真实性**：全盘遵循【绝对数据真实性】铁律，彻底清洗假数据与拟造满分，无采样时物理直白显示 `--`。
- **24H 动态滚动统计**：全盘采用 24H Rolling 窗口，提供精准的时效性架构决策支撑。

---

## 📦 快速开始 (Quick Start)

### 1. 安装依赖
```bash
npm install
```

### 2. 本地全栈开发模式
```bash
npm run dev
```
控制台默认将在 `http://127.0.0.1:1936/studio` 启动。

### 3. 构建生产包
```bash
npm run build
```
自动编译打包输出至 `dist/`，并同步部署至本地 OpenViking 运行环境。

---

## 🎉 Release v1.2.0 全量更新日志 (Full Release Notes)

自 **v1.1.0** 升阶至 **v1.2.0**，项目经历了全方位物理级重构与连通：

### 🛠️ 1. 前后端一体化全栈治理
- **后端打点与探针强化**：在 `mcp-openviking` 后端及 Vite 代理网关层深度嵌入 `harness_metrics` 物理算子，打通磁盘 `harness_metrics.json` 实时读写。
- **技能自演进算法**：建立了“感知 ➔ 描述自动生成 ➔ 规范标准化 ➔ FastMCP 1933 向量上架 ➔ Reflexion 反思”的 5 阶全自动闭环。

### 🎨 2. 技能中心 UX 极致精修 (v1.1.24 ~ v1.1.25)
- **6 大高价值 KPI 矩阵**：将观察卡片扩充为 3×2 平铺矩阵，新增 `技能资产活跃复用率`（透视僵尸技能）与 `Context 提示词压缩率`（度量 Token 降本）。
- **极客 Header 与对齐**：切除标题下方的 `border-b` 冗余横线，使用 `items-end` 布局使 `3小时 Rolling` Badge 与副标题基线 **100% 物理平齐**。
- **微圆角控件内嵌**：将搜索框下移并嵌套嵌入 Scope 分类筛选栏同行右侧。

### 🛡️ 3. 0 Mock 绝对数据真实性铁律
- **彻底清洗假数据**：删除了 `98.6%` 等静态硬编码字符串，纠正了空数据时伪造 `100.0%` 的 fallback，采样为空时统一优雅显示 `--`。

---

## 📜 许可证 (License)

[MIT License](LICENSE)


Apache-2.0 License.
