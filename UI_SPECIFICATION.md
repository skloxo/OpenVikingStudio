# OpenViking Studio 视觉与高密布局规范 (UI Visual & Density Specification)

> **🎯 设计核心目标：参考 tedtrading 高密数据看板风格**
> 1. **高信息密度 (High Information Density)**：收紧边距与内边距，在尽可能小的视口面积内展示最多有效数据。
> 2. **精致微圆角 (Compact Border Radius)**：收紧过大圆角（从 `rounded-xl/2xl` 收紧至 `rounded-md` 4px-6px），展现硬朗、专业的 Terminal / Trading 质感。
> 3. **极简间距 (Tight Spacing System)**：收紧组件间 `gap` 与 `padding`，消除不必要的空白浪费。

---

## 📐 1. 设计 Token 标准

| 元素类型 | 统一标准 (Target Class) | 优化对比说明 |
| :--- | :--- | :--- |
| **卡片/面板圆角** | `rounded` (4px) / `var(--radius: 0.25rem)` | ✅ 用户已验收：统一使用 4px 微圆角 |
| **按钮/输入框圆角** | `rounded-sm` (3px-4px) | 提升精细度，配合硬朗 Terminal 质感 |
| **标签 Badge 圆角** | `rounded-xs` (2px) | 紧凑精致微圆角 |
| **面板内边距 (Padding)** | `p-3` (12px) 或 `p-3.5` | 从 `p-6` (24px) 减半，空间利用率提升 50%+ |
| **组件间距 (Gap)** | `gap-2` (8px) / `gap-3` | 缩减大空白间距 |
| **表格行高 (Row Height)** | `h-8` (32px), `py-1.5` | 紧凑型列表排版 |
| **字体字号 (Typography)** | 数值/代码用 `font-mono text-xs/text-sm` | 高可读性、对齐紧凑 |

---

## 🔗 2. 任务卡片与修改摘要模板

每个重构版本卡片均遵循以下格式进行说明与关联：

```markdown
### [Task-v1.0.X] 任务名称
- **修改目标**：说明具体要改哪个组件/页面
- **修改逻辑**：根据什么逻辑去改（如：应用 UI_SPECIFICATION 高密规范）
- **关联规范**：[UI_SPECIFICATION.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/UI_SPECIFICATION.md)
- **修改文件**：受影响的源码路径
- **验收标准**：明确的 1-2 条验收操作
```

---

*文档保存路径：`/home/skloxo/aho/openclaw/project/OpenVikingStudio/UI_SPECIFICATION.md`*
*更新时间：2026-07-27*
