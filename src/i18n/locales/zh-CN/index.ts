import common from './common'
import tasks from './tasks'
import retrieval from './retrieval'
import resources from './resources'
import monitoring from './monitoring'
import settings from './settings'
import sessions from './sessions'
import home from './home'
import playground from './playground'

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
} as const

export default zhCN
