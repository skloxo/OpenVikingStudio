import { Maximize2Icon, Minimize2Icon, MinusIcon, PlusIcon, ScanIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'
import type { LiveContextMount } from '../-lib/model'
import { normalizeVikingUri } from '../-lib/uri'

export type ArrangerGraphItem = {
  entry: VikingFsEntry
  parentUri: string | null
  liveMount?: LiveContextMount
}

export function ContextGraph({
  rootUri,
  items,
  selectedUri,
  onSelect,
  onToggleExpand,
}: {
  rootUri: string
  items: ArrangerGraphItem[]
  selectedUri: string
  onSelect: (uri: string) => void
  onToggleExpand?: (uri: string) => void
}) {
  const { t } = useTranslation('arranger')
  const containerRef = useRef<HTMLDivElement | null>(null)
  const cyRef = useRef<import('cytoscape').Core | null>(null)
  const [fullscreen, setFullscreen] = useState(false)

  useEffect(() => {
    let active = true
    const container = containerRef.current
    if (!container) return

    void import('cytoscape').then(({ default: cytoscape }) => {
      if (!active || !containerRef.current) return

      const normalizedRoot = normalizeVikingUri(rootUri)
      const normSelected = selectedUri ? normalizeVikingUri(selectedUri) : ''
      const seen = new Set<string>()
      const elements: import('cytoscape').ElementDefinition[] = []

      for (const item of items) {
        const id = normalizeVikingUri(item.entry.uri)
        if (seen.has(id)) continue
        seen.add(id)
        const isRoot = id === normalizedRoot
        const isLive = Boolean(item.liveMount)
        elements.push({
          data: {
            id,
            label: isRoot ? item.entry.uri : item.entry.name || id.split('/').pop() || id,
            kind: isRoot ? 'root' : isLive ? 'live' : item.entry.isDir ? 'dir' : 'file',
            isDir: item.entry.isDir,
            selected: id === normSelected ? 'yes' : 'no',
          },
        })
        if (item.parentUri && seen.has(normalizeVikingUri(item.parentUri))) {
          const source = normalizeVikingUri(item.parentUri)
          if (source !== id) {
            elements.push({ data: { id: `${source}->${id}`, source, target: id } })
          }
        }
      }

      if (cyRef.current) {
        cyRef.current.destroy()
      }

      const cy = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: 'node',
            style: {
              label: 'data(label)',
              'font-size': 12,
              'text-valign': 'center',
              'text-halign': 'center',
              color: '#e2e8f0',
              'background-color': '#1e293b',
              'border-width': 1.5,
              'border-color': '#475569',
              shape: 'round-rectangle',
              padding: '10px',
              width: 'label',
              height: 30,
              'text-wrap': 'ellipsis',
              'text-max-width': '160px',
            },
          },
          {
            selector: 'node[kind = "root"]',
            style: {
              'background-color': '#0f172a',
              'border-color': '#38bdf8',
              'border-width': 2,
              'font-weight': 'bold',
            },
          },
          {
            selector: 'node[kind = "dir"]',
            style: {
              'background-color': '#1e293b',
              'border-color': '#64748b',
            },
          },
          {
            selector: 'node[kind = "live"]',
            style: {
              'background-color': '#083344',
              'border-color': '#06b6d4',
              color: '#cffafe',
            },
          },
          {
            selector: 'node[selected = "yes"]',
            style: {
              'border-color': '#22d3ee',
              'border-width': 3,
              'background-color': '#164e63',
            },
          },
          {
            selector: 'edge',
            style: {
              width: 1.5,
              'line-color': '#475569',
              'target-arrow-color': '#475569',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
            },
          },
        ],
        layout: {
          name: 'breadthfirst',
          directed: true,
          padding: 24,
          spacingFactor: 1.35,
          roots: seen.has(normalizedRoot) ? [normalizedRoot] : undefined,
        },
        minZoom: 0.25,
        maxZoom: 2.5,
      })

      cy.on('tap', 'node', (evt) => {
        const node = evt.target
        const id = node.id()
        onSelect(id)
        if (node.data('isDir') && onToggleExpand) {
          onToggleExpand(id)
        }
      })

      cyRef.current = cy
    })

    return () => {
      active = false
      cyRef.current?.destroy()
      cyRef.current = null
    }
  }, [items, onSelect, onToggleExpand, rootUri, selectedUri])

  return (
    <div
      className={cn(
        'relative flex flex-col overflow-hidden rounded-xl border bg-slate-950/95',
        fullscreen ? 'fixed inset-4 z-50 shadow-2xl' : 'h-[520px] w-full',
      )}
    >
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2 text-xs text-slate-300">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-cyan-500" />
            {t('live.badge')}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-slate-400" />
            {t('start.staticTitle')}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Zoom out"
            onClick={() => {
              const cy = cyRef.current
              if (cy) cy.zoom(cy.zoom() * 0.85)
            }}
          >
            <MinusIcon className="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Zoom in"
            onClick={() => {
              const cy = cyRef.current
              if (cy) cy.zoom(cy.zoom() * 1.15)
            }}
          >
            <PlusIcon className="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            title={t('actions.fitGraph')}
            aria-label={t('actions.fitGraph')}
            onClick={() => cyRef.current?.fit(undefined, 28)}
          >
            <ScanIcon className="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            title={t('actions.fullscreen')}
            aria-label={t('actions.fullscreen')}
            onClick={() => setFullscreen((prev) => !prev)}
          >
            {fullscreen ? (
              <Minimize2Icon className="size-3.5" />
            ) : (
              <Maximize2Icon className="size-3.5" />
            )}
          </Button>
        </div>
      </div>
      <div ref={containerRef} className="min-h-0 flex-1 w-full" />
    </div>
  )
}
