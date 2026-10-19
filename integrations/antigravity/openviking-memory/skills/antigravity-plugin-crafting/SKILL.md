---
name: antigravity-plugin-crafting
description: >-
  Google Antigravity 与 Antigravity IDE 原生插件标准工程工法、脚手架构建与全生命周期开发指南。
  涵盖官方六大构件标准、芒格逆向八大避坑铁律、反重力桌面端与IDE双端自适应适配、双轨MCP注册、以及生命周期Hooks工业级防爆SOP。
---

# Google Antigravity 原生插件开发与工程工法指南 (Antigravity Plugin Crafting)

本技能为在 **Google Antigravity Desktop (桌面端)** 与 **Google Antigravity IDE (编程端)** 生态下，打造 100% 官方合规、非暴力、非入侵式原生插件的**单一真相源 (SSOT) 标准工程工法**。

---

## 🧭 一、 查理·芒格逆向工程思考 — 10 大“必死之招”与防御铁律 (Munger Inversion)

> “反过来想，总是反过来想（Invert, always invert）。如果我知道自己会死在哪里，那我将永远不去那个地方。” —— 查理·芒格

若想让一个反重力插件必死无疑、引发宿主崩溃或被用户唾弃，最有效的做法如下。**看清这 10 大死穴，反向构建防御，插件必然稳如磐石**：

| 序号 | 致命毒药 (Anti-Pattern) | 崩坏现象与物理根因 | 芒格逆向防御铁律 (Engineering Invariant) |
| :--- | :--- | :--- | :--- |
| **死穴 1** | **暴力打猴子补丁 / 篡改二进制** | 篡改 IDE 的 `app.asar` 或底层二进制。官方一更新，补丁失效，全量白屏或无法启动。 | **100% 走官方 Customization 规范**：依托 `plugin.json`、`hooks.json`、`mcp_config.json`，做到零二进制侵入，前向兼容升级。 |
| **死穴 2** | **Windows 控制台抛 GBK 报错** | 脚本崩溃时抛出未捕获异常，输出 CP936 字节。IDE 底层 Go 进程塞入 Protobuf string 字段时触发 `invalid UTF-8` 校验，引发推流死循环，前端彻底白屏。 | **stderr 物理静音 + 字节流直写**：强制使用 `sys.stdout.buffer` 直写 UTF-8 字节，物理封闭 stderr，全流程捕获 `BaseException`，退出码恒为 0（Fail-Open）。 |
| **死穴 3** | **Hook 管道无脑 `read()` 阻塞** | 以为 IDE 会发送 EOF，调用 `sys.stdin.read()`。IDE 管道保持开启等待回传，导致父子进程双向死锁，3 秒后被超时强杀。 | **单行流式读取**：严禁 `read()`，必须使用 `sys.stdin.readline()` 单行解析，时延极限压至 10ms。 |
| **死穴 4** | **裸调全局 Python 导致冷启动击穿** | Windows 裸启动 Python 会扫描全部全局 site-packages，耗时高达 3.3 秒，刚好击穿 IDE 3.0s 超时门禁。 | **纯标准库隔离三剑客 (`-E -s -S`)**：在 Hook 命令中强制配置 `python.exe -E -s -S <script>`，将冷启动耗时骤降至 40ms（快 80 倍）。 |
| **死穴 5** | **配置孤岛：仅配私有 MCP 导致主面板失明** | 仅在 `plugins/<name>/mcp_config.json` 中配置，桌面端主界面「MCP 服务器」列表与「Manage MCP servers」无法感知，沦为孤岛。 | **双轨注册机制 (Dual-Track MCP)**：既保留插件私有 `mcp_config.json`（内聚规范），安装器同时优雅联动全局 `~/.gemini/config/mcp_config.json`，实现双向点亮。 |
| **死穴 6** | **写死单端脑区路径，跨端即瘫痪** | 桌面端脑区路径为 `antigravity/`，IDE 端为 `antigravity-ide/`。硬编码任一路径会导致在另一端找不到会话与状态文件。 | **双端路径自适应嗅探**：看门狗脚本根据 payload 中的 `artifactDirectoryPath` 动态提取宿主类型，实现桌面端与 IDE 端无感切换。 |
| **死穴 7** | **机械步数一刀切，打断长线交付** | 写死单轮 18 步硬上限，在端到端交付、TDD 测试与收尾提交时连环弹窗误杀，破坏开发者心流。 | **自适应弹性增量租约**：36 步健康态 / 15 步警戒态 / 人类放行 +15 步租约 / 收尾文档白名单 / 轮次清零。 |
| **死穴 8** | **端侧就地魔改与多机人工穿刺** | 跑到 ~/.gemini/config/plugins/ 里打临时补丁，或逐台 SSH 到远程机器手动改文件。导致 10,000 台机器版本全部分裂断层，沦为不可控的“雪花环境”。 | **唯一公共源修改 + 单向拉取部署 (Pull-Only)**：严禁端侧就地改动。所有修复 100% 在统一源码中枢（OpenVikingStudio/integrations/）进行、严格 Bump 版本并提交 Git；客户端只通过标准一键拉取安装命令部署。 |
| **死穴 9** | **版本幽灵与硬编码断层** | 修改了工具或 Hook 但未递增 plugin.json 版本，或在 setup.py 中写死硬编码常数。导致 IDE 缓存跳过更新、版本覆盖报错或多节点状态漂移。 | **单一真相源 (SSOT) 动态直连 + 凡更必 Bump**：setup.py 动态解析 plugin.json 提取版本；母本、部署端、宿主 config.json 注册表与探针四位一体 100% 同频。 |
| **死穴 10** | **半拉子安装与拓扑盲盒** | 仅拷贝文件到 plugins 目录导致 IDE 未激活注册；本地 2080 环境盲目使用公网域名造成代理拦截与秒级延迟。 | **自适应拓扑探测 + 宿主注册表写入**：本地强制锁死 127.0.0.1:1933 环回与管理员凭据；setup.py 自动幂等写入 ~/.gemini/config/config.json 的 plugins 字段。 |

---

## 🏛️ 二、 Google 官方标准插件拓扑结构 (Official Plugin Topology)

根据 Google 官方规范（`https://antigravity.google/schemas/v1/plugin.json`），一个合规插件的标准拓扑结构如下：

```text
~/.gemini/config/plugins/<plugin-name>/   (或工作区级 .agents/plugins/<plugin-name>/)
├── plugin.json         # [必需] 官方标准清单声明 (含 Schema、名称、Logo 与推荐指令)
├── mcp_config.json     # [可选] 插件私有挂载的 MCP 服务器声明 (Stdio / SSE)
├── hooks.json          # [可选] 官方 5 大原生生命周期钩子反射配置
├── rules/              # [可选] 插件激活后自动注入的规则契约
│   └── *.md            # 纯 Markdown 规则 (如 AGENTS.md)，无需 Frontmatter
├── skills/             # [可选] 插件暴露的领域认知导轨
│   └── <skill-name>/
│       └── SKILL.md    # 带 YAML Frontmatter 的渐进式技能文档
├── scripts/            # [建议] 核心看门狗、守卫或辅助执行脚本
├── setup.py            # [建议] 跨平台一键开箱安装与双轨自举向导
└── README.md           # [建议] 插件详情页「概览」Tab 渲染的高密文档
```

---

## 📑 三、 核心文件配置规范与官方契约

### 1. `plugin.json`：大厂官方级清单规范
切忌只写 `name` 和 `description`，必须补齐官方完整要素：

```json
{
  "$schema": "https://antigravity.google/schemas/v1/plugin.json",
  "name": "agent-circuit-breaker",
  "displayName": "智能体自适应断路器",
  "version": "1.3.0",
  "description": "专为 Google 反重力打造的物理级自适应断路器，具备 36 步健康预算、Fail-Open 故障自愈与 force_ask 零误杀双重防护。",
  "logo": "https://vk.tide.red/studio/ov-logo.png",
  "suggestedPrompts": [
    "检查当前断路器健康状态与步数预算",
    "重置当前会话的断路器状态与报错计数",
    "查看断路器自省停手规则与三行事实交接契约"
  ],
  "author": {
    "name": "OpenViking Eco & Antigravity Squad"
  },
  "keywords": [
    "antigravity",
    "circuit-breaker",
    "guardrails",
    "fail-open",
    "adaptive-lease"
  ],
  "repository": "https://vk.tide.red",
  "license": "Apache-2.0"
}
```

### 2. `hooks.json`：官方合法 5 大生命周期钩子
官方**仅支持**以下 5 种事件，切勿编写非标事件名（如 SessionStart）：

| 官方事件名 | 触发时机 | 典型入参 | 典型出参能力 |
| :--- | :--- | :--- | :--- |
| **`PreToolUse`** | 工具执行前 | `toolCall`, `stepIdx` | `decision`: `"allow"` / `"deny"` / `"ask"` / `"force_ask"`, `reason`, `overwrite` |
| **`PostToolUse`** | 工具执行后 | `toolCall`, `error` | `{}` (用于监听记账，失败即时累加计数) |
| **`PreInvocation`** | 模型推理前 | `invocationNum` | `injectSteps`: `[{"ephemeralMessage": "..."}]` (临时温和预警注脑) |
| **`PostInvocation`**| 模型推理后 | `initialNumSteps` | `terminationBehavior`: `"force_continue"` / `"terminate"` |
| **`Stop`** | 循环准备终止时 | `terminationReason` | `decision`: `"continue"` (阻止终止并继续自愈) |

**标准 `hooks.json` 模板**：
```json
{
  "agent-circuit-breaker": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python.exe -E -s -S C:/path/to/circuit_guard.py pre-tool",
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python.exe -E -s -S C:/path/to/circuit_guard.py post-tool",
            "timeout": 10
          }
        ]
      }
    ],
    "PreInvocation": [
      {
        "type": "command",
        "command": "python.exe -E -s -S C:/path/to/circuit_guard.py pre-invocation",
        "timeout": 10
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "python.exe -E -s -S C:/path/to/circuit_guard.py stop",
        "timeout": 10
      }
    ]
  }
}
```

### 3. `mcp_config.json`：双轨集成规范
- **插件私有声明**：放在 `plugins/<name>/mcp_config.json`，供进入插件详情页时点亮。
- **全局管理穿透**：通过 `setup.py` 联动写入 `~/.gemini/config/mcp_config.json`，让桌面端主面板底栏与「Manage MCP servers」可直接看到并控制。

---

## 🔄 四、 双端自适应适配规范 (Desktop vs IDE)

在编写守护脚本（如 `circuit_guard.py`）时，必须做到自动适配两端差异：

```python
def detect_antigravity_runtime(payload: dict) -> str:
    """
    自适应判定当前宿主环境：
    - 'ide': Antigravity IDE 编程端 (~/.gemini/antigravity-ide/)
    - 'desktop': Antigravity Desktop 桌面端 (~/.gemini/antigravity/)
    - 'cli': Antigravity CLI (~/.gemini/antigravity-cli/)
    """
    art_path = payload.get("artifactDirectoryPath", "")
    trans_path = payload.get("transcriptPath", "")
    full_str = f"{art_path}|{trans_path}".lower()
    
    if "antigravity-ide" in full_str:
        return "ide"
    elif "antigravity-cli" in full_str:
        return "cli"
    else:
        return "desktop"
```

### 针对 IDE 端的特定护栏增强：
1. **单文件 500 行红线防御**：在 `PreToolUse` 检测 `TargetFile`，若该文件在工作区且行数达到 450~500 行，主动求证或提醒进行领域接缝拆解；
2. **同文件频繁报错打补丁震荡检测**：同文件连续 3 次写操作且伴随 `error`，强制触发 `force_ask` 阻止盲目死循环；
3. **收尾文件免检**：良性状态下对 `REFACTORING_PLAN.md`、`README.md` 免受步数限制，保障临门一脚提交顺畅。

---

## 🛠️ 五、 新插件极速脚手架生成器 (Scaffolding Helper)

后续打造任何全新反重力插件时，运行以下标准模板即可秒级初始化合规骨架：

```bash
# 进入插件根目录
cd ~/.gemini/config/plugins/
# 建立标准拓扑
mkdir -p my-plugin/{scripts,rules,skills/my-plugin-ops,assets}
```

**自举与验证验收三步法**：
1. **静态清单校验**：验证 `plugin.json` 是否包含 `displayName` 与 `$schema`；
2. **Hook 隔离探活**：运行 `python.exe -E -s -S scripts/guard.py pre-tool`，确保 50ms 内返回合法 JSON 且 stderr 为空；
3. **UI 视觉验收**：在反重力桌面端或 IDE 中打开「自定义项 ➔ 已安装」，验证 Logo、名称、5 大 Tab（概览/技能/MCP/钩子/规则）是否完整点亮。
