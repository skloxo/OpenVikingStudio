import { describe, expect, it } from 'vitest'
import {
  initialSchemaArguments,
  prepareSchemaArguments,
  validateSchemaArguments,
} from './schema'
import type { JsonSchema } from './model'

describe('arranger json schema helpers', () => {
  const schema: JsonSchema = {
    type: 'object',
    required: ['repo'],
    properties: {
      repo: { type: 'string' },
      limit: { anyOf: [{ type: 'integer', default: 10 }, { type: 'null' }] },
      labels: { type: 'array', items: { type: 'string' } },
    },
  }

  it('builds initial values including nullable defaults and validates required strings', () => {
    const initial = initialSchemaArguments(schema)
    expect(initial).toEqual({ limit: 10 })
    expect(validateSchemaArguments(schema, initial)).toEqual({ repo: 'required' })

    const valid = prepareSchemaArguments(schema, {
      repo: 'OpenViking',
      limit: 20,
      labels: ['ui'],
    })
    expect(valid).toEqual({ repo: 'OpenViking', limit: 20, labels: ['ui'] })
    expect(validateSchemaArguments(schema, valid)).toEqual({})
  })
})
