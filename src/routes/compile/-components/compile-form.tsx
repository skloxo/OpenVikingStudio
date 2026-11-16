import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '#/components/ui/button'
import { Textarea } from '#/components/ui/textarea'
import { copyTextToClipboard } from '#/lib/clipboard'
import { compileCommand } from '../-lib/commands'
import { locationLabel, sourceUris } from '../-lib/locations'
import { skillGuide } from '../-lib/skills'
import { ArgsEditor } from './args-editor'
import { CapabilityNotice } from './capability-notice'
import { CompileFormSkill } from './compile-form-skill'
import { CompileLocations } from './compile-locations'
import { ScheduleFields } from './schedule-fields'
import { CompileError, CompileShell } from './shared'
import { useCompileFormState } from './use-compile-form'

export function CompileForm({
  fromTask,
  sourceUri,
  target,
}: {
  fromTask?: string
  sourceUri?: string
  target?: string
}) {
  const { t } = useTranslation('compile')
  const form = useCompileFormState({ fromTask, sourceUri, target })

  function fieldError(key: keyof typeof form.fieldErrors) {
    return form.attempted && form.fieldErrors[key] ? (
      <p id={`error-${key}`} role="alert" className="text-xs text-rose-500">
        {form.fieldErrors[key]}
      </p>
    ) : null
  }

  const selected = form.skills.data.find((s) => s.uri === form.draft.skill)
  const guide = selected ? skillGuide(selected, t) : null
  const targetLabel = locationLabel(form.draft.to, form.userResourceRoot)

  return (
    <CompileShell title={t(target ? 'schedule.edit' : 'new')}>
      {!target && <CapabilityNotice capability={form.capability} />}
      {target && !form.config.isFetchedAfterMount && !form.config.isError && (
        <p role="status" className="text-sm text-muted-foreground">
          {t('loading')}
        </p>
      )}
      {target && form.config.isError && (
        <CompileError
          error={form.config.error}
          retry={() => void form.config.refetch()}
        />
      )}
      {target && form.config.data?.last_error && (
        <div role="status" className="break-words text-sm text-rose-500">
          <p>{t('schedule.lastRunFailed')}</p>
          <details className="mt-2">
            <summary className="cursor-pointer text-xs">
              {t('errors.details')}
            </summary>
            <p className="mt-1 whitespace-pre-wrap text-xs">
              {form.config.data.last_error}
            </p>
          </details>
        </div>
      )}
      {form.recoverKey && (
        <Button
          variant="outline"
          className="self-start"
          disabled={form.busy}
          onClick={() => void form.recover()}
        >
          {t('recover')}
        </Button>
      )}
      {fromTask && (
        <p className="text-sm text-muted-foreground">{t('rerunHint')}</p>
      )}
      {form.original.isError && (
        <CompileError
          error={form.original.error}
          retry={() => void form.original.refetch()}
        />
      )}
      {form.error != null && (
        <div id="compile-error" tabIndex={-1}>
          <CompileError error={form.error} />
        </div>
      )}
      {form.uncertain && (
        <p role="status" className="text-sm text-amber-600 dark:text-amber-400">
          {t('unknownSubmission')}
        </p>
      )}

      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          void form.submit()
        }}
        className="w-full min-w-0 space-y-5"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted-foreground">{t('formIntro')}</p>
          {!target &&
            !form.draftStarted &&
            Object.values(form.savedDraft).some(Boolean) && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={form.busy || form.uncertain}
                onClick={() => {
                  form.setDraft(form.savedDraft)
                  form.setDraftStarted(true)
                  form.setAttempted(false)
                  form.setError(null)
                  form.setLocationRevision((v) => v + 1)
                }}
              >
                {t('restoreDraft')}
              </Button>
            )}
        </div>

        <fieldset
          disabled={
            form.busy ||
            form.uncertain ||
            (!!target &&
              (!form.config.data ||
                !form.config.isFetchedAfterMount ||
                form.config.isError))
          }
          className="space-y-6 rounded-xl border bg-card p-5 disabled:opacity-60 sm:p-6"
        >
          <CompileFormSkill
            skillUri={form.draft.skill}
            onSkillChange={(uri) => form.update('skill', uri)}
            skills={form.skills}
            skillContent={form.skillContent}
            disabled={form.busy || form.uncertain}
            invalid={form.attempted && !!form.fieldErrors.skill}
            fieldError={fieldError('skill')}
            preview={form.preview}
            onPreviewChange={form.setPreview}
          />

          <CompileLocations
            key={form.locationRevision}
            sources={form.draft.sources}
            to={form.draft.to}
            onSources={(value) => form.update('sources', value)}
            onTarget={(value) => form.update('to', value)}
            attempted={form.attempted}
            sourceError={form.fieldErrors.sources}
            destinationError={form.fieldErrors.to}
            targetReadOnly={!!target}
          />

          <section className="space-y-2">
            <label
              htmlFor="compile-instruction"
              className="block text-sm font-medium"
            >
              {t('instruction')}{' '}
              <span className="ml-2 font-normal text-muted-foreground">
                {t('optional')}
              </span>
            </label>
            <Textarea
              id="compile-instruction"
              rows={2}
              placeholder={t('instructionPlaceholder')}
              value={form.draft.instruction}
              onChange={(e) => form.update('instruction', e.target.value)}
            />
          </section>

          <ScheduleFields
            enabled={form.autoUpdate}
            schedule={form.schedule}
            onEnabled={form.setAutoUpdate}
            onChange={form.setSchedule}
          />

          {!target && (
            <details id="compile-advanced" className="border-t pt-4">
              <summary className="cursor-pointer rounded text-sm font-medium focus-visible:outline-2 focus-visible:outline-ring">
                {t('advanced')}
              </summary>
              <ArgsEditor
                value={form.args}
                onChange={(value) => {
                  form.setDraftStarted(true)
                  form.setArgs(value)
                }}
              />
              <p className="mt-2 text-xs text-muted-foreground">
                {t('argsHint')}
              </p>
              {fieldError('args')}
            </details>
          )}
        </fieldset>

        <div className="sticky bottom-0 space-y-3 border-t bg-background py-4">
          {form.draft.skill &&
            sourceUris(form.draft.sources).length > 0 &&
            form.draft.to && (
              <p className="break-words text-sm">
                {t('submissionSummary', {
                  skill:
                    guide?.name ||
                    selected?.name ||
                    form.draft.skill.split('/').pop(),
                  count: sourceUris(form.draft.sources).length,
                  space: t(targetLabel.scope),
                  folder: targetLabel.path || t('spaceRoot'),
                })}
              </p>
            )}
          {!target && form.draftStarted && (
            <p className="text-xs text-muted-foreground">
              {t(form.savingError ? 'storageFailed' : 'draft')}
            </p>
          )}
          <div className="flex flex-wrap justify-between gap-3">
            {!target && (
              <Button
                type="button"
                variant="outline"
                disabled={form.autoUpdate}
                onClick={() => {
                  try {
                    if (!form.validate()) return
                    void copyTextToClipboard(
                      compileCommand(form.buildRequest()),
                    )
                      .then(() => toast.success(t('copied')))
                      .catch(form.setError)
                  } catch (cause) {
                    form.setError(cause)
                  }
                }}
              >
                {t('copyCommand')}
              </Button>
            )}
            <div className="flex gap-2">
              {!target && (
                <Button
                  type="button"
                  variant="ghost"
                  disabled={form.busy || form.uncertain}
                  onClick={form.clearDraft}
                >
                  {t('clear')}
                </Button>
              )}
              <Button
                type="submit"
                disabled={
                  form.busy ||
                  (target
                    ? !form.config.data ||
                      !form.config.isFetchedAfterMount ||
                      form.config.isError
                    : !form.recoverKey &&
                      !form.uncertain &&
                      (form.capability.isError ||
                        !form.capability.data?.can_create))
                }
              >
                {t(
                  form.busy
                    ? 'submitting'
                    : form.uncertain
                      ? 'retry'
                      : target || form.autoUpdate
                        ? 'schedule.save'
                        : 'start',
                )}
              </Button>
            </div>
          </div>
        </div>
      </form>
    </CompileShell>
  )
}
