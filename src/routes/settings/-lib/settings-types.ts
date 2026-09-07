export type SettingsTab = 'general' | 'privacy' | 'dataOps'

export interface ParsedModelItem {
  model: string
  provider: string
  calls: string
  totalTokens: string
  lastUpdated: string
}

export interface ParsedObserverModels {
  vlm: ParsedModelItem[]
  embedding: ParsedModelItem[]
  rerank: ParsedModelItem[]
  compressor: ParsedModelItem[]
}

export function applyClientRedaction(
  text: string,
  options: { maskCredentials: boolean; maskPii: boolean },
): string {
  let out = text
  if (options.maskCredentials) {
    out = out.replace(/\b(sk-[a-zA-Z0-9]{4})[a-zA-Z0-9]{12,}([a-zA-Z0-9]{4})\b/g, '$1****$2')
    out = out.replace(/\b(Bearer\s+)[a-zA-Z0-9._-]{10,}\b/g, '$1[REDACTED_TOKEN]')
    out = out.replace(/(api[_-]?key\s*[:=]\s*["']?)[a-zA-Z0-9._-]{8,}(["']?)/gi, '$1[REDACTED_KEY]$2')
  }
  if (options.maskPii) {
    out = out.replace(/\b([a-zA-Z0-9._%+-]{1,2})[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b/g, '$1***@$2')
    out = out.replace(/\b(1[3-9]\d)\d{4}(\d{4})\b/g, '$1****$2')
    out = out.replace(/\b(\d{1,3}\.)\d{1,3}\.\d{1,3}(\.\d{1,3})\b/g, '$1***.***$2')
  }
  return out
}

export function parseSectionTable(sectionText: string): ParsedModelItem[] {
  const lines = sectionText.split('\n')
  const results: ParsedModelItem[] = []
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed.startsWith('|') || !trimmed.endsWith('|')) continue
    const parts = trimmed
      .split('|')
      .map((p) => p.trim())
      .filter((p) => p.length > 0)
    if (parts.length < 5) continue
    if (
      parts[0].toLowerCase() === 'model' ||
      parts[1]?.toLowerCase() === 'provider'
    ) {
      continue
    }
    results.push({
      model: parts[0],
      provider: parts[1] || '--',
      calls: parts[2] || '0',
      totalTokens: parts[5] || parts[parts.length - 2] || '--',
      lastUpdated: parts[parts.length - 1] || '--',
    })
  }
  return results
}

export function parseObserverModelsTable(statusText?: string | null): ParsedObserverModels {
  if (!statusText) {
    return { vlm: [], embedding: [], rerank: [], compressor: [] }
  }
  const extractSection = (heading: string, nextHeadings: string[]) => {
    const startIdx = statusText.indexOf(heading)
    if (startIdx === -1) return ''
    let endIdx = statusText.length
    for (const nh of nextHeadings) {
      const idx = statusText.indexOf(nh, startIdx + heading.length)
      if (idx !== -1 && idx < endIdx) {
        endIdx = idx
      }
    }
    return statusText.slice(startIdx + heading.length, endIdx)
  }

  return {
    vlm: parseSectionTable(
      extractSection('VLM Models:', [
        'Embedding Models:',
        'Rerank Models:',
        'Compressor Models:',
      ]),
    ),
    embedding: parseSectionTable(
      extractSection('Embedding Models:', [
        'Rerank Models:',
        'Compressor Models:',
      ]),
    ),
    rerank: parseSectionTable(
      extractSection('Rerank Models:', ['Compressor Models:']),
    ),
    compressor: parseSectionTable(extractSection('Compressor Models:', [])),
  }
}
