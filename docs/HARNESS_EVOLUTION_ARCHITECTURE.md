# Harness 自进化架构规范与多 Agent 交互设计 (Harness Evolution Architecture Specification)

本文档详细记录了在多智能体 (Multi-Agent) 与跨节点 (Windows / WSL / Linux) 环境下，**Harness 战衣外骨骼规范** 与 **OpenViking 1933 记忆中枢** 的自进化闭环设计。作为 Task Cards v1.1.38 ~ v1.1.41 的物理实施依据。

---

## 一、 系统架构与组件定位 (System Architecture & Roles)

1. **OpenViking 1933 (中央大脑与记忆中枢 / Single Source of Truth)**:
   - 托管全量 1.7GB 向量数据库 (cuVS + Qwen3-Embedding-8B + qwen3-reranker-0.6b)。
   - 提供 `master_memory` 存储与 85 个技能规范的 API 统一调度。
   - 暴露标准的 FastMCP 与 HTTP REST 接口，不进行任何后台外挂死循环轮询。

2. **Harness 战衣规范层 (Harness Specification Layer)**:
   - 为每个 Agent（Antigravity、OpenClaw、Hermes）提供统一的四阶段执行与演进 Hook。
   - 保证零大模型参数微调，依靠纯外部规则 (`SKILL.md`) 与内存/向量索引实现毫秒级自进化。

3. **多智能体实例 (Multi-Agent Instances)**:
   - **Antigravity IDE**: 运行在 Windows / WSL 环境。
   - **OpenClaw**: 运行在 Linux 宿主环境。
   - **Hermes**: 运行在 Linux 宿主环境。
   - 每一个 Agent 请求 OpenViking 时均携带统一 HTTP Header 标识：
     - `X-OpenViking-Actor-Peer`: `antigravity` / `openclaw` / `hermes`
     - `X-OpenViking-Node-ID`: `win-2080ti` / `wsl-ubuntu` / `linux-host`

---

## 二、 系统架构与拓扑图 (Architecture Topology)

```mermaid
graph TD
    subgraph 中央大脑与规则中枢 [OpenViking Central Hub - Port 1933]
        OV_Mem[(Master Memory 1.7GB 向量库)]
        OV_Skills[85 个 SKILL.md 技能中心]
        OV_API[FastMCP & REST API 网关]
    end

    subgraph Harness 外骨骼规范层 [Harness Engine Specification]
        H_Pre[Pre-Task: 自动召回 Hook]
        H_Run[Runtime: 控制台日志捕获]
        H_Post[Post-Task: 避坑经验萃取]
    end

    subgraph 多智能体个体 [Multi-Agent Instances]
        Agent_AG[Antigravity IDE - WSL/Win]
        Agent_OC[OpenClaw Agent - Linux]
        Agent_HM[Hermes Agent - Linux]
    end

    Agent_AG -->|穿戴套用| Harness 外骨骼规范层
    Agent_OC -->|穿戴套用| Harness 外骨骼规范层
    Agent_HM -->|穿戴套用| Harness 外骨骼规范层

    Harness 外骨骼规范层 <==>|双向同步 X-OpenViking-Actor-Peer| OV_API
    OV_API <--> OV_Mem
    OV_API <--> OV_Skills
```

---

## 三、 自进化 Loop 数据流 (Self-Evolution Data Flow)

```mermaid
flowchart TD
    Start[1. Agent A 收到任务指令] --> PreCheck[2. Pre-Task: 向 1933 发起 openviking_find]
    PreCheck --> Recall[3. 载入 Viking 中的避坑 Lesson & SKILL.md]
    Recall --> Exec[4. Runtime: 执行代码 / 工具调用]
    Exec --> TermCheck{5. 终端控制台物理校验}
    
    TermCheck -->|编译/测试失败| Retry[修改代码并重试]
    Retry --> Exec
    
    TermCheck -->|100% 成功且有修正记录| PostHook[6. Post-Task: Harness 萃取 Lessons Learned]
    PostHook --> WriteVK[7. 写入 OpenViking 1933 master_memory]
    WriteVK --> UpdateSkill[8. 热更新 SKILL.md 文件并提交 Git Tag]
    
    UpdateSkill --> NextAgent[9. Agent B 启动新任务 ➔ 秒级继承该避坑经验]
```

---

## 四、 多 Agent 跨节点交互时序图 (Interaction Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    participant AG as Antigravity (Win/WSL)
    participant VK as OpenViking (Port 1933)
    participant OC as OpenClaw (Linux)

    Note over AG,VK: 阶段一：Agent A 踩坑与经验提炼
    AG->>VK: 1. 执行任务遇到 API Null 误判 Bug
    AG->>AG: 2. 修复 Bug 并通过控制台测试
    AG->>VK: 3. Post-Task Hook: post /api/v1/sessions/store (存入新 Lesson)
    VK-->>AG: 4. 返回 200 OK，更新 master_memory

    Note over OC,VK: 阶段二：Agent B 自动继承与秒级避坑
    OC->>VK: 5. 启动新任务，自动发送 openviking_find(query="API 校验")
    VK-->>OC: 6. 召回 Agent A 刚写入的 0.99 匹配度 Lesson
    OC->>OC: 7. Agent B 自动跳过该 Bug，直接写出正确代码
```

---

## 五、 落地实现四大规范 (Implementation Guidelines)

1. **Pre-Task 战衣组装 (Cold-Start Recall)**:
   - 任何 Agent 接到任务后，首先隐式向 `http://127.0.0.1:1933/api/v1/search/find` 查询相关的历史 `Lessons`。
   - 将召回的 top-K 高相似度（Score ≥ 0.85）避坑规则注入 Prompt 头部。

2. **Runtime 实证校验 (Grounded Verification)**:
   - 拒绝大模型空想自我打分。
   - 只有终端命令行返回 `Exit Code 0`、`Build Success` 或 `Unit Tests 100% Passed` 的任务才被认定为有效经验。

3. **Post-Task 经验萃取 (Lesson Extraction Schema)**:
   - 提取格式必须为结构化 Markdown / JSON 摘要：
     ```json
     {
       "has_new_lesson": true,
       "target_skill": "diagnosing-bugs",
       "issue": "问题现象简述",
       "avoidance_rule": "避坑指南与正确规则",
       "code_snippet": "正确代码范例"
     }
     ```

4. **Evolution 写入与防死锁护栏 (Hot Refine Guardrails)**:
   - 写入动作直接在 API 响应结束前触发，绝不使用死循环轮询后台脚本。
   - 对 `SKILL.md` 的修改通过 Git 递增记录 (`git commit -m "chore(harness): evolve skill <name> with lesson"`).
