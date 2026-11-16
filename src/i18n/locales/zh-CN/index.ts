import common from './common'
import tasks from './tasks'
import retrieval from './retrieval'
import resources from './resources'
import monitoring from './monitoring'
import settings from './settings'
import sessions from './sessions'
import home from './home'
import playground from './playground'
import studio from './studio'
import agentExperience from './agent-experience'
import watches from './watches'
import compile from './compile'
import arranger from './arranger'
import adminConsole from './admin'
import memoryTemplates from './memory-templates'
import vikingbot from './vikingbot'

const zhCN = {
  ...common,
  ...tasks,
  ...retrieval,
  ...resources,
  ...monitoring,
  ...settings,
  ...sessions,
  ...home,
  ...playground,
  ...agentExperience,
  ...watches,
  ...compile,
  ...arranger,
  ...adminConsole,
  ...memoryTemplates,
  ...vikingbot,
  studio,
} as const

export default zhCN
