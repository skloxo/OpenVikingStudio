export type ObserverStatusBlock =
  | {
      kind: 'table'
      headers: string[]
      rows: string[][]
    }
  | {
      kind: 'text'
      value: string
    }

function parseRow(line: string): string[] {
  return line
    .slice(1, -1)
    .split('|')
    .map((cell) => cell.trim())
}

export function parseObserverStatus(status: string): ObserverStatusBlock[] {
  const lines = status
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  const blocks: ObserverStatusBlock[] = []

  for (let index = 0; index < lines.length; ) {
    const line = lines[index]

    // Filter out ASCII divider lines like "==========" or "----------"
    if (/^[=\-_*#]{4,}$/.test(line)) {
      index += 1
      continue
    }

    if (line.startsWith('+') && lines[index + 1]?.startsWith('|')) {
      const rows: string[][] = []
      index += 1

      while (index < lines.length) {
        const curLine = lines[index]
        if (curLine.startsWith('|')) {
          rows.push(parseRow(curLine))
          index += 1
        } else if (curLine.startsWith('+')) {
          index += 1
          // If the next line does not start with '|', this table has ended.
          if (!lines[index]?.startsWith('|')) {
            break
          }
        } else {
          break
        }
      }

      if (rows.length > 0) {
        blocks.push({
          headers: rows[0],
          kind: 'table',
          rows: rows.slice(1),
        })
      }
      continue
    }

    blocks.push({
      kind: 'text',
      value: line,
    })
    index += 1
  }

  return blocks
}
