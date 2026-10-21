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
  studio,
} as const

export default zhCN
