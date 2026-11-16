import { useMutation } from '@tanstack/react-query'
import { Loader2Icon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { Input } from '#/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import { mountLiveContext } from '../-lib/api'
import type {
  LiveContextMount,
  McpCatalog,
  McpCatalogTool,
} from '../-lib/model'
import {
  initialSchemaArguments,
  prepareSchemaArguments,
  validateSchemaArguments,
  type SchemaFormObject,
} from '../-lib/schema'
import { mcpServerNameFromToolUri, resolveMountNodeUri } from '../-lib/uri'
import { SchemaArgumentsForm } from './schema-arguments-form'

export function MountToolDialog({
  open,
  onOpenChange,
  parentUri,
  catalog,
  initialMount,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  parentUri: string
  catalog?: McpCatalog
  initialMount?: LiveContextMount
  onSuccess: (nodeUri: string) => void
}) {
  const { t } = useTranslation('arranger')
  const editing = Boolean(initialMount)
  const servers = catalog?.servers || []

  const initialServer =
    (initialMount?.tool_uri &&
      mcpServerNameFromToolUri(initialMount.tool_uri)) ||
    servers[0]?.name ||
    ''

  const [serverName, setServerName] = useState(initialServer)
  const [toolUri, setToolUri] = useState(initialMount?.tool_uri || '')
  const [nodeName, setNodeName] = useState(
    initialMount?.node_uri.split('/').pop() || '',
  )
  const [title, setTitle] = useState(initialMount?.title || '')
  const [description, setDescription] = useState(initialMount?.description || '')
  const [timeoutSeconds, setTimeoutSeconds] = useState(
    String(initialMount?.timeout_seconds || 60),
  )
  const [tagsText, setTagsText] = useState((initialMount?.tags || []).join(', '))
  const [argsValue, setArgsValue] = useState<SchemaFormObject>(
    initialMount?.arguments || {},
  )
  const [argErrors, setArgErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState('')

  const serverTools =
    servers.find((s) => s.name === serverName)?.tools || []
  const selectedTool: McpCatalogTool | undefined = catalog?.tools.find(
    (item) => item.uri === toolUri,
  )

  useEffect(() => {
    if (!open) return
    const nextServer =
      (initialMount?.tool_uri &&
        mcpServerNameFromToolUri(initialMount.tool_uri)) ||
      servers[0]?.name ||
      ''
    setServerName(nextServer)
    const firstTool = servers.find((s) => s.name === nextServer)?.tools[0]
    const nextToolUri = initialMount?.tool_uri || firstTool?.uri || ''
    setToolUri(nextToolUri)
    setNodeName(initialMount?.node_uri.split('/').pop() || '')
    setTitle(initialMount?.title || firstTool?.tool.title || '')
    setDescription(initialMount?.description || '')
    setTimeoutSeconds(String(initialMount?.timeout_seconds || 60))
    setTagsText((initialMount?.tags || []).join(', '))
    const toolObj = catalog?.tools.find((item) => item.uri === nextToolUri)
    setArgsValue(
      toolObj
        ? initialSchemaArguments(
            toolObj.tool.inputSchema,
            initialMount?.arguments || {},
          )
        : initialMount?.arguments || {},
    )
    setArgErrors({})
    setFormError('')
  }, [open, initialMount, catalog])

  const mountMutation = useMutation({
    mutationFn: async () => {
      if (!nodeName.trim() || !toolUri || !title.trim()) {
        throw new Error(t('validation.mountRequired'))
      }
      const timeoutNum = Number(timeoutSeconds)
      if (!Number.isFinite(timeoutNum) || timeoutNum <= 0) {
        throw new Error(t('validation.invalidTimeout'))
      }
      const schema = selectedTool?.tool.inputSchema
      if (schema) {
        const errs = validateSchemaArguments(schema, argsValue)
        if (Object.keys(errs).length) {
          setArgErrors(errs)
          throw new Error(t('validation.invalidArguments'))
        }
      }
      const nodeUri = resolveMountNodeUri(
        parentUri,
        nodeName.trim(),
        initialMount?.node_uri,
      )
      const tags = tagsText
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean)
      await mountLiveContext({
        node_uri: nodeUri,
        tool_uri: toolUri,
        title: title.trim(),
        description: description.trim() || undefined,
        timeout_seconds: timeoutNum,
        arguments: schema
          ? prepareSchemaArguments(schema, argsValue)
          : argsValue,
        tags: tags.length ? tags : undefined,
      })
      return nodeUri
    },
    onSuccess: (nodeUri) => {
      toast.success(t('save.saved'))
      onSuccess(nodeUri)
      onOpenChange(false)
    },
    onError: (err) => {
      setFormError(err instanceof Error ? err.message : String(err))
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>
            {t(editing ? 'actions.editMount' : 'dialogs.mount.title')}
          </DialogTitle>
          <DialogDescription>{t('dialogs.mount.description')}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <span className="text-xs font-medium">{t('fields.server')}</span>
              <Select
                value={serverName}
                onValueChange={(nextServer) => {
                  const srv = nextServer || ''
                  setServerName(srv)
                  const first = servers.find((s) => s.name === srv)?.tools[0]
                  setToolUri(first?.uri || '')
                  if (first) {
                    setArgsValue(initialSchemaArguments(first.tool.inputSchema))
                  }
                }}
              >
                <SelectTrigger className="w-full text-xs">
                  <SelectValue placeholder={t('mount.selectServer')} />
                </SelectTrigger>
                <SelectContent>
                  {servers.map((srv) => (
                    <SelectItem key={srv.name} value={srv.name}>
                      {srv.name} (
                      {t('mount.toolCount', { count: srv.tools.length })})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-medium">{t('fields.tool')}</span>
              <Select
                value={toolUri}
                onValueChange={(nextUri) => {
                  const uri = nextUri || ''
                  setToolUri(uri)
                  const tool = catalog?.tools.find((item) => item.uri === uri)
                  if (tool) {
                    if (!title) setTitle(tool.tool.title || tool.tool.name)
                    if (!nodeName) setNodeName(`${tool.tool.name}.md`)
                    setArgsValue(initialSchemaArguments(tool.tool.inputSchema))
                  }
                }}
              >
                <SelectTrigger className="w-full text-xs">
                  <SelectValue placeholder={t('mount.selectTool')} />
                </SelectTrigger>
                <SelectContent>
                  {serverTools.map((item) => (
                    <SelectItem key={item.uri} value={item.uri}>
                      {item.tool.title || item.tool.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <span className="text-xs font-medium">{t('fields.name')}</span>
              <Input
                className="font-mono text-xs"
                disabled={editing}
                placeholder={t('fields.mountNamePlaceholder')}
                value={nodeName}
                onChange={(e) => setNodeName(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <span className="text-xs font-medium">{t('fields.title')}</span>
              <Input
                className="text-xs"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <span className="text-xs font-medium">{t('fields.timeout')}</span>
              <Input
                type="number"
                className="text-xs"
                value={timeoutSeconds}
                onChange={(e) => setTimeoutSeconds(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <span className="text-xs font-medium">{t('fields.tags')}</span>
              <Input
                className="text-xs"
                placeholder={t('fields.tagsPlaceholder')}
                value={tagsText}
                onChange={(e) => setTagsText(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <span className="text-xs font-medium">{t('fields.description')}</span>
            <Input
              className="text-xs"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {selectedTool ? (
            <SchemaArgumentsForm
              schema={selectedTool.tool.inputSchema}
              value={argsValue}
              errors={argErrors}
              onChange={(next) => {
                setArgsValue(next)
                setArgErrors({})
              }}
            />
          ) : (
            <p className="text-xs text-muted-foreground">
              {t('mount.chooseToolFirst')}
            </p>
          )}

          {formError && <p className="text-xs text-rose-500">{formError}</p>}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            {t('actions.cancel')}
          </Button>
          <Button
            type="button"
            disabled={mountMutation.isPending}
            onClick={() => mountMutation.mutate()}
          >
            {mountMutation.isPending && <Loader2Icon className="animate-spin" />}
            {t('actions.confirm')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
