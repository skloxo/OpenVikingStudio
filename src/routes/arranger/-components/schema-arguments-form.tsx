import { PlusIcon, Trash2Icon } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import { Switch } from '#/components/ui/switch'
import { Textarea } from '#/components/ui/textarea'
import type { JsonSchema } from '../-lib/model'
import {
  isPlainObject,
  normalizeSchemaNode,
  primarySchemaType,
  type SchemaFormObject,
} from '../-lib/schema'

function FieldBadge({ required }: { required: boolean }) {
  const { t } = useTranslation('arranger')
  return (
    <Badge
      variant="outline"
      className={
        required
          ? 'border-cyan-500/40 bg-cyan-500/10 text-xs text-cyan-600 dark:text-cyan-400'
          : 'text-xs text-muted-foreground'
      }
    >
      {required ? t('fields.required') : t('fields.optional')}
    </Badge>
  )
}

function SchemaField({
  name,
  schema,
  rootSchema,
  value,
  required,
  errors,
  path,
  onChange,
}: {
  name: string
  schema: JsonSchema
  rootSchema: JsonSchema
  value: unknown
  required: boolean
  errors: Record<string, string>
  path: string
  onChange: (next: unknown) => void
}) {
  const { t } = useTranslation('arranger')
  const node = normalizeSchemaNode(schema, rootSchema)
  const type = primarySchemaType(node)
  const label = node.title || name
  const errKey = errors[path]

  if (Array.isArray(node.enum) && node.enum.length > 0) {
    const serialized = value === undefined ? '' : JSON.stringify(value)
    return (
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium">{label}</span>
          <FieldBadge required={required} />
        </div>
        {node.description && (
          <p className="text-xs text-muted-foreground">{node.description}</p>
        )}
        <Select
          value={serialized || '__unset__'}
          onValueChange={(raw) => {
            if (!raw || raw === '__unset__') onChange(undefined)
            else onChange(JSON.parse(raw))
          }}
        >
          <SelectTrigger className="w-full text-xs">
            <SelectValue placeholder={t('mount.selectValue')} />
          </SelectTrigger>
          <SelectContent>
            {!required && (
              <SelectItem value="__unset__">{t('mount.notSet')}</SelectItem>
            )}
            {node.enum.map((opt, idx) => (
              <SelectItem key={idx} value={JSON.stringify(opt)}>
                {String(opt)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {errKey && (
          <p className="text-xs text-rose-500">{t('validation.required')}</p>
        )}
      </div>
    )
  }

  if (type === 'boolean') {
    return (
      <div className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2">
        <div className="min-w-0 space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium">{label}</span>
            <FieldBadge required={required} />
          </div>
          {node.description && (
            <p className="text-xs text-muted-foreground">{node.description}</p>
          )}
        </div>
        <Switch checked={value === true} onCheckedChange={onChange} />
      </div>
    )
  }

  if (type === 'object' && node.properties) {
    const obj = isPlainObject(value) ? value : {}
    const reqSet = new Set(node.required || [])
    return (
      <fieldset className="space-y-3 rounded-lg border p-3">
        <legend className="px-1 text-xs font-medium">
          {label} <FieldBadge required={required} />
        </legend>
        {Object.entries(node.properties).map(([childKey, childSchema]) => (
          <SchemaField
            key={childKey}
            name={childKey}
            schema={childSchema}
            rootSchema={rootSchema}
            value={obj[childKey]}
            required={reqSet.has(childKey)}
            errors={errors}
            path={path ? `${path}.${childKey}` : childKey}
            onChange={(nextChild) => {
              const nextObj = { ...obj }
              if (nextChild === undefined) delete nextObj[childKey]
              else nextObj[childKey] = nextChild
              onChange(nextObj)
            }}
          />
        ))}
      </fieldset>
    )
  }

  if (type === 'array') {
    const arr = Array.isArray(value) ? value : []
    const itemSchema = !Array.isArray(node.items) && node.items ? node.items : { type: 'string' }
    return (
      <div className="space-y-2 rounded-lg border p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium">{label}</span>
            <FieldBadge required={required} />
          </div>
          <Button
            type="button"
            variant="outline"
            size="xs"
            onClick={() => onChange([...arr, ''])}
          >
            <PlusIcon className="size-3" />
            {t('mount.addItem')}
          </Button>
        </div>
        {arr.map((item, idx) => (
          <div key={idx} className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              <SchemaField
                name={t('mount.itemLabel', { index: idx + 1 })}
                schema={itemSchema}
                rootSchema={rootSchema}
                value={item}
                required
                errors={errors}
                path={`${path}[${idx}]`}
                onChange={(nextItem) => {
                  const copy = [...arr]
                  copy[idx] = nextItem
                  onChange(copy)
                }}
              />
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              aria-label={t('mount.removeItem')}
              onClick={() => onChange(arr.filter((_, i) => i !== idx))}
            >
              <Trash2Icon className="size-3.5 text-rose-500" />
            </Button>
          </div>
        ))}
      </div>
    )
  }

  if (type === 'number' || type === 'integer') {
    return (
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium">{label}</span>
          <FieldBadge required={required} />
        </div>
        {node.description && (
          <p className="text-xs text-muted-foreground">{node.description}</p>
        )}
        <Input
          type="number"
          className="text-xs"
          step={type === 'integer' ? 1 : 'any'}
          value={value === undefined || value === null ? '' : String(value)}
          onChange={(e) => {
            const raw = e.target.value
            onChange(raw === '' ? undefined : Number(raw))
          }}
        />
        {errKey && (
          <p className="text-xs text-rose-500">{t('validation.invalidArguments')}</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium">{label}</span>
        <FieldBadge required={required} />
      </div>
      {node.description && (
        <p className="text-xs text-muted-foreground">{node.description}</p>
      )}
      <Input
        className="text-xs"
        value={typeof value === 'string' ? value : value === undefined ? '' : JSON.stringify(value)}
        onChange={(e) => onChange(e.target.value)}
      />
      {errKey && (
        <p className="text-xs text-rose-500">{t('validation.required')}</p>
      )}
    </div>
  )
}

export function SchemaArgumentsForm({
  schema,
  value,
  errors,
  onChange,
}: {
  schema: JsonSchema
  value: SchemaFormObject
  errors: Record<string, string>
  onChange: (next: SchemaFormObject) => void
}) {
  const { t } = useTranslation('arranger')
  const [jsonMode, setJsonMode] = useState(false)
  const [rawText, setRawText] = useState(() => JSON.stringify(value, null, 2))
  const [rawError, setRawError] = useState('')
  const properties = normalizeSchemaNode(schema, schema).properties || {}
  const required = new Set(normalizeSchemaNode(schema, schema).required || [])

  if (!Object.keys(properties).length && !jsonMode) {
    return (
      <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
        {t('mount.noArguments')}
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium">{t('mount.argumentsTitle')}</span>
        <Button
          type="button"
          variant="ghost"
          size="xs"
          onClick={() => {
            if (!jsonMode) setRawText(JSON.stringify(value, null, 2))
            setRawError('')
            setJsonMode((prev) => !prev)
          }}
        >
          {t('mount.editAsJson')}
        </Button>
      </div>

      {jsonMode ? (
        <div className="space-y-1.5">
          <Textarea
            rows={6}
            className="font-mono text-xs"
            value={rawText}
            onChange={(e) => {
              const text = e.target.value
              setRawText(text)
              try {
                const parsed = JSON.parse(text || '{}')
                if (!isPlainObject(parsed)) throw new Error('object')
                setRawError('')
                onChange(parsed)
              } catch {
                setRawError(t('mount.expectedJsonObject'))
              }
            }}
          />
          {rawError && <p className="text-xs text-rose-500">{rawError}</p>}
        </div>
      ) : (
        <div className="space-y-3">
          {Object.entries(properties).map(([key, childSchema]) => (
            <SchemaField
              key={key}
              name={key}
              schema={childSchema}
              rootSchema={schema}
              value={value[key]}
              required={required.has(key)}
              errors={errors}
              path={key}
              onChange={(nextChild) => {
                const nextObj = { ...value }
                if (nextChild === undefined) delete nextObj[key]
                else nextObj[key] = nextChild
                onChange(nextObj)
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
