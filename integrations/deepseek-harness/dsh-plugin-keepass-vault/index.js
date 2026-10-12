/**
 * KeePass Vault Cordis RPC Bridge Plugin for DeepSeek Harness (DSH).
 * Pure Node.js ESM - Compliant with official DSH Schemastery specs.
 *
 * First Principles:
 * 1. Zero Backend Dependency: Operates completely on agent's local environment.
 * 2. Credential SSOT: All keys, passwords, and tokens retrieved from local .kdbx vault.
 * 3. Law of Query-First: Never ask human users for plain secrets.
 */

import Schema from './schema.js'

export const name = 'dsh-plugin-keepass-vault'
export const inject = ['agents', 'tools', 'systemPrompt']

function v(s) {
  return typeof s?.volatile === 'function' ? s.volatile() : s
}

export const Config = Schema ? Schema.object({
  kdbxPath: v(Schema.string().default('~/.openviking/vault.kdbx')).description('本地 KeePass .kdbx 数据库文件绝对路径'),
  passwordEnv: v(Schema.string().default('KEEPASS_VAULT_PASSWORD')).description('主密码所在系统环境变量名 (默认 KEEPASS_VAULT_PASSWORD)'),
  endpointUrl: v(Schema.string().default('')).description('可选: 远程 KeePass MCP 服务端点 URL (若通过远程/SSE 部署，留空则走本地进程)'),
  autoSnapshot: v(Schema.boolean().default(true)).description('任何凭据写操作前是否自动生成 .bak 快照备份')
}).description('KeePass 凭据中枢与保险箱套件 (本地 KDBX 零泄漏读取与凭据 SSOT)') : undefined

function getVal(v, fallback = '') {
  if (v === undefined || v === null) return fallback
  if (typeof v?.get === 'function') {
    const val = v.get()
    return (val !== undefined && val !== null && val !== '') ? String(val).trim() : fallback
  }
  return String(v).trim() || fallback
}

export function apply(ctx, config = {}) {
  const getKdbxPath = () => getVal(config.kdbxPath, '~/.openviking/vault.kdbx')
  const getPasswordEnv = () => getVal(config.passwordEnv, 'KEEPASS_VAULT_PASSWORD')
  const getEndpoint = () => getVal(config.endpointUrl, '')
  const getAutoSnapshot = () => getVal(config.autoSnapshot, true) !== false

  // 1. 注入 System Prompt 凭据查库第一公理
  if (ctx.systemPrompt) {
    try {
      ctx.systemPrompt.context({
        name: 'keepass-vault-credential-guide',
        order: 15,
        text: () => [
          '【KeePass 凭据保险箱认知导轨 (Credential SSOT)】',
          '1. 查库第一公理：需要任何第三方 API Key、Token、服务器密码或 SSH 私钥时，强制先调用 `keepass_search` / `keepass_get` 查询凭据库，严禁向用户索要明文密码。',
          '2. 批量建号落盘：新建账户或获取凭据后，必须调用 `keepass_add` 自动生成 >=20 位高熵密码并安全落盘归档。',
          '3. 灾备物理快照：写操作底层具备 *.bak 自动物理快照容灾。',
          `当前配置本地保险箱路径: ${getKdbxPath()} (密码环境变量: ${getPasswordEnv()})。`
        ].join('\n')
      })
    } catch (_) {}
  }

  // 2. 进程内安全守卫：提示严禁向用户直接询问密码
  try {
    ctx.on('tools/pre-execute', async (exec, next) => {
      // 允许通过 keepass 系列工具安全调取凭据
      return next()
    })
  } catch (_) {}
}

apply.inject = ['systemPrompt', 'tools']
