import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BookOpenIcon, FileTextIcon, SearchIcon, XIcon } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'

export interface WikiDocItem {
  uri: string
  name: string
  category: string
  size_bytes: number
  mod_time: string
  preview: string
}

interface WikiDocumentPickerProps {
  onSelect: (uri: string, name: string) => void
  currentUri?: string
}

export function WikiDocumentPicker({ onSelect, currentUri }: WikiDocumentPickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<string>('all')

  const { data: documents = [], isLoading } = useQuery<WikiDocItem[]>({
    queryKey: ['wiki-dehydrate-documents', search, category],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (search.trim()) params.append('search', search.trim())
      if (category !== 'all') params.append('category', category)
      params.append('limit', '100')
      const res = await ovClient.instance.get(`/api/v1/wiki/dehydrate/documents?${params.toString()}`)
      return (res as { data: WikiDocItem[] }).data
    },
    enabled: isOpen,
    staleTime: 30000,
  })

  const categories = ['all', 'decisions', 'evolution_lessons', 'benchmarks', 'master_blueprint', 'root']

  return (
    <>
      <Button
        size="sm"
        variant="outline"
        className="h-6 text-xs px-2.5 font-medium border-cyan-500/40 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10 cursor-pointer"
        onClick={() => setIsOpen(true)}
      >
        <BookOpenIcon className="size-3 mr-1" />
        知识库真实文档库 (600+)
      </Button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <div className="flex h-130 w-full max-w-2xl flex-col rounded-md border border-border bg-card p-3 shadow-lg">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <BookOpenIcon className="size-4 text-cyan-500" />
                <span className="text-xs font-semibold text-foreground">
                  挑选 VikingFS 真实知识库文档进行抽稀
                </span>
                <span className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono text-muted-foreground">
                  {documents.length} 篇可用
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="text-muted-foreground hover:text-foreground cursor-pointer"
              >
                <XIcon className="size-4" />
              </button>
            </div>

            <div className="flex flex-col gap-2 py-2">
              <div className="relative">
                <SearchIcon className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="搜索真实 Wiki 文档名称或 URI..."
                  className="w-full rounded-md border border-input bg-background pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:border-cyan-500 focus:outline-none font-mono"
                />
              </div>

              <div className="flex flex-wrap items-center gap-1.5">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setCategory(cat)}
                    className={`rounded px-2 py-0.5 text-xs font-mono transition-colors cursor-pointer ${
                      category === cat
                        ? 'bg-cyan-50 dark:bg-cyan-950/60 text-cyan-800 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-700 font-semibold'
                        : 'bg-muted/50 text-muted-foreground hover:text-foreground border border-border/60'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
              {isLoading ? (
                <div className="flex h-32 items-center justify-center text-xs text-muted-foreground">
                  正在扫描 VikingFS 知识库文档...
                </div>
              ) : documents.length === 0 ? (
                <div className="flex h-32 items-center justify-center text-xs text-muted-foreground">
                  未找到匹配的 Wiki 文档
                </div>
              ) : (
                documents.map((doc) => {
                  const isSelected = currentUri === doc.uri
                  return (
                    <div
                      key={doc.uri}
                      onClick={() => {
                        onSelect(doc.uri, doc.name)
                        setIsOpen(false)
                      }}
                      className={`flex flex-col gap-1 rounded-md border p-2.5 transition-colors cursor-pointer ${
                        isSelected
                          ? 'border-cyan-500/60 bg-cyan-500/10'
                          : 'border-border/60 bg-muted/20 hover:border-border hover:bg-muted/40'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 truncate">
                          <FileTextIcon className="size-3.5 shrink-0 text-cyan-500" />
                          <span className="text-xs font-medium text-foreground truncate">{doc.name}</span>
                          <span className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono text-muted-foreground">
                            {doc.category}
                          </span>
                        </div>
                        <span className="text-xs font-mono text-muted-foreground shrink-0 tabular-nums">
                          {(doc.size_bytes / 1024).toFixed(1)} KB
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground font-mono truncate">{doc.preview}</div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
