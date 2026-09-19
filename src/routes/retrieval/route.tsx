import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  CompassIcon,
  DatabaseIcon,
  FlaskConicalIcon,
  LayersIcon,
  SearchIcon,
  SparklesIcon,
  TerminalIcon,
  ZapIcon,
  ShieldCheckIcon,
} from 'lucide-react'

import { RetrievalBenchmarkDrawer } from './-components/benchmark-drawer'
import { GatekeeperMetricsCard } from './-components/gatekeeper-metrics-card'
import { GatekeeperAuditStream } from './-components/gatekeeper-audit-stream'
import { RetrievalControls } from './-components/retrieval-controls'
import { RetrievalMetricsCards } from './-components/retrieval-metrics-cards'
import { BM25HybridCockpit } from './-components/bm25-hybrid-cockpit'
import { ZGSearchCockpit } from './-components/zg-search-cockpit'
import { RAGAbstentionCockpit } from './-components/rag-abstention-cockpit'
import { HGRAGCompassCockpit } from './-components/hg-rag-compass-cockpit'
import { EntropyCrystallizerCockpit } from './-components/entropy-crystallizer-cockpit'
import { ActiveNotesHistoryCockpit } from './-components/active-notes-history-cockpit'
import { ValetIngestionCockpit } from './-components/valet-ingestion-cockpit'
import { SkillEvalCockpit } from './-components/skill-eval-cockpit'
import { AHECockpit } from './-components/ahe-cockpit'
import { HermesEvolveCockpit } from './-components/hermes-evolve-cockpit'
import { RetrievalResults } from './-components/retrieval-results'
import { RetrievalSearchBar } from './-components/search-bar'
import {
  DEFAULT_CUSTOM_PATH_INPUT,
  DEFAULT_RESULT_COUNT,
  DEFAULT_RETRIEVAL_MODE,
  DEFAULT_RETRIEVAL_SCOPE,
} from './-constants/retrieval'
import { useResourceContextProbe } from './-hooks/use-resource-context-probe'
import { useRetrievalQuery } from './-hooks/use-retrieval-query'
import { flattenResults } from './-lib/results'
import { resolveScopeTargetUri } from './-lib/scope'
import { validateRetrievalSearch } from './-lib/search-state'
import type { RetrievalMode, RetrievalScope } from './-types/retrieval'

export type RetrievalTab = 'search' | 'bm25' | 'zg' | 'compass' | 'crystallizer' | 'context' | 'valet' | 'skillEval' | 'ahe' | 'hermes'

export const Route = createFileRoute('/retrieval')({
  validateSearch: validateRetrievalSearch,
  component: RetrievalPage,
})

function RetrievalPage() {
  const { t } = useTranslation('retrieval')
  const navigate = useNavigate({ from: Route.fullPath })
  const search = Route.useSearch()

  const [activeTab, setActiveTab] = useState<RetrievalTab>('search')

  const initialMode = search.mode ?? DEFAULT_RETRIEVAL_MODE
  const initialResultCount = search.count ?? DEFAULT_RESULT_COUNT
  const initialScope = search.scope ?? DEFAULT_RETRIEVAL_SCOPE
  const initialCustomPath = search.path ?? DEFAULT_CUSTOM_PATH_INPUT
  const initialSessionId = search.session ?? ''
  const initialIgnoreCase = search.ignoreCase ?? false

  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(initialMode)
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [resultCount, setResultCount] = useState<number>(initialResultCount)
  const [retrievalScope, setRetrievalScope] =
    useState<RetrievalScope>(initialScope)
  const [customPathInput, setCustomPathInput] = useState(initialCustomPath)
  const [sessionIdInput, setSessionIdInput] = useState(initialSessionId)
  const [ignoreCase, setIgnoreCase] = useState(initialIgnoreCase)
  const [activeOnly, setActiveOnly] = useState<boolean>(true)
  const inputRef = useRef<HTMLInputElement>(null)

  const targetUri = useMemo(() => {
    return resolveScopeTargetUri(retrievalScope, customPathInput)
  }, [customPathInput, retrievalScope])

  const hasSubmitted = submittedQuery.trim().length > 0
  const sessionId = sessionIdInput.trim() || undefined
  const retrievalQuery = useRetrievalQuery({
    enabled: hasSubmitted,
    ignoreCase,
    mode: retrievalMode,
    query: submittedQuery,
    resultCount,
    sessionId,
    targetUri,
  })
  const resourceProbeQuery = useResourceContextProbe()

  const data = hasSubmitted ? retrievalQuery.data : undefined
  const hasResults = Boolean(data && data.total > 0)
  const hasRetrievableContext = resourceProbeQuery.data?.hasContext ?? false
  const flatItems = useMemo(() => (data ? flattenResults(data) : []), [data])
  const displayFlatItems = useMemo(() => {
    if (!activeOnly) return flatItems
    return flatItems.filter((fi) => {
      const uri = fi.item.uri.toLowerCase()
      const isStagingOrArchived =
        uri.includes('/staging/') ||
        uri.includes('/archive/') ||
        uri.includes('_sessions')
      return !isStagingOrArchived
    })
  }, [flatItems, activeOnly])
  const queryPlanItems = data?.query_plan?.queries ?? []

  const handleSubmit = useCallback(() => {
    const trimmed = query.trim()
    if (trimmed.length === 0) {
      return
    }

    setSubmittedQuery(trimmed)
  }, [query])

  const handleUploadClick = useCallback(() => {
    void navigate({ to: '/playground', search: { upload: true } })
  }, [navigate])

  useEffect(() => {
    inputRef.current?.focus()
    // Clear legacy sessionStorage search so it never haunts the user on page reopen
    try {
      if (typeof window !== 'undefined') {
        window.sessionStorage.removeItem('last_retrieval_search')
      }
    } catch {
      // Ignore in sandbox environments
    }
  }, [])

  // If page was loaded with a ?q= in URL, clean the URL immediately to avoid re-triggering on F5
  useEffect(() => {
    if (search.q) {
      void navigate({ replace: true, search: {} })
    }
  }, [navigate, search.q])

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      {/* 高密座舱顶层 Tab 导航 (消除 4 屏瀑布式纵向滚动) */}
      <div className="flex items-center gap-1.5 border-b border-border/60 pb-1">
        {[
          { id: 'search', label: '主控检索与综合结果', icon: <SearchIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
          { id: 'bm25', label: 'BM25 双流混合融合', icon: <LayersIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
          { id: 'zg', label: 'zg 端侧代码语义', icon: <TerminalIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
          { id: 'compass', label: 'HG-RAG 拓扑与主动弃答', icon: <CompassIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
          { id: 'crystallizer', label: '三门结晶与不可变事实', icon: <SparklesIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
          { id: 'context', label: '主动上下文与历史分仓', icon: <DatabaseIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
          { id: 'valet', label: '前门泊车与反熵准入', icon: <ZapIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
          { id: 'skillEval', label: '🧪 技能视网膜', icon: <FlaskConicalIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
          { id: 'ahe', label: '🛡️ AHE 自演进', icon: <ShieldCheckIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
          { id: 'hermes', label: '🧬 Hermes 经历与微补丁', icon: <DatabaseIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id as RetrievalTab)}
            className={`flex items-center rounded-t-md px-3 py-1.5 text-xs font-medium transition-all cursor-pointer ${
              activeTab === tab.id
                ? 'border-b-2 border-cyan-600 dark:border-cyan-400 bg-card text-foreground font-semibold'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: 主控检索与综合结果 */}
      {activeTab === 'search' && (
        <div className="flex flex-col gap-4">
          {/* 熵增防御：写入准入与四态变异宏观 KPI */}
          <GatekeeperMetricsCard />

          {/* 4 大核心检索运行与质量基准 KPI 指标卡片 */}
          <RetrievalMetricsCards />

          <div className="flex items-center gap-2">
            <div className="flex-1 min-w-0">
              <RetrievalSearchBar
                inputRef={inputRef}
                onChange={setQuery}
                onSubmit={handleSubmit}
                placeholder={t(`placeholders.${retrievalMode}`)}
                query={query}
                sendLabel={t('send')}
              />
            </div>
            <RetrievalBenchmarkDrawer />
          </div>

          <RetrievalControls
            activeOnly={activeOnly}
            customPathInput={customPathInput}
            ignoreCase={ignoreCase}
            mode={retrievalMode}
            onActiveOnlyChange={setActiveOnly}
            onCustomPathInputChange={setCustomPathInput}
            onIgnoreCaseChange={setIgnoreCase}
            onModeChange={setRetrievalMode}
            onResultCountChange={setResultCount}
            onScopeChange={setRetrievalScope}
            onSessionIdInputChange={setSessionIdInput}
            resultCount={resultCount}
            scope={retrievalScope}
            sessionIdInput={sessionIdInput}
            t={t}
            targetUri={targetUri}
          />

          <RetrievalResults
            flatItems={displayFlatItems}
            hasRetrievableContext={hasRetrievableContext}
            hasResults={hasResults}
            hasSubmitted={hasSubmitted}
            isCheckingContext={resourceProbeQuery.isLoading}
            isError={retrievalQuery.isError}
            isLoading={retrievalQuery.isLoading}
            onUploadClick={handleUploadClick}
            queryPlanItems={queryPlanItems}
            resultCount={resultCount}
            t={t}
          />
        </div>
      )}

      {/* Tab 2: BM25 双流混合融合 */}
      {activeTab === 'bm25' && <BM25HybridCockpit />}

      {/* Tab 3: zg 端侧代码语义 */}
      {activeTab === 'zg' && <ZGSearchCockpit />}

      {/* Tab 4: HG-RAG 分层指南针拓扑与读写分离知识工程座舱 */}
      {activeTab === 'compass' && (
        <div className="flex flex-col gap-4">
          <HGRAGCompassCockpit />
          <RAGAbstentionCockpit />
          <GatekeeperAuditStream />
        </div>
      )}

      {/* Tab 5: 三门结晶减熵与不可变事实座舱 */}
      {activeTab === 'crystallizer' && <EntropyCrystallizerCockpit />}

      {/* Tab 6: 主动上下文与历史分仓座舱 */}
      {activeTab === 'context' && <ActiveNotesHistoryCockpit />}

      {/* Tab 7: 前门泊车与反熵准入座舱 */}
      {activeTab === 'valet' && <ValetIngestionCockpit />}
      {activeTab === 'skillEval' && <SkillEvalCockpit />}
      {activeTab === 'ahe' && <AHECockpit />}
      {activeTab === 'hermes' && <HermesEvolveCockpit />}
    </div>
  )
}
