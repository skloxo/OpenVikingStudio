---
name: living-asset-system
description: '全项目通用四大活态自驱系统与资产复用体系 (Living Asset & Self-Driving System) — 彻底终结死文档、重复手搓轮子与架构退化。包含开工查库第一潜意识、全景资产档案库、物理视网膜测试门禁与 Harvest-as-You-Go 完工回填自演进闭环。触发词: 活态自驱, 公共组件, 复用轮子, 资产盘点, 解耦复用, living-assets, 查库第一, 避免重复造轮子, 轮子归档'
---

# 🧬 全项目通用四大活态自驱系统与资产复用体系 (Living Asset System v1.0)

> **"A codebase without living tests is dead; a component library without subconscious habits is phantom."**  
> **没有自动化守护的规范是死规范，没有活水注入的库是死库。**  
> 本技能为跨项目、跨技术栈、全局常驻默认加载的最高工程防御与资产沉淀体系。

---

## 🌌 一、 第一性原理：为什么 99% 的公共组件库都会沦为死库？

在软件工程实践中，存在著名的**“死文档悖论与重复手搓黑洞”**：
1. **认知盲区**：开发者/AI 在接到新需求时，直觉是“立刻在当前文件写业务逻辑”，根本不会主动去翻看庞大复杂的历史文档；
2. **碎片化手搓**：同一个剪贴板、分页器、格式化函数、确认弹窗在 8 个不同页面被重复手搓 8 遍，实现各异，暗藏 Bug（如非 HTTPS 下 Clipboard 报错）；
3. **缺乏物理反馈**：新增了重复代码没有任何报错，即使建了规范文档，无人更新也不会导致构建失败，系统不可逆地走向熵增与退化。

**四大活态自驱系统 (Four-Dimensional Living Defense)** 从物理层彻底击穿这一顽疾：
通过**“潜意识反射 ➔ 统一档案库 ➔ 视网膜门禁 ➔ 完工自演进”**四位一体闭环，让公共资产像生命体一样活起来，越用越丰富，且 100% 具备机器级强防线。

---

## 🛡️ 二、 四大活态自驱维度全息矩阵 (The 4D Living Matrix)

```text
                                  【维度一：潜意识神经反射 (Subconscious Reflex)】
                           开工查库第一律 ｜ 任何编码任务启动前下意识检索资产库
                                                   │
                                                   ▼
                                  【维度二：全景资产档案库 (Living Inventory SSOT)】
                           COMPONENT_AND_WHEEL_INVENTORY.md ｜ 分级卡片 ｜ 一览无余
                                                   │
                                                   ▼
                                  【维度三：物理视网膜测试门禁 (Test Retina Gatekeeper)】
                           component-inventory.test.ts ｜ 自动化扫描 ｜ 未登记物理阻断构建
                                                   │
                                                   ▼
                                  【维度四：完工自回填与体外大脑 (Harvest-as-You-Go)】
                           顺手牵羊提纯 ｜ 回填档案库 ｜ 双写 OpenViking Master Memory
```

---

## ⚡ 三、 4D 核心运行规约与落地标准

### 维度一：开工查库第一律 (Search First SSOT)
- **物理契约**：任何编码操作（无论是新建页面、抽屉、列表还是工具函数），**第一步必须在项目资产库中按关键词检索已有轮子**；
- **防线内化**：严禁在未确认是否有现成轮子的情况下直接敲写功能代码。若发现已有相似轮子，**必须 100% 复用**；若功能有细微差异，**优先扩展原轮子**而非另立门户。

### 维度二：全景资产档案库规范 (Inventory SSOT)
每个项目在 `docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md`（或对应标准路径）维护唯一资产档案，严格执行**三级资产分类法**：
1. **基础原子资产 (Primitives)**：按钮、输入框、微胶囊 Badge、卡片容器、骨架屏等通用 UI 原子；
2. **复合业务轮子 (Composite Wheels)**：通用审计抽屉、分页控制器、通用确认弹窗、动态图表容器等；
3. **数据与逻辑轮子 (Logic & Pure Utilities)**：统一网络客户端、安全剪贴板 (`copy-button`)、跨端格式化器 (`formatBytes`, `formatDuration`)、本地存储代理等。

### 维度三：物理视网膜门禁 (Test Retina Gatekeeper) ⭐⭐⭐⭐⭐
- **第一性原理**：靠人自觉必会遗漏，必须由机器代码充当 Agent 的“视网膜”，用测试红绿灯直接阻断侥幸心理；
- **自动化测试守卫机制**：
  - 在单测套件中配置 `component-inventory.test.ts`（或对应语言的测试脚本）；
  - 测试**自动扫描所有组件目录**（如 `src/components/ui/`、`src/components/common/`）；
  - 将扫描到的物理文件名与 `COMPONENT_AND_WHEEL_INVENTORY.md` 进行集合差集比对；
  - **断言铁律**：只要发现有任何一个组件未在档案库登记，测试**直接判定失败抛出红灯**，构建与 CI/CD 流程物理阻断！

### 维度四：完工自回填与体外大脑双写 (Harvest-as-You-Go)
- **顺手牵羊提纯 (Harvest-as-You-Go)**：在开发任何业务模块时，只要提取了解耦度高、具备通用价值的组件或函数，在提交前**顺手登记回填档案库**；
- **体外大脑持久化**：将新收割的轮子名称、接口签名与设计决策，通过 `openviking_record_evolution_lesson` 或 `openviking_write` 同步至体外大脑 (`viking://resources/master_memory/`)，让跨项目、跨会话的任何 Agent 都能在第一时间调用。

---

## 🛠️ 四、 跨技术栈极速接入脚手架 (3-Minute Onboarding)

### 1. 前端生态 (TypeScript / React / Vue / Vitest / Jest)
在项目的 `src/components/` 下创建 `component-inventory.test.ts`：

```typescript
import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

describe('Living Component Inventory SSOT Guard', () => {
  const inventoryPath = path.resolve(__dirname, '../../docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md');
  const inventoryContent = fs.readFileSync(inventoryPath, 'utf-8');

  it('every UI primitive component must be registered in inventory', () => {
    const uiDir = path.resolve(__dirname, 'ui');
    if (!fs.existsSync(uiDir)) return;
    const files = fs.readdirSync(uiDir).filter(f => f.endsWith('.tsx') && !f.includes('.test.'));

    const missing = files.filter(file => {
      const baseName = file.replace('.tsx', '');
      return !inventoryContent.includes(`\`${file}\``) && !inventoryContent.includes(`\`${baseName}\``);
    });

    expect(missing, `❌ 未登记组件导致构建阻断！请将以下组件补充登记至 COMPONENT_AND_WHEEL_INVENTORY.md: ${missing.join(', ')}`).toEqual([]);
  });
});
```

### 2. 后端生态 (Python / Pytest)
在项目的 `tests/` 下创建 `test_asset_inventory.py`：

```python
import os
import pytest

def test_shared_utils_registered_in_inventory():
    inventory_path = "docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md"
    assert os.path.exists(inventory_path), "缺少资产档案库文档！"
    with open(inventory_path, "r", encoding="utf-8") as f:
        content = f.read()

    utils_dir = "my_app/utils"
    if os.path.exists(utils_dir):
        files = [f for f in os.listdir(utils_dir) if f.endswith(".py") and not f.startswith("__")]
        missing = [f for f in files if f not in content]
        assert not missing, f"❌ 未登记工具模块: {missing}，请登记至 {inventory_path}"
```

---

## 🔄 五、 技能自演进与反思履历 (Self-Evolution Loop)

本技能践行**自产自销 (Dogfooding)** 铁律：每当在任何项目中踩坑或提炼出新的资产守护形态，必须按照标准反思三段式将新教训写回本技能与体外大脑。

#### 📌 Lesson 2026-09-10：四大活态自驱系统击穿死文档与重复造轮子黑洞
- **CONTEXT**：在 OpenVikingStudio 代码全景扫描中，发现同一项目中存在 8 处手搓剪贴板复制逻辑、4 处各异的分页控制器、7 处 formatBytes 重复定义，以及 2 个废弃未用的抽屉组件。同时历史文档众多，但开发时极易遗忘查阅。
- **REFLECTION**：单纯编写文档无法阻止人类与 AI 的惰性与遗忘。唯有将规则转化为“机器维度的单测视网膜（如 component-inventory.test.ts）”，新文件未登记直接 CI 阻断，配合“开工查库第一”的潜意识反射和“Harvest-as-You-Go”完工回填，才能实现资产与文档的永久共生与活态自驱。
- **LESSON**：跨项目全面推行四大活态自驱系统 (1D 潜意识 ➔ 2D 档案库 ➔ 3D 视网膜 ➔ 4D 自演进)。所有新老项目开工第一件事：查库；完工最后一件事：回填并跑通视网膜测试。


#### 📌 Lesson 2026-09-10：四大活态自驱系统独立技能化与全项目默认常驻加载
- **CONTEXT**：用户高度认可“四大活态自驱系统”（潜意识反射、资产档案库、视网膜门禁、Harvest-as-You-Go 自演进），要求将其提炼为所有开发项目通用的默认使用加载的核心技能与研发规范，并且必须默认加载、持续完善迭代。
- **REFLECTION**：软件工程中 99% 的公共组件库与文档都会沦为“死库”与“死文档”，导致开发者/AI 不断重复手搓剪贴板、分页器、格式化函数。纯文档规范无法约束惰性，唯有将资产登记与单测视网膜硬核绑定（新组件未登记直接 CI 阻断），配合开工潜意识反射与完工回填自演进，才能实现公共轮子越滚越多且 100% 保持单一真相源。
- **LESSON**：1. 正式创建全局通用一级独立技能 living-asset-system (四大活态自驱与资产复用体系)，包含四维矩阵、TS/Python 极速接入脚手架及自演进机制。
2. 深度融入顶级通用总控技能 master-dev 的【法】(Fa) 层，与 TDD、Auto-PR 并列为开局必检必开工序。
3. 注入全局潜意识规则 AGENTS.md 第一章第 10 项自动触发矩阵与第四章第 11 节铁律，实现全项目、全会话默认常驻加载。
4. 明确四大活态自驱机制：1D 潜意识查库反射 ➔ 2D COMPONENT_AND_WHEEL_INVENTORY.md 档案库 ➔ 3D component-inventory.test.ts 视网膜门禁阻断 ➔ 4D Harvest-as-You-Go 完工回填与体外大脑双写。
