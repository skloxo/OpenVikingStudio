---
name: circuit-breaker-ops
description: >-
  Antigravity 原生熔断断路器运维与跨节点（如 3070 客户端）同步指南。
  涵盖 Fail-Open 架构、force_ask 零误杀机制、阈值调优、以及多客户端跨机部署 SOP。
---

# Antigravity 断路器护栏运维与跨机部署指南 (Circuit Breaker Ops)

## 一、 核心架构与设计思想

本系统为解决自主智能体（Agent）长时间盲目自嗨、连续报错打补丁、烧光 Token 与陷入死循环而设计。

1. **官方标准原生纳管**：
   - 依托 Antigravity 官方 `plugins/` 体系与 `hooks.json` 生命周期规范；
   - 绝不入侵二进制、不打 Monkey Patch，随 Antigravity 官方版本迭代 100% 前向兼容。
2. **Fail-Open（故障自愈）铁律**：
   - 拦截脚本自身发生任何未知异常时，最坏情况自动放行（`allow`），绝对不因护栏故障拖垮 IDE 正常工具调用。
3. **`force_ask` 零误杀机制**：
   - 触发连续 3 次写报错、单轮超过步数限制、或同文件震荡时，系统不作一刀切 `deny`，而是唤起官方 `force_ask` 弹窗；
   - 开发者如果是合法的长重构或 TDD，随手点击“允许”即可继续，消灭假阳性。
4. **只读探索免检**：
   - `view_file`、`grep`、`read_url_content`、`openviking_*`、`keepass_*` 等只读与查询工具 0 延迟直接放行，完全不计入报错计数。

---

## 二、 插件目录规范

插件位于标准路径：`~/.gemini/config/plugins/agent-circuit-breaker/`

```text
agent-circuit-breaker/
├── plugin.json               # 官方插件清单声明
├── setup.py                  # 跨平台一键自举安装/卸载向导 (自动生成绝对路径与 Fail-Open Hooks)
├── server.py                 # MCP Server (暴露 circuit_breaker_status / reset 工具)
├── mcp_config.json           # 暴露给 Antigravity 的 MCP 声明
├── hooks.json                # 原生生命周期钩子配置 (PreToolUse / PostToolUse / PreInvocation)
├── rules/
│   └── AGENTS.md             # 熔断触发后的停手与三行汇报规则契约
├── scripts/
│   └── circuit_guard.py      # 核心看门狗拦截脚本 (Fail-Open, 跨平台)
└── skills/
    └── circuit-breaker-ops/
        └── SKILL.md          # 运维与跨机同步文档 (本文件)
```

---

## 三、 客户端一键开箱安装 SOP

在任何客户端或远程节点上，**严禁且无需人工手动敲命令修改配置文件**，直接使用自举安装向导：

### 1. 本地快速一键安装 (Windows / Linux / macOS)
从 OpenViking Studio 插件中心下载或通过命令安装：
```bash
# Windows PowerShell
python setup.py install

# Linux / macOS
python3 setup.py install
```
向导会自动检测操作系统、绑定当前 Python 解释器绝对路径、写入 `-E -s -S` 隔离参数、生成 `hooks.json` 并注册至 `~/.gemini/config/config.json`，无需重启 IDE。

### 2. 状态放行验证
```bash
python scripts/circuit_guard.py pre-tool
# 应输出: {"decision": "allow"}
```

---

## 四、 核心参数调优 (`scripts/circuit_guard.py`)

如需调整灵敏度，直接修改 `scripts/circuit_guard.py` 头部常量：

- `MAX_CONSECUTIVE_FAILURES = 3`：连续写/执行报错上限（触发 force_ask）。
- `BASE_HEALTHY_STEP_LIMIT = 36`：健康全绿灯状态下的单轮步数上限（支持大型组件与测试交付）。
- `BASE_UNHEALTHY_STEP_LIMIT = 15`：异常/有报错状态下的警戒步数上限（防止死循环打补丁）。
- `LEASE_EXTENSION_STEPS = 15`：用户点击放行后自动追加授予的增量探索租约（彻底消灭连环夺命弹）。
- `FINALIZATION_FILE_KEYWORDS`：良性收尾与文档记录文件（`refactoring_plan.md` 等，健康状态下豁免步数护栏直接放行）。
- `MAX_SAME_FILE_TOUCHES = 3`：同文件连续写入震荡检测上限。

---

## 五、 Windows 平台高可用防核爆五大避坑铁律

1. **纯标准库隔离参数 (`-E -s -S`)**：避免 Windows Python 扫描 site-packages 造成 3.3s 延迟超时，压缩至 40ms。
2. **严禁使用 `sys.stdin.read()`**：IDE 管道常开，必须使用 `sys.stdin.readline()` 避免永久挂死。
3. **Win32 原生 PE 直调**：严禁通过 bat/cmd 包装，防止跨工作区丢失命令。
4. **stderr 物理屏蔽与 GBK 零投毒**：stdout.buffer 直写 UTF-8，彻底屏蔽 stderr，杜绝 Go 进程 UTF-8 校验爆炸导致的会话白屏。
5. **Fail-Open 托底**：任何异常必须回退 `{"decision": "allow"}`，exit code 恒为 0。

---

## 六、 插件全生命周期研发、打包发版与 SSOT 治理铁律 (Plugin SSOT Pipeline)

> 🚨 **高压红线**：严禁直接在单台机器的 `~/.gemini/config/plugins/agent-circuit-breaker/` 目录私自打补丁！任何临时打补丁的行为都会制造本地配置孤岛，导致多机节点与后续 Agent 无法继承。

### 1. 物理源码唯一事实源 (SSOT)
- **源工程物理根目录**：`OpenVikingStudio/integrations/antigravity/agent-circuit-breaker/`
- 所有的规则契约 (`rules/AGENTS.md`)、生命周期钩子 (`hooks.json`)、MCP 声明 (`mcp_config.json`) 及看门狗参数，**必须且只能在源工程内修改**。

### 2. 四步标准研发与发版流水线 (Release SOP)

```text
[源工程代码/规则更新]
        │
        ▼
[plugin.json 递增版本号 (SemVer)]
        │
        ▼
[Python 扁平打包至 public/agent-circuit-breaker-<version>.tgz]
        │
        ▼
[VK 插件中心面向全生态分发 (https://vk.tide.red/plugins)]
        │
        ▼
[同步解压覆盖本机 ~/.gemini/config/plugins/ 完成闭环]
```

### 3. 一键标准打包代码范式 (Python Tarfile)
```python
import os, tarfile, shutil

src = 'C:/Users/Skl/Desktop/coding/OpenVikingStudio/integrations/antigravity/agent-circuit-breaker'
pub = 'C:/Users/Skl/Desktop/coding/OpenVikingStudio/public'
local_runtime = 'C:/Users/Skl/.gemini/config/plugins/agent-circuit-breaker'

# 1. 打包输出
for out_name in ['agent-circuit-breaker-1.3.2.tgz', 'agent-circuit-breaker.tgz']:
    with tarfile.open(os.path.join(pub, out_name), 'w:gz') as tar:
        for item in os.listdir(src):
            if not item.startswith('.') and item != '__pycache__':
                tar.add(os.path.join(src, item), arcname=item)

# 2. 同步覆盖本地运行时
for item in os.listdir(src):
    if not item.startswith('.') and item != '__pycache__':
        s, d = os.path.join(src, item), os.path.join(local_runtime, item)
        if os.path.isdir(s):
            if os.path.exists(d): shutil.rmtree(d)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)
```

