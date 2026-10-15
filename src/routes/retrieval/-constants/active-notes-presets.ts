// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export interface ActiveNotesPreset {
  id: string
  name: string
  description: string
  session_id: string
  active_goal: string
  working_constraints: string[]
  current_state: string
  discovered_facts: string[]
  history: Array<{
    role: 'user' | 'assistant' | 'tool' | 'system'
    content: string
  }>
}

export const ACTIVE_NOTES_PRESETS: ActiveNotesPreset[] = [
  {
    id: 'preset-refactor-session',
    name: '架构长程会话: 检索与上下文治理',
    description: '模拟长程多轮对话，对比全局 Compaction 摘要失真与 Active Notes 双轨分仓',
    session_id: 'session_refactor_retrieval_01',
    active_goal: '重构 Retrieval 混合检索与双轨分仓上下文治理，彻底切除有损 Compaction',
    working_constraints: [
      'NO GREEN EVER 🚫: 界面严禁出现绿色，仅偏离基线上色',
      '座舱级最高信息密度律: 最小字号硬下限 >= 12px (text-xs)',
      '单文件 100~300 行黄金甜点区 (绝对 <= 500 行)',
      '对外唯一服务端口物理收口为 1933',
    ],
    current_state: 'Step 3/4: 前端高密座舱与试验台挂载',
    discovered_facts: [
      'SQLite FTS5 + WAL 模式具备原子无锁毫秒级检索',
      'ActiveNotes 常驻主上下文仅需 ~180 Tokens，节约率达 96.5%',
      'History 独立分仓保留原始文本，排查错误码和路径 100% 保真',
    ],
    history: [
      { role: 'user', content: '请先阅读 .agents/AGENTS.md 与 REFACTORING_PLAN.md。' },
      { role: 'assistant', content: '收到，已完成架构研读，确认本次主攻 Card-Context-ActiveNotesAndHistory。' },
      { role: 'user', content: '请说明为什么必须切除全局有损 Compaction？' },
      { role: 'assistant', content: '因为重复摘要会抹平报错码、路径与未完成的中间状态，造成严重失忆与幻觉。' },
      { role: 'user', content: '开始按 TDD 编写红绿循环测试用例。' },
    ],
  },
  {
    id: 'preset-port-diagnostics',
    name: '端口排障与不可变事实确立',
    description: '回溯端口治理历史流，搜索 ERR_PORT_CONFLICT 与 1936 关键字',
    session_id: 'session_port_diagnostics_02',
    active_goal: '彻底肃清历史遗留 1936 端口，确立唯一对外服务端口 1933 单一真相源',
    working_constraints: [
      '严禁双端口混部，杜绝端口冲突',
      '单例进程运行，禁止残留僵尸端口',
    ],
    current_state: '端口治理已验收封板',
    discovered_facts: [
      '1936 端口已在 systemd 中彻底解绑',
      '唯一 REST/MCP 统一由端口 1933 承载',
    ],
    history: [
      { role: 'user', content: '检查当前后台是否有端口冲突报错？' },
      { role: 'assistant', content: '排查发现日志: ERR_PORT_CONFLICT_1936，系旧测试脚本残留。' },
      { role: 'user', content: '立即物理终止并解绑旧服务。' },
      { role: 'assistant', content: '已执行 kill 与配置解绑，端口 1933 恢复健康唯一监听。' },
    ],
  },
  {
    id: 'preset-error-traceback',
    name: '报错回溯与精确路径检索',
    description: '通过 search_history 精确找回深层文件路径与特定错误码',
    session_id: 'session_error_traceback_03',
    active_goal: '排查并治愈 Pydantic V2 class-based config 废弃告警',
    working_constraints: [
      '保持向下兼容性',
      '单测必须 100% 通过',
    ],
    current_state: '完成 model_config = ConfigDict(...) 替换',
    discovered_facts: [
      'WatchTask 中使用的 class Config 已在 Pydantic V2 废弃',
      '使用 ConfigDict 即可消除全部控制台警告',
    ],
    history: [
      { role: 'user', content: '运行 pytest 检查是否有 Pydantic 警告？' },
      { role: 'assistant', content: '发现警告: PydanticDeprecatedSince20 at openviking/resource/watch_manager.py:55' },
      { role: 'user', content: '请修复该警告。' },
      { role: 'assistant', content: '已将 class Config 替换为 model_config = ConfigDict(arbitrary_types_allowed=True)。' },
    ],
  },
]
