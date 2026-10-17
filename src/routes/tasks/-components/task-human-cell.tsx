import { useTranslation } from 'react-i18next'
import type { TaskRecord } from '#/routes/tasks/-lib/task-record'

interface TaskHumanCellProps {
  task: TaskRecord
  index: number
  pageOffset: number
}

/**
 * 纯净任务名称解析（严禁 Emoji 🚫、严禁冗余类型前缀 🚫）
 */
export function cleanTaskTitle(
  rawTitle?: string,
  fallbackResourceName?: string | null,
  fallbackTypeName?: string,
): string {
  let title = (rawTitle || '').trim()
  // 1. 彻底切除开头的 Emoji (如 📥, 📦, 🚀 等)，避免 combined character class 警告
  title = title.replace(/^[\p{Extended_Pictographic}\s]+/u, '').trim()
  // 2. 彻底切除冗余的任务类型或动作冒号前缀 (如 "原子入库：", "资源处理:", "会话归档：", "技能注册:", 等)
  title = title.replace(/^[^：:\n]{2,16}[：:]\s*/, '').trim()

  if (title) {
    return title
  }
  if (fallbackResourceName) {
    return fallbackResourceName
  }
  return fallbackTypeName || '-'
}

export function TaskHumanCell({
  task,
  index,
  pageOffset,
}: TaskHumanCellProps) {
  const { t } = useTranslation('tasksPage')
  const meta = task.meta ?? {}
  const shortId = task.task_id
    ? task.task_id.length > 12
      ? task.task_id.slice(-8)
      : task.task_id
    : String(pageOffset + index + 1)

  const rawType = task.task_type || ''
  const sourceName = meta.source_name || (meta.source_path ? String(meta.source_path).split(/[\\/]/).pop() : null)
  const resourceName = sourceName || (task.resource_id ? task.resource_id.split('/').pop()?.replace('.md', '') : null)
  const typeName = t(`types.${rawType}`, { defaultValue: rawType || `工序 #${shortId}` })

  const displayTitle = cleanTaskTitle(meta.human_title, resourceName, typeName)

  return (
    <div className="flex items-center min-w-0 max-w-sm py-0.5">
      <span
        className="truncate text-xs font-medium text-foreground hover:text-primary transition-colors select-none"
        title={displayTitle}
      >
        {displayTitle}
      </span>
    </div>
  )
}

