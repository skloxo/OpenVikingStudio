import { Link } from '@tanstack/react-router'
import { EyeIcon } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '#/components/ui/dialog'
import { skillGuide, type useCompileSkills } from '../-lib/skills'
import { CompileError } from './shared'
import { SkillPicker } from './skill-picker'

type SkillsState = ReturnType<typeof useCompileSkills>

export function CompileFormSkill({
  skillUri,
  onSkillChange,
  skills,
  skillContent,
  disabled,
  invalid,
  fieldError,
  preview,
  onPreviewChange,
}: {
  skillUri: string
  onSkillChange: (uri: string) => void
  skills: SkillsState
  skillContent: {
    isPending: boolean
    isError: boolean
    error: unknown
    data?: { content: string }
    refetch: () => Promise<unknown>
  }
  disabled: boolean
  invalid: boolean
  fieldError: ReactNode
  preview: boolean
  onPreviewChange: (open: boolean) => void
}) {
  const { t } = useTranslation('compile')
  const [openFallback] = useState(false)
  const selected = skills.data.find((s) => s.uri === skillUri)
  const guide = selected ? skillGuide(selected, t) : null
  const skillGroups = [
    ['builtinSkills', skills.builtin],
    ['mySkills', skills.mine],
    ['sharedSkills', skills.shared],
  ] as const

  const anyPending =
    skills.builtin.isPending || skills.mine.isPending || skills.shared.isPending
  const allPending =
    skills.builtin.isPending && skills.mine.isPending && skills.shared.isPending
  const noErrors =
    !skills.builtin.isError && !skills.mine.isError && !skills.shared.isError

  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <label htmlFor="compile-skill" className="block text-sm font-medium">
          {t('skill')} <span className="text-rose-500">*</span>
        </label>
        {skillUri && (
          <Dialog
            open={preview ?? openFallback}
            onOpenChange={onPreviewChange}
          >
            <DialogTrigger
              render={<Button type="button" variant="ghost" size="sm" />}
            >
              <EyeIcon className="size-4" />
              {t('preview')}
            </DialogTrigger>
            <DialogContent className="flex max-h-[80dvh] min-w-0 flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
              <DialogHeader className="shrink-0 border-b py-5 pl-6 pr-14">
                <DialogTitle className="break-words text-lg leading-snug">
                  {guide?.name || selected?.name || t('preview')}
                </DialogTitle>
                <DialogDescription className="break-all text-xs">
                  {skillUri}
                </DialogDescription>
              </DialogHeader>
              <div className="min-h-0 overflow-auto overscroll-contain px-6 py-5">
                {skillContent.isPending ? (
                  <p role="status" className="text-sm text-muted-foreground">
                    {t('loading')}
                  </p>
                ) : skillContent.isError ? (
                  <CompileError
                    error={skillContent.error}
                    retry={() => void skillContent.refetch()}
                  />
                ) : skillContent.data?.content ? (
                  <pre className="whitespace-pre-wrap break-words text-xs leading-relaxed">
                    {skillContent.data.content}
                  </pre>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {t('skillContentEmpty')}
                  </p>
                )}
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <SkillPicker
        invalid={invalid}
        disabled={disabled || allPending}
        loading={anyPending}
        value={skillUri}
        skills={skills.data}
        onChange={(uri) => {
          onSkillChange(uri)
          onPreviewChange(false)
        }}
      />
      {fieldError}

      <p className="text-xs text-muted-foreground">{t('skillLocationHint')}</p>

      {skillGroups.map(
        ([label, query]) =>
          query.isError && (
            <div key={label} className="space-y-2">
              <p className="text-sm">
                {t('skillGroupFailed', { group: t(label) })}
              </p>
              <CompileError
                error={query.error}
                retry={() => void query.refetch()}
              />
            </div>
          ),
      )}

      {!anyPending && noErrors && !skills.data.length && (
        <p className="text-sm text-muted-foreground">
          {t('noSkills')}{' '}
          <Link to="/skills" className="text-cyan-500 underline">
            {t('manageSkills')}
          </Link>
        </p>
      )}

      {selected?.metadataError && (
        <p className="text-xs text-muted-foreground">
          {t('skillMetadataFailed')}{' '}
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => void skills.builtin.refetch()}
          >
            {t('retry')}
          </Button>
        </p>
      )}
    </section>
  )
}
