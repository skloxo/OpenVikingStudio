import { describe, expect, it } from 'vitest'
import {
  formatLiveContextResult,
  hashText,
  isLiveContextDocument,
  parseLiveContextMetadata,
  sha256HexSync,
} from './doc'

describe('arranger live document & sha256 helpers', () => {
  it('computes RFC 6234 SHA-256 digest deterministically', async () => {
    const syncDigest = sha256HexSync(new TextEncoder().encode('abc'))
    const asyncDigest = await hashText('abc')
    expect(syncDigest).toBe(
      'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
    )
    expect(asyncDigest).toBe(syncDigest)
  })

  it('parses OpenViking Live Context YAML frontmatter', () => {
    const doc = [
      '---',
      'type: OpenViking Live Context',
      'title: Service Status',
      'description: Production readiness',
      'x-openviking:',
      '  definition: viking://agent/tools/obs/status.json',
      '  timeout_seconds: 45',
      '  args:',
      '    env: prod',
      '---',
      '# Service Status',
    ].join('\n')

    expect(isLiveContextDocument(doc)).toBe(true)
    expect(parseLiveContextMetadata(doc)).toEqual({
      title: 'Service Status',
      description: 'Production readiness',
      timeout_seconds: 45,
      tool_uri: 'viking://agent/tools/obs/status.json',
      arguments: { env: 'prod' },
    })
    expect(isLiveContextDocument('# Regular Markdown')).toBe(false)
  })

  it('formats MCP text content blocks and structured results', () => {
    expect(
      formatLiveContextResult({
        content: [{ type: 'text', text: 'healthy' }],
        isError: false,
      }),
    ).toEqual({ isError: false, text: 'healthy' })

    expect(
      formatLiveContextResult({
        structuredContent: { ok: true },
        isError: true,
      }),
    ).toEqual({
      isError: true,
      text: '{\n  "ok": true\n}',
    })
  })
})
