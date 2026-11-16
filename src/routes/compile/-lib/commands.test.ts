import { describe, expect, it } from 'vitest'
import {
  CompileCommandError,
  compileCommand,
  compileHistory,
  parseArgs,
  parseCompile,
  tokenize,
} from './commands'
import { locationLabel, sourceUris, targetError } from './locations'

describe('compile commands & locations', () => {
  it('parses valid compile commands and builds reproducible CLI output', () => {
    const tokens = tokenize(
      "ov /compile --from viking://resources/a,viking://resources/b --to viking://resources/out --skill viking://system/compile/example-skills/llm-wiki --instruction 'Group by theme'",
    )
    const req = parseCompile(tokens)
    expect(req.from).toEqual(['viking://resources/a', 'viking://resources/b'])
    expect(req.to).toBe('viking://resources/out')
    expect(compileCommand(req)).toContain('--from')
    expect(
      compileHistory(
        'compile --from viking://resources/a --to viking://resources/out --skill viking://system/skill --args \'{"k":1}\'',
      ).remember,
    ).toBe(false)
  })

  it('rejects shell injection and malformed args JSON', () => {
    expect(() => tokenize('compile | rm -rf')).toThrow(CompileCommandError)
    expect(() => parseArgs('["not-object"]')).toThrow(CompileCommandError)
  })

  it('validates target URIs and extracts unique sources', () => {
    expect(sourceUris('viking://resources/a/\n\nviking://resources/a')).toEqual([
      'viking://resources/a',
    ])
    expect(targetError('viking://resources/')).toBe('targetRootInvalid')
    expect(targetError('viking://system/compile')).toBe('targetRootInvalid')
    expect(targetError('viking://resources/my-wiki')).toBeNull()
    expect(locationLabel('viking://resources/my-wiki', 'viking://user/u1/resources')).toEqual({
      scope: 'sharedSpace',
      path: 'my-wiki',
    })
  })
})
