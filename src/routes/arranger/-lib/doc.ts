import { parse as parseYaml } from 'yaml'
import type { MountInput } from './model'

export type FormattedLiveResult = {
  isError: boolean
  text: string
}

export function formatLiveContextResult(value: unknown): FormattedLiveResult {
  if (typeof value === 'string') return { isError: false, text: value }
  if (!value || typeof value !== 'object') {
    return { isError: false, text: JSON.stringify(value) }
  }

  const result = value as Record<string, unknown>
  const content = Array.isArray(result.content) ? result.content : []
  const blocks = content.flatMap((item) => {
    if (!item || typeof item !== 'object') return []
    const block = item as Record<string, unknown>
    if (block.type === 'text' && typeof block.text === 'string') {
      return [block.text]
    }
    return [JSON.stringify(block, null, 2)]
  })

  if (blocks.length) {
    return {
      isError: result.isError === true,
      text: blocks.join('\n\n'),
    }
  }

  const structured = result.structuredContent ?? result.structured_content
  return {
    isError: result.isError === true,
    text: JSON.stringify(structured ?? value, null, 2),
  }
}

export function parseLiveContextMetadata(
  content: string,
): Partial<MountInput> | null {
  const match = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(content)
  if (!match) return null
  try {
    const metadata = parseYaml(match[1]) as Record<string, unknown> | null
    if (metadata?.type !== 'OpenViking Live Context') return null
    const extension =
      metadata['x-openviking'] && typeof metadata['x-openviking'] === 'object'
        ? (metadata['x-openviking'] as Record<string, unknown>)
        : {}
    return {
      arguments:
        extension.args && typeof extension.args === 'object'
          ? (extension.args as Record<string, unknown>)
          : {},
      description:
        typeof metadata.description === 'string'
          ? metadata.description
          : undefined,
      timeout_seconds:
        typeof extension.timeout_seconds === 'number'
          ? extension.timeout_seconds
          : 60,
      title: typeof metadata.title === 'string' ? metadata.title : undefined,
      tool_uri:
        typeof extension.definition === 'string'
          ? extension.definition
          : undefined,
    }
  } catch {
    return {}
  }
}

export function isLiveContextDocument(content: string): boolean {
  return parseLiveContextMetadata(content) !== null
}

// Compact pure-JS SHA-256 fallback so hashing works even on non-HTTPS LAN URLs where crypto.subtle is unavailable.
const K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
  0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
  0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
  0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
  0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
  0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
])

function rotr(value: number, bits: number): number {
  return (value >>> bits) | (value << (32 - bits))
}

export function sha256HexSync(data: Uint8Array): string {
  const bitLen = data.length * 8
  const paddedLen = Math.ceil((data.length + 9) / 64) * 64
  const buf = new Uint8Array(paddedLen)
  buf.set(data)
  buf[data.length] = 0x80
  const view = new DataView(buf.buffer)
  view.setUint32(paddedLen - 8, Math.floor(bitLen / 0x100000000), false)
  view.setUint32(paddedLen - 4, bitLen >>> 0, false)

  const hash = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ])
  const w = new Uint32Array(64)

  for (let i = 0; i < paddedLen; i += 64) {
    for (let t = 0; t < 16; t += 1) w[t] = view.getUint32(i + t * 4, false)
    for (let t = 16; t < 64; t += 1) {
      const s0 = rotr(w[t - 15], 7) ^ rotr(w[t - 15], 18) ^ (w[t - 15] >>> 3)
      const s1 = rotr(w[t - 2], 17) ^ rotr(w[t - 2], 19) ^ (w[t - 2] >>> 10)
      w[t] = (w[t - 16] + s0 + w[t - 7] + s1) >>> 0
    }
    let [a, b, c, d, e, f, g, h] = hash
    for (let t = 0; t < 64; t += 1) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
      const ch = (e & f) ^ (~e & g)
      const temp1 = (h + S1 + ch + K[t] + w[t]) >>> 0
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
      const maj = (a & b) ^ (a & c) ^ (b & c)
      const temp2 = (S0 + maj) >>> 0
      h = g
      g = f
      f = e
      e = (d + temp1) >>> 0
      d = c
      c = b
      b = a
      a = (temp1 + temp2) >>> 0
    }
    hash[0] = (hash[0] + a) >>> 0
    hash[1] = (hash[1] + b) >>> 0
    hash[2] = (hash[2] + c) >>> 0
    hash[3] = (hash[3] + d) >>> 0
    hash[4] = (hash[4] + e) >>> 0
    hash[5] = (hash[5] + f) >>> 0
    hash[6] = (hash[6] + g) >>> 0
    hash[7] = (hash[7] + h) >>> 0
  }

  return Array.from(hash, (v) => v.toString(16).padStart(8, '0')).join('')
}

export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  if (typeof globalThis.crypto?.subtle?.digest === 'function') {
    const copy = new Uint8Array(bytes)
    const digest = await globalThis.crypto.subtle.digest('SHA-256', copy.buffer)
    return Array.from(new Uint8Array(digest), (b) =>
      b.toString(16).padStart(2, '0'),
    ).join('')
  }
  return sha256HexSync(bytes)
}

export async function hashText(content: string): Promise<string> {
  return sha256Hex(new TextEncoder().encode(content))
}
