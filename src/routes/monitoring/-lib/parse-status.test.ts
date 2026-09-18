import { describe, expect, it } from 'vitest'

import { parseObserverStatus } from './parse-status'

describe('parseObserverStatus', () => {
  it('converts an ASCII table into structured rows', () => {
    expect(
      parseObserverStatus(`
+-------+---------+
| Queue | Pending |
+-------+---------+
| Embed | 2       |
+-------+---------+
`),
    ).toEqual([
      {
        headers: ['Queue', 'Pending'],
        kind: 'table',
        rows: [['Embed', '2']],
      },
    ])
  })

  it('keeps plain status messages as text', () => {
    expect(parseObserverStatus('No active locks.')).toEqual([
      {
        kind: 'text',
        value: 'No active locks.',
      },
    ])
  })

  it('separates consecutive tables and ignores ASCII divider lines', () => {
    const raw = `
Mount: /local (plugin: localfs)
============================================================
+-----------+-------+
| Operation | Count |
+-----------+-------+
| mkdir     | 4     |
+-----------+-------+
+------------------+-------+
| Metric           | Value |
+------------------+-------+
| Total Operations | 4603  |
+------------------+-------+
`
    expect(parseObserverStatus(raw)).toEqual([
      {
        kind: 'text',
        value: 'Mount: /local (plugin: localfs)',
      },
      {
        kind: 'table',
        headers: ['Operation', 'Count'],
        rows: [['mkdir', '4']],
      },
      {
        kind: 'table',
        headers: ['Metric', 'Value'],
        rows: [['Total Operations', '4603']],
      },
    ])
  })
})
