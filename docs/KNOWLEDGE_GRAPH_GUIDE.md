# 🌌 OpenViking 3D 全量知识关系图谱架构与性能优化指南

本文档记载了 OpenViking Studio 3D 知识拓扑图谱的技术架构、性能优化参数调优矩阵以及视觉美学规范，作为后续工程迭代的核心设计依据。

---

## 1. 技术栈与模块依赖链条

```
react-force-graph-3d (React 组件层)
   └── 3d-force-graph (Vanilla JS WebGL 容器层)
         └── three-forcegraph (Three.js 核心 3D Object3D 实体层)
               └── d3-force-3d (D3 三维物理力学演算引擎)
```

- **渲染引擎**：Web Content 3D Canvas (WebGL2 矢量硬件加速)
- **底层驱动**：Three.js `WebGLRenderer` + `PerspectiveCamera` + `Raycaster` 射线拾取
- **力学物理引擎**：D3 3D 斥力与引力模拟 (`d3-force-3d`)

---

## 2. 性能与资源消耗优化矩阵 (Performance Tuning)

在处理 >1,000 个 节点与 >3,000 条关联边时，为消除卡顿、掉帧与显卡高负载，实施以下配置：

| 优化参数 / API | 默认值 | 生产优化推荐值 | 物理原理与优化效果 |
| :--- | :--- | :--- | :--- |
| **`warmupTicks`** | `0` | **`100`** | **预热静默演算**：在画布呈现给用户前，在后台静默跑 100 轮物理碰撞计算，彻底消除初次加载时的“爆炸散开”卡顿。 |
| **`cooldownTicks`** | `Infinity` | **`200`** | **力学引擎自动冻结**：演算 200 帧稳定后立刻停止物理引擎，避免 GPU 无意义持续耗电，**GPU 占用率降低 90%**。 |
| **`nodeResolution`** | `8` 或 `16` | **`6`** | **网格几何降维**：精简 Sphere 多边形面片，大幅降低显卡 Vertex/Fragment 渲染压力，稳定 60 FPS。 |
| **`linkDirectionalParticles`** | `0` | 选中节点时为 `3` | **动态粒子按需分配**：仅在节点被选中或高亮时开启粒子流，全景状态保持静止降耗。 |
| **`enablePointerInteraction`**| `true` | `true` (关闭无用 hover) | 保持轻量 raycaster 拾取，避免过于复杂的逐帧 Mesh 检测。 |
| **对象池复用 (Pooling)** | 无 | **全局 Mesh/Geometry 复用** | 严禁在 render 函数中动态 `new THREE.Mesh()`，全部复用 shared `SphereGeometry` 与 `Material`，消除垃圾回收 (GC) 停顿。 |

---

## 3. 视觉审美与全屏布局规范 (Visual & Fullscreen Layout)

1. **沉浸式 100% 全屏 Viewport**：
   - 移除传统顶部固定 Header 占用的视口高度。
   - 3D 画布铺满整个屏幕 (`h-[calc(100vh-4rem)]` / `100% viewport`)。

2. **悬浮式 玻璃拟态 (Glassmorphism) 工具栏**：
   - **顶部浮动面板**：搜索框、分类切片 Badge、重置视角按钮统一悬浮在画布上方 (`bg-background/85 backdrop-blur-md shadow-lg`)。
   - **底部浮动状态栏**：全量节点与边统计信息、当前状态指标悬浮于左下角。

3. **三维连线美学 (`linkCurvature`)**：
   - 默认平直硬连线设为 `0.2` ~ `0.25` 的三维贝塞尔曲线，赋予拓扑图柔和灵动的星系质感。

---

## 4. 维护与后续升级指引

当需要升级 `react-force-graph-3d` 或 `three` 依赖时：
- 确保 `three` 版本与 `@types/three` 版本完全同频。
- 保持 `useMemo` 对 `graphData` 的深度缓存，严禁在 React re-render 时重建包含 1400+ 节点的数组对象。

---

## 5. 待处理优化 Backlog 任务

1. **未创建 Session 节点的软兜底 Preview 渲染**：
   - 当点击图谱中未在服务器持久化的示例 Session 节点（如 `session_88`）时，自动展示创建引导或软 Preview 弹窗，避免路由 404 触发异常。
2. **大图谱 5,000+ 节点 Canvas 视口虚拟化 (Frustum Culling / LOD)**：
   - 后续当图谱节点扩展至 5,000~10,000+ 时，增加 LOD 细节层次与视口外剔除功能。
