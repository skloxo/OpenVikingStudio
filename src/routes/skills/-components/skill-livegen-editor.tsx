import { CodeIcon, FileCheckIcon, Wand2Icon } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'

interface SkillLiveGenEditorProps {
  skillName: string
  setSkillName: (val: string) => void
  skillDescription: string
  setSkillDescription: (val: string) => void
  allowedToolsStr: string
  setAllowedToolsStr: (val: string) => void
  draftContent: string
  setDraftContent: (val: string) => void
  onGenerateScaffold: () => void
  onValidate: () => void
  isScaffolding: boolean
  isValidating: boolean
}

export function SkillLiveGenEditor({
  skillName,
  setSkillName,
  skillDescription,
  setSkillDescription,
  allowedToolsStr,
  setAllowedToolsStr,
  draftContent,
  setDraftContent,
  onGenerateScaffold,
  onValidate,
  isScaffolding,
  isValidating,
}: SkillLiveGenEditorProps) {
  const lineCount = draftContent.split('\n').length

  const getLineStatusBadge = (lines: number) => {
    if (lines > 500) return <Badge variant="outline" className="text-xs font-mono text-rose-400 border-rose-500/40">🚫 超过 500 行阻断红线</Badge>
    if (lines > 400) return <Badge variant="outline" className="text-xs font-mono text-rose-400 border-rose-500/40">⚠️ 逼近 400 行预警线</Badge>
    if (lines > 300) return <Badge variant="outline" className="text-xs font-mono text-amber-400 border-amber-500/40">⚡ 300-400 行成长区</Badge>
    if (lines >= 100) return <Badge variant="outline" className="text-xs font-mono text-cyan-400 border-cyan-500/40">⭐ 100~300 行黄金甜点区</Badge>
    return <Badge variant="outline" className="text-xs font-mono text-muted-foreground border-border">📦 &lt; 100 行轻量紧凑</Badge>
  }

  return (
    <Card className="p-3.5 bg-card/60 border-border/70 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold font-mono flex items-center gap-1.5 text-foreground">
          <CodeIcon className="size-3.5 text-cyan-400" /> SKILL.md 编辑器
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-muted-foreground">行数: {lineCount}</span>
          {getLineStatusBadge(lineCount)}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs font-mono text-muted-foreground">技能名称 (kebab-case):</label>
          <input
            type="text"
            value={skillName}
            onChange={(e) => setSkillName(e.target.value)}
            className="w-full mt-1 px-2 py-1 text-xs font-mono bg-background border border-border rounded text-foreground focus:outline-none focus:border-cyan-500"
          />
        </div>
        <div>
          <label className="text-xs font-mono text-muted-foreground">工具列表 (逗号分隔):</label>
          <input
            type="text"
            value={allowedToolsStr}
            onChange={(e) => setAllowedToolsStr(e.target.value)}
            className="w-full mt-1 px-2 py-1 text-xs font-mono bg-background border border-border rounded text-foreground focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      <div>
        <label className="text-xs font-mono text-muted-foreground">技能描述与意图触发词:</label>
        <input
          type="text"
          value={skillDescription}
          onChange={(e) => setSkillDescription(e.target.value)}
          className="w-full mt-1 px-2 py-1 text-xs font-mono bg-background border border-border rounded text-foreground focus:outline-none focus:border-cyan-500"
        />
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="text-xs h-7 font-mono"
          onClick={onGenerateScaffold}
          disabled={isScaffolding}
        >
          <Wand2Icon className="size-3.5 mr-1 text-cyan-400" />
          重新生成脚手架
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="text-xs h-7 font-mono"
          onClick={onValidate}
          disabled={isValidating}
        >
          <FileCheckIcon className="size-3.5 mr-1 text-cyan-400" />
          检查规范
        </Button>
      </div>

      <textarea
        value={draftContent}
        onChange={(e) => setDraftContent(e.target.value)}
        rows={16}
        className="w-full p-2.5 text-xs font-mono bg-background border border-border rounded text-foreground focus:outline-none focus:border-cyan-500 leading-relaxed resize-y"
        placeholder="编写符合 Agent Skills 规范的 SKILL.md 内容..."
      />
    </Card>
  )
}
