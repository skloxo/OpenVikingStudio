import { useTranslation } from 'react-i18next'
import type { UpdateSchedule } from '../-lib/api'
import { CompileSelect } from './compile-select'

const timeParts = ['hour', 'minute'] as const

export const defaultSchedule: UpdateSchedule = {
  frequency: 'daily',
  hour: 9,
  minute: 0,
}

export function ScheduleFields({
  enabled,
  schedule,
  onEnabled,
  onChange,
  showToggle = true,
}: {
  showToggle?: boolean
  enabled: boolean
  schedule: UpdateSchedule
  onEnabled: (enabled: boolean) => void
  onChange: (schedule: UpdateSchedule) => void
}) {
  const { t } = useTranslation('compile')
  return (
    <section className={showToggle ? 'space-y-3 border-t pt-4' : 'space-y-3'}>
      {showToggle && (
        <label className="flex items-center gap-2 text-sm font-medium">
          <input
            type="checkbox"
            className="size-4 accent-cyan-500"
            checked={enabled}
            onChange={(event) => onEnabled(event.target.checked)}
          />
          {t('schedule.enabled')}
        </label>
      )}
      {enabled && (
        <div className="flex flex-wrap items-end gap-4">
          <div className="space-y-1 text-sm">
            <span className="block">{t('schedule.frequency')}</span>
            <CompileSelect
              label={t('schedule.frequency')}
              className="min-w-28"
              value={schedule.frequency}
              options={[
                { value: 'daily', label: t('schedule.daily') },
                { value: 'weekly', label: t('schedule.weekly') },
              ]}
              onValueChange={(value) =>
                onChange(
                  value === 'weekly'
                    ? {
                        frequency: 'weekly',
                        weekday: 1,
                        hour: schedule.hour,
                        minute: schedule.minute,
                      }
                    : {
                        frequency: 'daily',
                        hour: schedule.hour,
                        minute: schedule.minute,
                      },
                )
              }
            />
          </div>
          {schedule.frequency === 'weekly' && (
            <div className="space-y-1 text-sm">
              <span className="block">{t('schedule.weekday')}</span>
              <CompileSelect
                label={t('schedule.weekday')}
                className="min-w-28"
                value={String(schedule.weekday)}
                options={Array.from({ length: 7 }, (_, index) => ({
                  value: String(index + 1),
                  label: t(`schedule.weekdays.${index + 1}` as never),
                }))}
                onValueChange={(value) =>
                  onChange({ ...schedule, weekday: Number(value) })
                }
              />
            </div>
          )}
          <fieldset className="space-y-1 text-sm">
            <legend>{t('schedule.time')}</legend>
            <div className="flex items-center gap-2">
              {timeParts.map((part) => (
                <CompileSelect
                  key={part}
                  label={t(`schedule.${part}`)}
                  className="min-w-18 tabular-nums"
                  value={String(schedule[part])}
                  options={Array.from(
                    { length: part === 'hour' ? 24 : 60 },
                    (_, value) => ({
                      value: String(value),
                      label: String(value).padStart(2, '0'),
                    }),
                  )}
                  onValueChange={(value) =>
                    onChange({ ...schedule, [part]: Number(value) })
                  }
                />
              ))}
            </div>
          </fieldset>
        </div>
      )}
      {showToggle && (
        <p className="text-xs leading-relaxed text-muted-foreground">
          {enabled
            ? `${t('schedule.saveHint')} ${t('schedule.timezone')}`
            : t('schedule.manualHint')}
        </p>
      )}
    </section>
  )
}
