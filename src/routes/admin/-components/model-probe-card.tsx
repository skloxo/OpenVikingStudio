import { Loader2Icon, PlugZapIcon } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import { Input } from '#/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import { useAppConnection } from '#/hooks/use-app-connection'
import { showErrorToast } from '#/lib/error-toast'
import {
  supportsModelTest,
  testServerModelConnection,
  type ModelKind,
} from '../-lib/config-api'

export function ModelProbeCard({
  initialVlm,
  initialEmbedding,
}: {
  initialVlm?: Record<string, unknown>
  initialEmbedding?: Record<string, unknown>
}) {
  const { t } = useTranslation('adminConsole')
  const { connection } = useAppConnection()
  const [kind, setKind] = useState<ModelKind>('vlm')
  const baseCfg = kind === 'vlm' ? initialVlm || {} : initialEmbedding || {}
  const [provider, setProvider] = useState(String(baseCfg.provider || 'openai'))
  const [model, setModel] = useState(String(baseCfg.model || ''))
  const [apiBase, setApiBase] = useState(String(baseCfg.api_base || ''))
  const [apiKey, setApiKey] = useState('')
  const [testing, setTesting] = useState(false)
  const [probeResult, setProbeResult] = useState<{
    ok: boolean
    code?: string
    ms?: number
  } | null>(null)

  const handleKindChange = (next: ModelKind) => {
    setKind(next)
    const target = next === 'vlm' ? initialVlm || {} : initialEmbedding || {}
    setProvider(String(target.provider || 'openai'))
    setModel(String(target.model || ''))
    setApiBase(String(target.api_base || ''))
    setProbeResult(null)
  }

  const runTest = async () => {
    setTesting(true)
    setProbeResult(null)
    try {
      const fallback = kind === 'vlm' ? initialVlm || {} : initialEmbedding || {}
      const result = await testServerModelConnection(
        {
          accountId: connection.accountId,
          adminApiKey: connection.adminApiKey,
          apiKey: connection.apiKey,
        },
        {
          kind,
          config: {
            provider: provider.trim(),
            model: model.trim(),
            ...(apiBase.trim() ? { api_base: apiBase.trim() } : {}),
            ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
          },
          fallback,
        },
      )
      setProbeResult(result)
    } catch (error) {
      showErrorToast(error)
    } finally {
      setTesting(false)
    }
  }

  const canProbe = supportsModelTest(kind, provider)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <PlugZapIcon className="size-4 text-cyan-500" />
          {t('configuration.modelTestTitle')}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-1.5">
            <span className="text-xs font-medium">{t('configuration.modelKind')}</span>
            <Select
              value={kind}
              onValueChange={(v) => handleKindChange((v || 'vlm') as ModelKind)}
            >
              <SelectTrigger className="w-full text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="vlm">VLM</SelectItem>
                <SelectItem value="embedding">Embedding</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <span className="text-xs font-medium">{t('configuration.provider')}</span>
            <Input
              className="text-xs"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <span className="text-xs font-medium">{t('configuration.modelName')}</span>
            <Input
              className="text-xs"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <span className="text-xs font-medium">{t('configuration.apiBase')}</span>
            <Input
              className="font-mono text-xs"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Input
            type="password"
            className="max-w-sm text-xs"
            placeholder={t('configuration.apiKey')}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={testing || !canProbe}
            onClick={() => void runTest()}
          >
            {testing ? <Loader2Icon className="animate-spin" /> : <PlugZapIcon />}
            {t(testing ? 'actions.testingModel' : 'actions.testModel')}
          </Button>
          {probeResult && (
            <span
              className={
                probeResult.ok
                  ? 'text-xs font-medium text-cyan-600 dark:text-cyan-400'
                  : 'text-xs font-medium text-rose-500'
              }
            >
              {probeResult.ok
                ? t('configuration.modelOk', { ms: probeResult.ms ?? 0 })
                : t('configuration.modelFail', {
                    code: probeResult.code || 'FAILED',
                  })}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
