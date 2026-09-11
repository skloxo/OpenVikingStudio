import { describe, expect, it } from 'vitest'

import {
  hasTaskResult,
  normalizeTaskRecord,
  normalizeTasks,
  parseInitiator,
} from './task-record'

describe('task record helpers', () => {
  it('normalizes task records from API payloads', () => {
    expect(
      normalizeTaskRecord({
        stage: 'processing_queue',
        status: 'running',
        task_id: 'task-1',
      }),
    ).toMatchObject({
      stage: 'processing_queue',
      status: 'running',
      task_id: 'task-1',
    })
  })

  it('drops invalid list entries', () => {
    expect(normalizeTasks([null, 'invalid', { task_id: 'task-1' }])).toEqual([
      { task_id: 'task-1' },
    ])
  })

  it('only reports meaningful results', () => {
    expect(hasTaskResult(undefined)).toBe(false)
    expect(hasTaskResult({})).toBe(false)
    expect(hasTaskResult([])).toBe(false)
    expect(hasTaskResult({ archive_uri: 'viking://archive' })).toBe(true)
  })

  it('correctly parses initiator and handles valet_parking tenant fallback', () => {
    // Valet parking with default namespace should map to [2080TI] Antigravity Agent
    expect(parseInitiator('default', 'valet_parking')).toEqual({
      isAgent: true,
      isUser: false,
      name: '[2080TI] Antigravity',
      raw: 'default',
    })

    // Valet parking without initiator should also map to [2080TI] Antigravity Agent
    expect(parseInitiator(undefined, 'valet_parking')).toEqual({
      isAgent: true,
      isUser: false,
      name: '[2080TI] Antigravity',
      raw: '',
    })

    // Structured client@node attribution
    expect(parseInitiator('antigravity@2080ti')).toEqual({
      isAgent: true,
      isUser: false,
      name: '[2080TI] Antigravity',
      raw: 'antigravity@2080ti',
    })

    expect(parseInitiator('workbuddy@3070')).toEqual({
      isAgent: true,
      isUser: false,
      name: '[3070] WorkBuddy',
      raw: 'workbuddy@3070',
    })

    expect(parseInitiator('mimocode@3070')).toEqual({
      isAgent: true,
      isUser: false,
      name: '[3070] MimoCode',
      raw: 'mimocode@3070',
    })

    expect(parseInitiator('openclaw.researcher@2080ti')).toEqual({
      isAgent: true,
      isUser: false,
      name: '[2080TI] OpenClaw (Researcher)',
      raw: 'openclaw.researcher@2080ti',
    })

    // Explicit agent with model name
    expect(parseInitiator('Agent (Gemini Flash)')).toEqual({
      isAgent: true,
      isUser: false,
      name: 'Gemini Flash',
      raw: 'Agent (Gemini Flash)',
    })

    // Explicit user
    expect(parseInitiator('User (admin)')).toEqual({
      isAgent: false,
      isUser: true,
      name: 'admin',
      raw: 'User (admin)',
    })

    // Other task with default user
    expect(parseInitiator('default', 'sync')).toEqual({
      isAgent: false,
      isUser: true,
      name: 'default',
      raw: 'default',
    })
  })
})
