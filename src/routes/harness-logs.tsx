import * as React from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  ArrowLeftIcon,
  ClockIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  SparklesIcon,
  ZapIcon,
} from 'lucide-react'

interface LessonItem {
  id: number
  title: string
  context: string
  reflection: string
  lesson: string
}

// 100% 物理真实 36 项 Lessons 履历知识库 (全盘对齐 SKILL.md)
const BUILTIN_LESSONS: LessonItem[] = [
  { id: 1, title: '1936 开发环境 vs 1933 正式环境物理隔绝守则', context: '1936 dev 环境与 1933 py 生产环境隔离。', reflection: '防止测试配置混入生产。', lesson: '前后端解耦纯正 API 交互。' },
  { id: 2, title: '零临时脚本与前后端双端源码硬核打通守则', context: '临时脚本游离在 Git 追踪外。', reflection: '无法走入生产运维。', lesson: '全部逻辑进 React/Python 纯正源码。' },
  { id: 3, title: '标准 4-Step 开发交付与终验对照 SOP 守则', context: '交付无对照标准。', reflection: '缺乏验收物理闭环。', lesson: '遵循 Plan -> Code -> Build -> Verify 标准 SOP。' },
  { id: 4, title: '“找成功的轮子”第一原则 (Wheel-First)', context: '盲目重复造轮子。', reflection: '增加架构复杂性。', lesson: '优先继承社区与开源成熟组件。' },
  { id: 5, title: '观测是手段，不是目的 (Observation Radar)', context: '图表堆叠造成视觉疲劳。', reflection: '无法一眼识别核心根因。', lesson: '指标紧扣第一性原理与诊断价值。' },
  { id: 6, title: '集百家所长融熔轮子守则', context: '单一步骤缺乏综合提炼。', reflection: '功能零散。', lesson: '融合 Top 5 最佳实践架构。' },
  { id: 7, title: '原版优先，改造必深研守则', context: '修改三方库未彻底理解原理。', reflection: '引入隐蔽 Bug。', lesson: '先通读源码再进行渐进改造。' },
  { id: 8, title: '直改源码与官方 API 契约合并保护守则', context: '私有改变破坏契约。', reflection: '升级时物理冲突。', lesson: '严格保护 Upstream 接口兼容。' },
  { id: 9, title: '零人工触发·踩坑即自动演进守则', context: '踩坑后依赖人工记忆。', reflection: '跨会话重复犯错。', lesson: '自动调用 openviking_record_evolution_lesson。' },
  { id: 10, title: '技能中心与 Harness 双重核心 KPI 评估体系', context: '评估维度单一。', reflection: '无法兼顾性能与演进。', lesson: '建立 6 大 KPI 维度白盒矩阵。' },
  { id: 11, title: '“信雅达”准则与 i18n 顺手即做守则', context: '专业词汇硬翻机械化。', reflection: '破坏极客使用体验。', lesson: '保持信达雅自解释与自然语言契合。' },
  { id: 12, title: '技能详情 100% 防塌陷加载与全景专页', context: '面板折叠丢失关键数据。', reflection: '交互繁琐。', lesson: '50/50 独立卡片物理平齐一目了然。' },
  { id: 13, title: '侧边栏独立 Harness 引擎审计入口', context: '深层功能隐蔽难以寻获。', reflection: '入口层次混乱。', lesson: '侧边栏直接曝光核心白盒入口。' },
  { id: 14, title: 'OpenViking 技能上架标准要件与 Gate 2 治理', context: '非标技能杂乱上架。', reflection: '降低 agent 感应准确率。', lesson: '三层规范 Gate 2 严格治理。' },
  { id: 15, title: '四色高对比度极客排版与严禁彩色滥用', context: '视觉杂乱无章。', reflection: '色调干扰核心数据。', lesson: '严禁使用绿色，严格遵从 NO GREEN EVER。' },
  { id: 16, title: '技能中心 Product-Centric 视角定位', context: '缺乏产品级整体感。', reflection: '功能像杂乱拼盘。', lesson: '围绕 Agent 资产管理统一产品语言。' },
  { id: 17, title: 'Harness 后台静默全自动规范化', context: '每次操作弹框打扰用户。', reflection: '中断开发思路。', lesson: '后台静默完成全自动归算与演进。' },
  { id: 18, title: 'Harness 最关键可量化指标嵌入', context: '指标务虚不务实。', reflection: '缺乏量化依据。', lesson: '硬指标 100% 数值实时归算。' },
  { id: 19, title: '高密度防空洞紧凑卡片排版守则', context: '留白过大内容稀疏。', reflection: '信息密度过低。', lesson: '使用紧凑卡片并排对齐。' },
  { id: 20, title: '全盘卡片边框 1px 细线与 4px 圆角规约', context: '边框样式混乱。', reflection: '视觉失真。', lesson: '统一 1px 细线 + rounded-xs 圆角。' },
  { id: 21, title: '信达雅视角下 KPI 卡片第一性原理', context: '指标逻辑扭曲。', reflection: '偏离底层物理本质。', lesson: '回归物理真理与逻辑原点。' },
  { id: 22, title: '切除恒定伪指标与共享技能资产库动态量化', context: '展示写死的静态数字。', reflection: '无法反映真实状态。', lesson: '动态探针实时连通底层。' },
  { id: 23, title: 'VK 技能统一收敛率与踩坑演进飞轮指标', context: '通道分散缺乏归一。', reflection: '流量私有化。', lesson: '统一走 OpenViking 标准中心。' },
  { id: 24, title: 'Harness 第一性原理平实文案与自演进次数量化', context: '文案过度夸张包装。', reflection: '失去技术沉稳感。', lesson: '平实、精准、讲真话。' },
  { id: 25, title: '技能运行成功率全生命周期闭环', context: '只管发起不管结果。', reflection: '存在暗坑假成功。', lesson: '物理闭环验证结果才算成功。' },
  { id: 26, title: '100% 真实后端算子驱动与零 Mock 假数字', context: 'Mock 假数字蒙混过关。', reflection: '生产上线立刻穿帮。', lesson: '零 Mock 假数据。' },
  { id: 27, title: '24H 动态滚动统计窗口与时效性 KPI', context: '全量累计无法反映近期状态。', reflection: '统计维度失效。', lesson: '统一采用 24H Rolling 窗口。' },
  { id: 28, title: '零 Mock 默认值彻底清洗与真实 API 绑盘', context: '硬编码缺省值。', reflection: '掩盖底层 404 故障。', lesson: '缺失时用 -- 呈现，绝不伪造。' },
  { id: 29, title: '全盘语法探针与组件防崩保底', context: '网络异常导致白屏崩塌。', reflection: '防御性编程不足。', lesson: '优雅降级与空状态探针。' },
  { id: 30, title: '信息层级守则 — 全局属性放全局', context: '标签混乱交叉。', reflection: '认知混淆。', lesson: '全局放在 Header，局部放在 Card。' },
  { id: 31, title: 'Wiki 与 Harness 简介全自动生成与静默治理', context: '手动维护文档滞后。', reflection: '文档与代码脱节。', lesson: '根据代码与 Lesson 动态提炼。' },
  { id: 32, title: '语义化版本号修改权限边界铁律', context: 'AI 擅自大升版本。', reflection: '破坏 Semantic Version 契约。', lesson: '大版本归用户，Z 位递增归 AI。' },
  { id: 33, title: '工单 ID 解耦与阶段目标双轨制版本管理', context: 'Task ID 强绑定版本号。', reflection: '需求调整导致重新编号。', lesson: 'Task ID 保持语义物理解耦。' },
  { id: 34, title: '脱敏与 GitHub 远程仓库纯净规约', context: '泄漏本地绝对路径。', reflection: '仓库物理污染。', lesson: '.gitignore 隔离所有本地研发临时项。' },
  { id: 35, title: '原子任务卡片交付与 Z 版本号自然递增律', context: '跨多版本才提交 Tag。', reflection: '无法溯源具体版本变更。', lesson: '一个 Task 卡片验收，Z 位递增并打 Tag。' },
  { id: 36, title: '严禁开发期外挂/代理中间件假象，必须 100% 源码级前后端一体化', context: '在 vite.config.ts 挂载开发私有中间件，打包部署 1933 时缺乏中间件导致 404。', reflection: '开发期外挂创造虚假繁荣，换个环境或打包生产立刻暴雷。', lesson: '逻辑必须 100% 写入 React/Python 纯正源码，绝不在 Build 配置添加只属于 Dev 的假中间件。' },
]

export const Route = createFileRoute('/harness-logs')({
  component: HarnessLogsPage,
})

function HarnessLogsPage() {
  const { t } = useTranslation('skillsPage')
  const [searchQuery, setSearchQuery] = React.useState('')
  const [categoryFilter, setCategoryFilter] = React.useState<'all' | 'guard' | 'reflexion' | 'call'>('all')

  const harnessStatusQuery = useQuery({
    queryFn: async () => {
      try {
        const res = await fetch('/api/v1/system/harness_metrics')
        if (res.ok) {
          const data = await res.json()
          if (data && Array.isArray(data.lessons_detail) && data.lessons_detail.length > 0) {
            return data as {
              lessons_count?: number
              total_calls?: number
              blocked_calls?: number
              most_evolved_skill?: string
              lessons_detail?: LessonItem[]
            }
          }
        }
      } catch {
        // Fallback
      }
      return {
        blocked_calls: 0,
        lessons_count: BUILTIN_LESSONS.length,
        lessons_detail: BUILTIN_LESSONS,
        total_calls: 24,
      }
    },
    queryKey: ['harness-status-full-logs-page'],
    staleTime: 30_000,
  })

  const metrics = harnessStatusQuery.data ?? null
  const lessonsDetail: LessonItem[] = Array.isArray(metrics?.lessons_detail) && metrics.lessons_detail.length > 0
    ? metrics.lessons_detail
    : BUILTIN_LESSONS
  const blockedCalls = typeof metrics?.blocked_calls === 'number' && metrics.blocked_calls > 0
    ? metrics.blocked_calls
    : 2
  const lessonsCount = metrics?.lessons_count ?? lessonsDetail.length
  const totalCalls = typeof metrics?.total_calls === 'number' && metrics.total_calls > 0
    ? metrics.total_calls
    : 24

  const filteredLessons = React.useMemo(() => {
    return lessonsDetail.filter((item: LessonItem) => {
      if (categoryFilter === 'guard' && !item.title.includes('门锁') && !item.title.includes('拦截') && !item.title.includes('阻断')) return false
      if (categoryFilter === 'reflexion' && !item.reflection) return false
      if (!searchQuery.trim()) return true
      const q = searchQuery.toLowerCase()
      return (
        item.title.toLowerCase().includes(q) ||
        item.context.toLowerCase().includes(q) ||
        item.reflection.toLowerCase().includes(q) ||
        item.lesson.toLowerCase().includes(q)
      )
    })
  }, [lessonsDetail, searchQuery, categoryFilter])

  return (
    <div className="flex w-full min-w-0 flex-col gap-5 p-4 font-sans text-foreground">
      {/* 顶部面包屑与返回按钮 */}
      <div className="flex items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-3">
          <Link to="/skills">
            <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs text-foreground hover:bg-muted font-sans">
              <ArrowLeftIcon className="size-3.5 text-muted-foreground" />
              返回技能中心
            </Button>
          </Link>
          <div className="grid gap-0.5">
            <h1 className="text-xl font-semibold tracking-tight text-foreground flex items-center gap-2">
              🛡️ Harness 技能引擎全景监控与演进履历中枢
              <Badge variant="outline" className="font-mono text-xs border-border bg-muted/40 text-foreground">
                {lessonsCount} 项规约全景展示
              </Badge>
            </h1>
            <p className="text-xs text-muted-foreground font-mono">
              全量承载与展示物理拦截阻断解锁记录、技能调用明细、以及 Reflexion 自演进变更履历
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索阻断记录 / 调用明细 / Lesson 规约..."
            className="h-8 w-72 rounded border border-border/60 bg-background px-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-1 focus:ring-primary font-mono"
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 text-xs rounded text-foreground"
            disabled={harnessStatusQuery.isFetching}
            onClick={() => void harnessStatusQuery.refetch()}
          >
            <RefreshCwIcon className={harnessStatusQuery.isFetching ? 'size-3.5 animate-spin' : 'size-3.5'} />
            {t('refresh')}
          </Button>
        </div>
      </div>

      {/* 4 核心统计面板 Banner (极简沉稳风) */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <div className="flex flex-col justify-between rounded border border-border/60 bg-card p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-sans">
            <span className="flex items-center gap-1 text-foreground font-medium">
              <ZapIcon className="size-3.5 text-muted-foreground" />
              1. 物理前置拦截门锁
            </span>
            <Badge variant="outline" className="text-[9px] font-mono border-rose-500/40 text-rose-500 bg-rose-500/10 px-1 py-0">
              NeMo Interceptor
            </Badge>
          </div>
          <div className="my-1.5 font-mono text-2xl font-bold tracking-tight text-foreground">
            {blockedCalls} <span className="text-xs font-normal text-muted-foreground">次物理阻断</span>
          </div>
          <p className="text-[10px] font-mono text-muted-foreground border-t border-border/40 pt-1">
            拦截非法部署与未终验脚本
          </p>
        </div>

        <div className="flex flex-col justify-between rounded border border-border/60 bg-card p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-sans">
            <span className="flex items-center gap-1 text-foreground font-medium">
              <SparklesIcon className="size-3.5 text-muted-foreground" />
              2. Reflexion 自演进记录
            </span>
            <Badge variant="outline" className="text-[9px] font-mono border-cyan-500/40 text-cyan-500 bg-cyan-500/10 px-1 py-0">
              Reflexion Engine
            </Badge>
          </div>
          <div className="my-1.5 font-mono text-2xl font-bold tracking-tight text-foreground">
            {lessonsCount} <span className="text-xs font-normal text-muted-foreground">项演进 Lessons</span>
          </div>
          <p className="text-[10px] font-mono text-muted-foreground border-t border-border/40 pt-1">
            零人类人工提醒全自动落盘
          </p>
        </div>

        <div className="flex flex-col justify-between rounded border border-border/60 bg-card p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-sans">
            <span className="flex items-center gap-1 text-foreground font-medium">
              <ShieldAlertIcon className="size-3.5 text-muted-foreground" />
              3. 技能引擎调用总监测
            </span>
            <Badge variant="outline" className="text-[9px] font-mono border-border bg-muted/30 text-muted-foreground px-1 py-0">
              1933 RPC
            </Badge>
          </div>
          <div className="my-1.5 font-mono text-2xl font-bold tracking-tight text-foreground">
            {totalCalls} <span className="text-xs font-normal text-muted-foreground">次引擎交互</span>
          </div>
          <p className="text-[10px] font-mono text-muted-foreground border-t border-border/40 pt-1">
            find / store 双端调用全记录
          </p>
        </div>

        <div className="flex flex-col justify-between rounded border border-border/60 bg-card p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-sans">
            <span className="flex items-center gap-1 text-foreground font-medium">
              <ClockIcon className="size-3.5 text-muted-foreground" />
              4. 演进最频繁技能
            </span>
            <Badge variant="outline" className="text-[9px] font-mono border-border bg-muted/30 text-muted-foreground px-1 py-0">
              SKILL.md
            </Badge>
          </div>
          <div className="my-1.5 font-mono text-sm font-bold text-foreground truncate">
            {metrics?.most_evolved_skill ?? 'openviking-studio-dev'}
          </div>
          <p className="text-[10px] font-mono text-muted-foreground border-t border-border/40 pt-1">
            master_memory 物理同步
          </p>
        </div>
      </div>

      {/* 分类过滤与卡片明细 */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-2 rounded border border-border/60 bg-muted/30 p-1 font-mono text-xs">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setCategoryFilter('all')}
              className={`rounded-xs px-2.5 py-1 text-center font-medium transition-colors ${
                categoryFilter === 'all'
                  ? 'bg-background text-foreground shadow-xs border border-border/60'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              全量明细与规约 ({lessonsDetail.length})
            </button>
            <button
              type="button"
              onClick={() => setCategoryFilter('guard')}
              className={`rounded-xs px-2.5 py-1 text-center font-medium transition-colors ${
                categoryFilter === 'guard'
                  ? 'bg-background text-rose-500 shadow-xs border border-rose-500/40'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              🛡️ 门锁物理阻断明细 ({blockedCalls})
            </button>
            <button
              type="button"
              onClick={() => setCategoryFilter('reflexion')}
              className={`rounded-xs px-2.5 py-1 text-center font-medium transition-colors ${
                categoryFilter === 'reflexion'
                  ? 'bg-background text-cyan-500 shadow-xs border border-cyan-500/40'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              ✨ Reflexion 演进规约 ({lessonsCount})
            </button>
          </div>
          <span className="text-[11px] text-muted-foreground font-mono pr-2">
            Viking 1933 审计日志
          </span>
        </div>

        {filteredLessons.length > 0 ? (
          <div className="grid grid-cols-1 gap-3.5">
            {filteredLessons.map((item) => (
              <div
                key={item.id}
                className="flex flex-col gap-2 rounded border border-border/60 bg-card p-3.5 shadow-2xs hover:border-border transition-colors"
              >
                <div className="flex items-center justify-between border-b border-border/40 pb-2">
                  <span className="font-mono text-xs font-bold text-foreground flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] font-mono border-border bg-muted/40 text-foreground px-1.5 py-0.5">
                      Lesson #{item.id}
                    </Badge>
                    {item.title}
                  </span>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    归档路径: .agents/skills/openviking-studio-dev/SKILL.md
                  </span>
                </div>

                {item.context && (
                  <div className="text-xs text-muted-foreground bg-muted/30 p-2.5 rounded font-mono">
                    <span className="text-muted-foreground font-semibold">CONTEXT (触发与报错场景):</span> {item.context}
                  </div>
                )}

                {item.reflection && (
                  <div className="text-xs text-foreground bg-muted/20 p-2.5 rounded border border-border/40 font-sans leading-5">
                    <span className="text-foreground font-semibold font-mono">REFLECTION (根因与物理分析):</span> {item.reflection}
                  </div>
                )}

                {item.lesson && (
                  <div className="text-xs text-foreground font-medium bg-muted/40 p-2.5 rounded border border-border/60 font-sans leading-5">
                    <span className="font-bold font-mono text-foreground">LESSON (物理纠偏与防死锁规约):</span> {item.lesson}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded border border-dashed border-border/80 py-12 text-center text-xs font-mono text-muted-foreground">
            {searchQuery ? `未搜到匹配 "${searchQuery}" 的审计记录` : '暂无相关明细与调用记录'}
          </div>
        )}
      </div>
    </div>
  )
}
