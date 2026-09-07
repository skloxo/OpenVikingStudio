import * as React from 'react'
import { EyeIcon, PlayIcon, ShieldAlertIcon, ShieldIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import { Switch } from '#/components/ui/switch'
import { Textarea } from '#/components/ui/textarea'
import { applyClientRedaction } from '../-lib/settings-types'

const DEFAULT_SAMPLE_TEXT =
  'Authorization: Bearer sk-99887766aabbccddeeff001122, contact: fsk@8.129.0.26, phone: +86-13800138000, client_ip: 192.168.1.100'

export function PrivacyTab() {
  const { i18n, t } = useTranslation('settings')
  const isZh = i18n.resolvedLanguage?.startsWith('zh')

  const [maskCredentials, setMaskCredentials] = React.useState(true)
  const [maskPii, setMaskPii] = React.useState(true)
  const [sampleInput, setSampleInput] = React.useState(DEFAULT_SAMPLE_TEXT)
  const [sanitizedPreview, setSanitizedPreview] = React.useState(() =>
    applyClientRedaction(DEFAULT_SAMPLE_TEXT, {
      maskCredentials: true,
      maskPii: true,
    }),
  )

  const handlePreviewRedaction = () => {
    const result = applyClientRedaction(sampleInput, {
      maskCredentials,
      maskPii,
    })
    setSanitizedPreview(result)
    toast.success(isZh ? '脱敏预览已更新' : 'Sanitized preview updated')
  }

  return (
    <div className="space-y-4">
      {/* Section 1: Governance & Switches */}
      <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
        <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded-md bg-amber-500/10 text-amber-500 border border-amber-500/30">
                <ShieldIcon className="size-4" />
              </div>
              <div>
                <CardTitle className="text-sm font-semibold">
                  {t('hub.privacy.title')}
                </CardTitle>
                <p className="text-[11px] text-muted-foreground">
                  {t('hub.privacy.description')}
                </p>
              </div>
            </div>
            <Badge
              variant="outline"
              className="text-[11px] font-mono border-amber-500/30 bg-amber-500/10 text-amber-500"
            >
              {t('hub.privacy.activeRules')}: 5
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 px-5 py-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex items-center justify-between rounded-md border bg-muted/20 p-3">
              <div className="space-y-0.5 pr-2">
                <div className="text-xs font-semibold text-foreground">
                  {t('hub.privacy.toggleMask')}
                </div>
                <div className="text-[11px] text-muted-foreground">
                  {t('hub.privacy.toggleMaskDesc')}
                </div>
              </div>
              <Switch
                checked={maskCredentials}
                onCheckedChange={setMaskCredentials}
              />
            </div>
            <div className="flex items-center justify-between rounded-md border bg-muted/20 p-3">
              <div className="space-y-0.5 pr-2">
                <div className="text-xs font-semibold text-foreground">
                  {t('hub.privacy.piiMask')}
                </div>
                <div className="text-[11px] text-muted-foreground">
                  {t('hub.privacy.piiMaskDesc')}
                </div>
              </div>
              <Switch checked={maskPii} onCheckedChange={setMaskPii} />
            </div>
          </div>

          {/* Redaction Rules Table */}
          <div className="rounded-md border border-border/80 overflow-hidden mt-2">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b bg-muted/30 text-[11px] text-muted-foreground font-medium">
                  <th className="py-2 px-3">{t('hub.privacy.ruleName')}</th>
                  <th className="py-2 px-3">{t('hub.privacy.rulePattern')}</th>
                  <th className="py-2 px-3">{t('hub.privacy.ruleAction')}</th>
                  <th className="py-2 px-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50 font-mono text-[11px]">
                <tr>
                  <td className="py-2 px-3 font-sans font-medium text-foreground">
                    API Key / Token
                  </td>
                  <td className="py-2 px-3 text-muted-foreground">
                    sk-[a-zA-Z0-9]{'{20,}'}
                  </td>
                  <td className="py-2 px-3 font-sans text-cyan-500">
                    {t('hub.privacy.actionMask')}
                  </td>
                  <td className="py-2 px-3 text-center">
                    <Badge
                      variant="outline"
                      className="px-1.5 py-0 text-[11px] border-cyan-500/30 text-cyan-500"
                    >
                      Active
                    </Badge>
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-sans font-medium text-foreground">
                    Bearer Auth
                  </td>
                  <td className="py-2 px-3 text-muted-foreground">
                    Bearer\s+[a-zA-Z0-9._-]+
                  </td>
                  <td className="py-2 px-3 font-sans text-amber-500">
                    {t('hub.privacy.actionRedact')}
                  </td>
                  <td className="py-2 px-3 text-center">
                    <Badge
                      variant="outline"
                      className="px-1.5 py-0 text-[11px] border-cyan-500/30 text-cyan-500"
                    >
                      Active
                    </Badge>
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-sans font-medium text-foreground">
                    Phone Number (CN/Intl)
                  </td>
                  <td className="py-2 px-3 text-muted-foreground">
                    \+?[0-9]{'{10,14}'}
                  </td>
                  <td className="py-2 px-3 font-sans text-cyan-500">
                    {t('hub.privacy.actionMask')}
                  </td>
                  <td className="py-2 px-3 text-center">
                    <Badge
                      variant="outline"
                      className="px-1.5 py-0 text-[11px] border-cyan-500/30 text-cyan-500"
                    >
                      Active
                    </Badge>
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-sans font-medium text-foreground">
                    Email Address
                  </td>
                  <td className="py-2 px-3 text-muted-foreground">
                    [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+
                  </td>
                  <td className="py-2 px-3 font-sans text-cyan-500">
                    {t('hub.privacy.actionMask')}
                  </td>
                  <td className="py-2 px-3 text-center">
                    <Badge
                      variant="outline"
                      className="px-1.5 py-0 text-[11px] border-cyan-500/30 text-cyan-500"
                    >
                      Active
                    </Badge>
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-sans font-medium text-foreground">
                    IPv4 / Private Address
                  </td>
                  <td className="py-2 px-3 text-muted-foreground">
                    \b(?:[0-9]{'{1,3}'}\.){'{3}'}[0-9]{'{1,3}'}\b
                  </td>
                  <td className="py-2 px-3 font-sans text-cyan-500">
                    {t('hub.privacy.actionMask')}
                  </td>
                  <td className="py-2 px-3 text-center">
                    <Badge
                      variant="outline"
                      className="px-1.5 py-0 text-[11px] border-cyan-500/30 text-cyan-500"
                    >
                      Active
                    </Badge>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Section 2: Live Playground & Audit */}
      <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
        <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
              <EyeIcon className="size-4" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold">
                {t('hub.privacy.playgroundTitle')}
              </CardTitle>
              <p className="text-[11px] text-muted-foreground">
                {t('hub.privacy.playgroundDesc')}
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 px-5 py-4">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-foreground">
                {t('hub.privacy.inputLabel')}
              </span>
              <Button
                onClick={handlePreviewRedaction}
                size="sm"
                className="h-7 text-xs font-medium bg-cyan-600 hover:bg-cyan-700 text-white cursor-pointer"
              >
                <PlayIcon className="size-3 fill-current mr-1" />
                <span>{t('hub.privacy.previewBtn')}</span>
              </Button>
            </div>
            <Textarea
              value={sampleInput}
              onChange={(e) => setSampleInput(e.target.value)}
              placeholder={t('hub.privacy.inputPlaceholder')}
              rows={3}
              className="text-xs font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <span className="text-xs font-medium text-foreground">
              {t('hub.privacy.previewOutput')}
            </span>
            <div className="rounded-md border border-border/80 bg-muted/20 p-3 font-mono text-xs text-foreground select-all break-all whitespace-pre-wrap">
              {sanitizedPreview}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
