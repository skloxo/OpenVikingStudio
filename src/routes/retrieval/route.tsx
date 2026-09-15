import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { RetrievalBenchmarkDrawer } from './-components/benchmark-drawer'
import { GatekeeperMetricsCard } from './-components/gatekeeper-metrics-card'
import { GatekeeperAuditStream } from './-components/gatekeeper-audit-stream'
import { RetrievalControls } from './-components/retrieval-controls'
import { RetrievalMetricsCards } from './-components/retrieval-metrics-cards'
import { BM25HybridCockpit } from './-components/bm25-hybrid-cockpit'
import { ZGSearchCockpit } from './-components/zg-search-cockpit'
import { RAGAbstentionCockpit } from './-components/rag-abstention-cockpit'
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

export const Route = createFileRoute('/retrieval')({
  validateSearch: validateRetrievalSearch,
  component: RetrievalPage,
})

function RetrievalPage() {
  const { t } = useTranslation('retrieval')
  const navigate = useNavigate({ from: Route.fullPath })
  const search = Route.useSearch()

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
      {/* 熵增防御：写入准入与四态变异宏观 KPI */}
      <GatekeeperMetricsCard />

      {/* 记忆治理流水：实时写入判定轨迹与向量审查大盘 */}
      <GatekeeperAuditStream />

      {/* 4 大核心检索运行与质量基准 KPI 指标卡片 */}
      <RetrievalMetricsCards />

      {/* BM25 + 向量双流融合座舱与精确符号试验台 (Card-Retrieval-BM25Hybrid) */}
      <BM25HybridCockpit />

      {/* zg 端侧代码语义检索与分级懒加载座舱 (Card-Retrieval-LocalFirst-zgSemanticSearch) */}
      <ZGSearchCockpit />

      {/* RAG 约束验证与主动弃答门禁座舱 (Card-RAG-Abstention-ZeroHallucination-Pipeline) */}
      <RAGAbstentionCockpit />

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
  )
}
