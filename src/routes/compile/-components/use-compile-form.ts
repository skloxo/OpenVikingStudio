import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useBlocker, useNavigate } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useAppConnection } from '#/hooks/use-app-connection'
import { createRandomUuid } from '#/lib/browser-crypto'
import { isOvClientError } from '#/lib/ov-client'
import { fetchFileContent, fetchFsStat } from '#/routes/resources/-lib/api'
import {
  createCompile,
  fetchCompileConfig,
  fetchCompileTask,
  lookupSubmission,
  updateCompileConfig,
  type CompileConfig,
  type CompileRequest,
  type CompileTask,
  type UpdateSchedule,
} from '../-lib/api'
import { parseArgs } from '../-lib/commands'
import { isRejectedCompileSubmission } from '../-lib/errors'
import { clearCompileHandoff, readCompileHandoff } from '../-lib/handoff'
import { sourceUris, targetError } from '../-lib/locations'
import { useCompileSkills } from '../-lib/skills'
import { useCompileCapability } from './capability-notice'
import { defaultSchedule } from './schedule-fields'

export type CompileDraft = {
  skill: string
  sources: string
  to: string
  instruction: string
}

export const emptyCompileDraft: CompileDraft = {
  skill: '',
  sources: '',
  to: '',
  instruction: '',
}

function readDraft(key: string): CompileDraft {
  try {
    const data = JSON.parse(localStorage.getItem(key) || '{}')
    return Object.fromEntries(
      Object.keys(emptyCompileDraft).map((field) => [
        field,
        typeof data?.[field] === 'string' ? data[field] : '',
      ]),
    ) as CompileDraft
  } catch {
    return emptyCompileDraft
  }
}

export function useCompileFormState({
  fromTask,
  sourceUri,
  target,
}: {
  fromTask?: string
  sourceUri?: string
  target?: string
}) {
  const { t } = useTranslation('compile')
  const navigate = useNavigate()
  const { identityScopeKey, connection } = useAppConnection()
  const userResourceRoot = `viking://user/${connection.userId || 'default'}/resources/`
  const draftKey = `compile-draft:${identityScopeKey}`
  const submissionKey = `compile-submission:${identityScopeKey}`
  const [handoff] = useState(() => readCompileHandoff(identityScopeKey))
  const queryClient = useQueryClient()
  const [autoUpdate, setAutoUpdate] = useState(false)
  const [schedule, setSchedule] = useState<UpdateSchedule>(defaultSchedule)

  const config = useQuery({
    queryKey: ['compile-config', identityScopeKey, target],
    queryFn: ({ signal }) => fetchCompileConfig(target!, signal),
    enabled: !!target,
    staleTime: 0,
  })

  const [recoverKey, setRecoverKey] = useState(() => {
    if (target) return null
    try {
      return sessionStorage.getItem(submissionKey)
    } catch {
      return null
    }
  })

  const [savedDraft] = useState(() => readDraft(draftKey))
  const [draftStarted, setDraftStarted] = useState(
    () => !!(recoverKey || handoff || fromTask || sourceUri),
  )
  useEffect(() => {
    clearCompileHandoff()
  }, [])

  const [draft, setDraft] = useState<CompileDraft>(() =>
    target
      ? { ...emptyCompileDraft, to: target }
      : recoverKey
        ? savedDraft
        : handoff
          ? {
              skill: handoff.skill || '',
              sources: handoff.from?.join('\n') || '',
              to: handoff.to || '',
              instruction: handoff.instruction || '',
            }
          : fromTask
            ? savedDraft
            : {
                ...emptyCompileDraft,
                sources: sourceUri || userResourceRoot.replace(/\/$/, ''),
              },
  )

  const [args, setArgs] = useState(
    !target && !recoverKey && handoff?.args
      ? JSON.stringify(handoff.args, null, 2)
      : '',
  )
  const [preview, setPreview] = useState(false)
  const [locationRevision, setLocationRevision] = useState(0)
  const capability = useCompileCapability()
  const [error, setError] = useState<unknown>(null)
  const [savingError, setSavingError] = useState(false)
  const [busy, setBusy] = useState(false)
  const [uncertain, setUncertain] = useState(false)
  const [attempted, setAttempted] = useState(false)
  const submission = useRef<{ key: string; request: CompileRequest } | null>(null)
  const mounted = useRef(true)
  const completed = useRef(false)
  const filled = useRef(false)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  useBlocker({
    shouldBlockFn: () =>
      !completed.current &&
      (busy || !!args.trim() || savingError) &&
      !window.confirm(t('leave')),
    enableBeforeUnload: () => !completed.current && !!args.trim(),
  })

  useEffect(() => {
    if (completed.current || !draftStarted || target) return
    try {
      localStorage.setItem(draftKey, JSON.stringify(draft))
      setSavingError(false)
    } catch {
      setSavingError(true)
    }
  }, [draft, draftKey, draftStarted, target])

  useEffect(() => {
    if (!config.isSuccess || !config.isFetchedAfterMount || filled.current) return
    filled.current = true
    setDraft({
      skill: config.data.skill,
      sources: config.data.from.join('\n'),
      to: config.data.to,
      instruction: config.data.instruction || '',
    })
    setAutoUpdate(config.data.auto_update)
    setSchedule(config.data.update_schedule || defaultSchedule)
    setLocationRevision((v) => v + 1)
  }, [config.data, config.isSuccess, config.isFetchedAfterMount])

  const skills = useCompileSkills()
  const original = useQuery({
    queryKey: ['compile-task', identityScopeKey, fromTask],
    queryFn: ({ signal }) => fetchCompileTask(fromTask!, signal),
    enabled: !!fromTask,
  })

  useEffect(() => {
    const originalRequest = original.data?.meta?.request
    if (!originalRequest || filled.current || recoverKey) return
    filled.current = true
    if (
      Object.values(readDraft(draftKey)).some(Boolean) &&
      !window.confirm(t('selectDraft'))
    ) {
      return
    }
    setLocationRevision((v) => v + 1)
    setDraft({
      skill: originalRequest.skill,
      sources: originalRequest.from.join('\n'),
      to: originalRequest.to,
      instruction: originalRequest.instruction || '',
    })
    setArgs(
      originalRequest.args ? JSON.stringify(originalRequest.args, null, 2) : '',
    )
  }, [original.data, draftKey, recoverKey, t])

  const skillContent = useQuery({
    queryKey: ['compile-skill-content', identityScopeKey, draft.skill],
    queryFn: () => fetchFileContent(`${draft.skill.replace(/\/$/, '')}/SKILL.md`),
    enabled: preview && !!draft.skill,
  })

  function update(key: keyof CompileDraft, value: string) {
    setDraftStarted(true)
    setDraft((v) => ({ ...v, [key]: value }))
  }

  const sourceRows = draft.sources ? draft.sources.split('\n') : ['']
  const targetErrKey = targetError(draft.to.trim())
  const fieldErrors = {
    skill: !draft.skill ? t('skillRequired') : '',
    sources: !draft.sources.trim()
      ? t('sourcesRequired')
      : sourceRows.some((v) => v.trim() && !v.trim().startsWith('viking://'))
        ? t('invalidUri')
        : '',
    to: targetErrKey ? t(targetErrKey as never) : '',
    args: (() => {
      try {
        const parsed = parseArgs(args)
        if (parsed && ('auto_update' in parsed || 'update_schedule' in parsed)) {
          return t('schedule.reservedArgs')
        }
        return ''
      } catch {
        return t('argsError')
      }
    })(),
  }

  function validate() {
    setAttempted(true)
    const first = (
      Object.keys(fieldErrors) as (keyof typeof fieldErrors)[]
    ).find((key) => fieldErrors[key])
    if (!first) return true
    if (first === 'args') {
      document.getElementById('compile-advanced')?.setAttribute('open', '')
    }
    document
      .getElementById(`compile-${first === 'to' ? 'target' : first}`)
      ?.focus()
    return false
  }

  function buildRequest(): CompileRequest {
    const sources = sourceUris(draft.sources)
    if (!draft.skill || !sources.length || !draft.to.trim()) {
      throw new Error(t('required'))
    }
    if ([...sources, draft.skill, draft.to.trim()].some((u) => !u.startsWith('viking://'))) {
      throw new Error(t('invalidUri'))
    }
    let parsed: Record<string, unknown> | undefined
    try {
      parsed = parseArgs(args)
    } catch {
      throw new Error(t('argsError'))
    }
    return {
      from: sources,
      skill: draft.skill,
      to: draft.to.trim(),
      ...(draft.instruction.trim() ? { instruction: draft.instruction.trim() } : {}),
      ...(parsed || autoUpdate
        ? {
            args: {
              ...parsed,
              ...(autoUpdate ? { auto_update: true, update_schedule: schedule } : {}),
            },
          }
        : {}),
    }
  }

  async function finish(result: CompileTask | CompileConfig) {
    if (!mounted.current) return
    completed.current = true
    if (!target) {
      try {
        localStorage.removeItem(draftKey)
        sessionStorage.removeItem(submissionKey)
      } catch {
        /* optional */
      }
    }
    if ('task_id' in result) {
      await navigate({
        to: '/compile/tasks/$taskId',
        params: { taskId: result.task_id },
      })
    } else {
      await queryClient.invalidateQueries({
        queryKey: ['compile-configs', identityScopeKey],
      })
      await queryClient.invalidateQueries({
        queryKey: ['compile-config', identityScopeKey],
        refetchType: 'none',
      })
      toast.success(t('schedule.saved'))
      await navigate({ to: '/compile', search: { tab: 'schedules' } })
    }
  }

  async function submit() {
    if (
      busy ||
      (target && (!config.data || !config.isFetchedAfterMount || config.isError))
    ) {
      return
    }
    setError(null)
    const restoredKey = submission.current ? null : recoverKey
    setBusy(true)
    try {
      if (restoredKey) {
        try {
          await finish(await lookupSubmission(restoredKey))
          return
        } catch (cause) {
          if (!isOvClientError(cause) || cause.code !== 'NOT_FOUND') throw cause
        }
        if (!mounted.current) return
        const submittedAt = Number(restoredKey.split(':')[0])
        if (!Number.isFinite(submittedAt) || Date.now() - submittedAt > 86400000) {
          throw new Error(t('expiredSubmission'))
        }
      }
      if (!submission.current && !validate()) return
      if (target) {
        const body = buildRequest()
        await finish(
          await updateCompileConfig({
            to: target,
            from: body.from,
            skill: body.skill,
            instruction: draft.instruction.trim() || null,
            auto_update: autoUpdate,
            update_schedule: autoUpdate ? schedule : null,
          }),
        )
        return
      }
      const checked = await capability.refetch()
      if (!mounted.current || checked.isError || !checked.data?.can_create) return
      if (!submission.current && !restoredKey) {
        const entries = await Promise.all(
          sourceUris(draft.sources).map((uri) =>
            fetchFsStat(uri, { throwOnError: true }),
          ),
        )
        if (!mounted.current) return
        if (entries.some((entry) => !entry.isDir)) {
          throw new Error(t('sourceNotDirectory'))
        }
        try {
          const dest = await fetchFsStat(draft.to.trim(), { throwOnError: true })
          if (!dest.isDir) throw new Error(t('targetNotDirectory'))
        } catch (cause) {
          if ((cause as { code?: string }).code !== 'NOT_FOUND') throw cause
        }
        if (!mounted.current) return
      }
      if (autoUpdate && !submission.current && !restoredKey) {
        await finish(
          await createCompile(buildRequest(), `${Date.now()}:${createRandomUuid()}`),
        )
        return
      }
      const body = submission.current?.request || buildRequest()
      if (!submission.current) {
        submission.current = {
          key: recoverKey || `${Date.now()}:${createRandomUuid()}`,
          request: body,
        }
      }
      const key = submission.current.key
      try {
        sessionStorage.setItem(submissionKey, key)
      } catch {
        /* optional */
      }
      setRecoverKey(key)
      await finish(await createCompile(body, key))
    } catch (cause) {
      if (mounted.current) {
        const definite = isRejectedCompileSubmission(cause)
        if (definite && !restoredKey) {
          submission.current = null
          setRecoverKey(null)
          try {
            sessionStorage.removeItem(submissionKey)
          } catch {
            /* optional */
          }
        }
        if (restoredKey) submission.current = null
        setError(cause)
        setUncertain(!definite && !!submission.current)
      }
    } finally {
      if (mounted.current) setBusy(false)
    }
  }

  async function recover() {
    if (!recoverKey) return
    setBusy(true)
    try {
      await finish(await lookupSubmission(recoverKey))
    } catch (cause) {
      setError(cause)
    } finally {
      if (mounted.current) setBusy(false)
    }
  }

  function clearDraft() {
    setAutoUpdate(false)
    setSchedule(defaultSchedule)
    setDraftStarted(true)
    setDraft(emptyCompileDraft)
    setLocationRevision((v) => v + 1)
    setArgs('')
    setAttempted(false)
    setError(null)
    setPreview(false)
    submission.current = null
    filled.current = true
    setRecoverKey(null)
    try {
      sessionStorage.removeItem(submissionKey)
    } catch {
      /* optional */
    }
  }

  useEffect(() => {
    if (error) document.getElementById('compile-error')?.focus()
  }, [error])

  return {
    args,
    attempted,
    autoUpdate,
    busy,
    capability,
    clearDraft,
    config,
    draft,
    draftStarted,
    error,
    fieldErrors,
    locationRevision,
    original,
    preview,
    recover,
    recoverKey,
    savedDraft,
    savingError,
    schedule,
    setArgs,
    setAttempted,
    setAutoUpdate,
    setDraft,
    setDraftStarted,
    setError,
    setLocationRevision,
    setPreview,
    setSchedule,
    skillContent,
    skills,
    submit,
    uncertain,
    update,
    userResourceRoot,
    validate,
    buildRequest,
  }
}
