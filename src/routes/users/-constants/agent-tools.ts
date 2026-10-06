/**
 * agent-tools.ts
 * 智能体工具池常量与分类定义 (Tool ACL Matrix)。
 */

export type ToolCategory = {
  id: string
  name: string
  description: string
  tools: { id: string; name: string; description: string; defaultSelected?: boolean }[]
}

export const TOOL_CATEGORIES: ToolCategory[] = [
  {
    id: 'memory',
    name: '🧠 记忆中枢类',
    description: '核心体外大脑召回与语义检索工具',
    tools: [
      { id: 'find', name: 'find (语义召回)', description: '基于分层语义索引智能查找最相关记忆', defaultSelected: true },
      { id: 'search', name: 'search (精确检索)', description: '对记忆中枢进行关键词与过滤检索', defaultSelected: true },
      { id: 'read', name: 'read (读取记忆)', description: '读取特定记忆资源或文档的完整内容', defaultSelected: true },
    ],
  },
  {
    id: 'evolution',
    name: '⚡ 经验沉淀类',
    description: '自我演进、避坑事实与教训结晶沉淀',
    tools: [
      { id: 'record_evolution_lesson', name: 'record_evolution_lesson (经验沉淀)', description: '解决重大问题后将经验沉淀至体外大脑', defaultSelected: true },
    ],
  },
  {
    id: 'code',
    name: '🔍 代码探索类',
    description: '源码结构、符号树与静态检索',
    tools: [
      { id: 'grep', name: 'grep (模式匹配)', description: '快速在代码库中检索文本模式' },
      { id: 'glob', name: 'glob (文件寻址)', description: '按文件通配符扫描定位文件' },
      { id: 'tree', name: 'tree (目录树)', description: '获取代码库或工作区的层级结构' },
    ],
  },
  {
    id: 'filesystem',
    name: '📝 文件修改类',
    description: '工作区文件写入与精准编辑 (敏感操作)',
    tools: [
      { id: 'edit', name: 'edit (精准编辑)', description: '对指定文件执行唯一指纹锚点编辑' },
      { id: 'write', name: 'write (写入文件)', description: '新建或全量覆写文件内容' },
    ],
  },
]

export const ALL_TOOL_IDS = TOOL_CATEGORIES.flatMap((c) => c.tools.map((t) => t.id))
export const DEFAULT_TOOL_IDS = TOOL_CATEGORIES.flatMap((c) =>
  c.tools.filter((t) => t.defaultSelected).map((t) => t.id),
)
