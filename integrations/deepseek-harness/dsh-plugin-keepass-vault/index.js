/**
 * KeePass Vault Cordis RPC Bridge & Native CLI Plugin for DeepSeek Harness (DSH).
 * Pure Node.js ESM - Compliant with official DSH Schemastery & Cordis specs.
 *
 * First Principles:
 * 1. Zero Backend Dependency: Operates completely on agent's local environment.
 * 2. Credential SSOT: All keys, passwords, and tokens retrieved from local .kdbx vault.
 * 3. Law of Query-First: Never ask human users for plain secrets.
 * 4. Zero-Crash Output: output.render strictly returns array of ContentBlock objects.
 * 5. Complete 9-Tool Set: Status, Search, Get, Add, Edit, Rm, Tree, Analyze, Export.
 */

import { spawnSync } from 'node:child_process'
import { existsSync, statSync, copyFileSync, readdirSync, unlinkSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { createServer } from 'node:http'
import { resolve, dirname, basename } from 'node:path'
import { homedir } from 'node:os'
import Schema from './schema.js'

export const name = 'dsh-plugin-keepass-vault'
export const inject = ['agents', 'tools', 'systemPrompt']

const PKG_NAME = 'dsh-plugin-keepass-vault'
const SHORT_NAME = 'keepass-vault'

function v(s) {
  return typeof s?.volatile === 'function' ? s.volatile() : s
}

export const Config = Schema ? Schema.object({
  kdbxPath: v(Schema.string().default('~/Desktop/Key.kdbx')).description('KeePass .kdbx 数据库文件路径'),
  passwordEnv: v(Schema.string().default('KEEPASS_VAULT_PASSWORD')).description('从系统环境变量中引用的密码变量名'),
  masterKey: v(Schema.string().role('secret').default('')).description('主密码 (可选)'),
  autoSnapshot: v(Schema.boolean().default(true)).description('写入前自动执行 .bak 物理快照备份')
}).description('KeePass 本地密码保险库凭据插件') : undefined

if (Config && !Config['~standard']) {
  Config['~standard'] = {
    version: 1,
    vendor: 'schemastery-fallback',
    validate: (val) => ({ value: val })
  }
}

function getDshDir() {
  const home = process.env.USERPROFILE || process.env.HOME || homedir()
  return resolve(home, '.dsh')
}

function getUiConfigStorePath() {
  return resolve(getDshDir(), 'openviking-plugins-config.json')
}

function readUiSavedConfig() {
  try {
    const p = getUiConfigStorePath()
    if (existsSync(p)) {
      const all = JSON.parse(readFileSync(p, 'utf8'))
      return all[PKG_NAME] || all[SHORT_NAME] || {}
    }
  } catch (_) {}
  try {
    const localCfg = resolve(process.env.USERPROFILE || homedir(), '.gemini/config/plugins/keepass-vault/config.json')
    if (existsSync(localCfg)) {
      const c = JSON.parse(readFileSync(localCfg, 'utf8'))
      return {
        kdbxPath: c.kdbx_path || c.db_path || '',
        masterKey: c.master_key || c.key || ''
      }
    }
  } catch (_) {}
  return {}
}

function getVal(v, fallback = '') {
  if (v === undefined || v === null) return fallback
  if (typeof v?.get === 'function') {
    const val = v.get()
    return (val !== undefined && val !== null && val !== '') ? String(val).trim() : fallback
  }
  return String(v).trim() || fallback
}

function resolvePath(p) {
  if (!p) return ''
  if (p.startsWith('~')) {
    const home = process.env.USERPROFILE || process.env.HOME || homedir()
    return resolve(home, p.slice(2))
  }
  return resolve(p)
}

function runKeePassCli(args, masterKey, timeout = 10000) {
  try {
    const input = (masterKey ? `${masterKey}\n` : '\n')
    const res = spawnSync('keepassxc-cli', args, {
      input,
      encoding: 'utf8',
      timeout,
      env: { ...process.env, QT_QPA_PLATFORM: 'offscreen' }
    })
    return {
      success: res.status === 0,
      stdout: (res.stdout || '').trim(),
      stderr: (res.stderr || '').trim(),
      code: res.status
    }
  } catch (err) {
    return { success: false, stdout: '', stderr: String(err?.message || err), code: -1 }
  }
}

function makeSnapshot(dbPath, maxBackups = 10) {
  if (!existsSync(dbPath)) return null
  try {
    const d = new Date()
    const pad = n => String(n).padStart(2, '0')
    const stamp = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
    const bak = `${dbPath}.${stamp}.bak`
    copyFileSync(dbPath, bak)
    const dir = dirname(dbPath)
    const base = basename(dbPath)
    const all = readdirSync(dir)
      .filter(f => f.startsWith(base) && f.endsWith('.bak'))
      .sort()
    if (all.length > maxBackups) {
      for (const old of all.slice(0, all.length - maxBackups)) {
        try { unlinkSync(resolve(dir, old)) } catch (_) {}
      }
    }
    return bak
  } catch (_) {
    return null
  }
}

function ensureKpvProbeBridge() {
  if (globalThis.__kpv_dsh_probe_server__) return

  try {
    const srv = createServer((req, res) => {
      res.setHeader('Access-Control-Allow-Origin', '*')
      res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type')

      if (req.method === 'OPTIONS') {
        res.writeHead(204)
        res.end()
        return
      }

      if (req.method === 'POST' && (req.url === '/kpv-probe' || req.url === '/kpv-test')) {
        let body = ''
        req.on('data', chunk => { body += chunk })
        req.on('end', () => {
          try {
            const payload = JSON.parse(body || '{}')
            const rawPath = (payload.kdbxPath || '').trim()
            const key = payload.masterKey || ''

            if (!rawPath) {
              res.writeHead(200, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({ ok: false, error: '未指定数据库路径，请填写 .kdbx 完整绝对路径' }))
              return
            }

            const db = resolvePath(rawPath)
            if (!existsSync(db)) {
              res.writeHead(200, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({ ok: false, exists: false, error: `数据库文件不存在: [${db}]。请核对本地路径。` }))
              return
            }

            const fileStat = statSync(db)
            const sizeKb = Math.round(fileStat.size / 1024)

            if (!key) {
              res.writeHead(200, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({
                ok: false,
                exists: true,
                unlocked: false,
                error: `文件存在 (${sizeKb} KB)，但未提供解锁主密码。请输入主密码执行解锁体检。`
              }))
              return
            }

            const unlockRes = runKeePassCli(['ls', '-q', db], key)
            if (unlockRes.success) {
              const lines = unlockRes.stdout.split('\n').map(l => l.trim()).filter(Boolean)
              res.writeHead(200, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({
                ok: true,
                exists: true,
                unlocked: true,
                entry_count: lines.length,
                size_kb: sizeKb,
                msg: `物理文件真实存在 (${sizeKb} KB) · 主密码解锁成功！共检索到 ${lines.length} 个根条目/分组。`
              }))
            } else {
              res.writeHead(200, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({
                ok: false,
                exists: true,
                unlocked: false,
                error: `文件存在 (${sizeKb} KB)，但解锁失败: 主密码错误或数据库损坏 (${unlockRes.stderr || 'Invalid credentials'})`
              }))
            }
          } catch (e) {
            res.writeHead(500, { 'Content-Type': 'application/json' })
            res.end(JSON.stringify({ ok: false, error: String(e) }))
          }
        })
        return
      }

      if (req.method === 'POST' && req.url === '/kpv-save') {
        let body = ''
        req.on('data', chunk => { body += chunk })
        req.on('end', () => {
          try {
            const payload = JSON.parse(body || '{}')
            const storePath = getUiConfigStorePath()
            mkdirSync(dirname(storePath), { recursive: true })
            let existing = {}
            if (existsSync(storePath)) {
              try { existing = JSON.parse(readFileSync(storePath, 'utf8')) } catch (_) {}
            }
            existing[PKG_NAME] = payload
            existing[SHORT_NAME] = payload
            writeFileSync(storePath, JSON.stringify(existing, null, 2), 'utf8')
            res.writeHead(200, { 'Content-Type': 'application/json' })
            res.end(JSON.stringify({ ok: true }))
          } catch (e) {
            res.writeHead(500, { 'Content-Type': 'application/json' })
            res.end(JSON.stringify({ ok: false, error: String(e) }))
          }
        })
        return
      }

      res.writeHead(404)
      res.end()
    })

    srv.on('error', () => {})
    srv.listen(19341, '127.0.0.1', () => {
      try { srv.unref() } catch (_) {}
    })
    globalThis.__kpv_dsh_probe_server__ = srv
  } catch (_) {}
}

const OUT_SPEC = {
  schema: { type: 'string' },
  render: (_args, value) => [{
    type: 'text',
    text: typeof value === 'string' ? value : JSON.stringify(value ?? '', null, 2)
  }]
}

export function apply(ctx, config = {}) {
  ensureKpvProbeBridge()

  const getKdbxPath = () => {
    const ui = readUiSavedConfig()
    const raw = getVal(config.kdbxPath, '') || ui.kdbxPath || ui.db_path || ''
    if (raw) return resolvePath(raw)
    const desk = resolve(process.env.USERPROFILE || homedir(), 'Desktop', 'Key.kdbx')
    if (existsSync(desk)) return desk
    return resolvePath('~/.openviking/vault.kdbx')
  }

  const getMasterPassword = () => {
    const ui = readUiSavedConfig()
    const direct = getVal(config.masterKey, '') || (ui.masterKey || '').trim()
    if (direct) return direct
    const envName = getVal(config.passwordEnv, 'KEEPASS_VAULT_PASSWORD')
    if (envName && process.env[envName]) return process.env[envName]
    if (process.env.KPXC_KEY) return process.env.KPXC_KEY
    if (process.env.KPXC_MASTER_KEY) return process.env.KPXC_MASTER_KEY
    if (process.env.KEEPASS_PASSWORD) return process.env.KEEPASS_PASSWORD
    return ''
  }

  if (ctx.systemPrompt) {
    try {
      ctx.systemPrompt.context({
        name: 'keepass-vault-credential-guide',
        order: 15,
        text: () => [
          '【KeePass 凭据保险箱认知导轨 (Credential SSOT)】',
          '1. 查库第一公理：凡遇 API Key、SSH 密码/私钥、数据库连接串，强制先调用 keepass_search / keepass_get 查询凭据库，严禁向人类索要明文密码。',
          '2. 批量建号落盘：新建账户或获取凭据后，必须调用 keepass_add 自动生成 >=20 位高熵密码并安全落盘归档。',
          '3. 灾备物理快照：写操作底层具备 *.bak 自动物理快照容灾。',
          `当前本地保险箱路径: ${getKdbxPath()}。`
        ].join('\n')
      })
    } catch (_) {}
  }

  if (ctx.tools && typeof ctx.tools.register === 'function') {
    const toStandardJsonSchema = (params) => {
      if (!params || typeof params !== 'object') return { type: 'object', properties: {} }
      if (params.type === 'object' && params.properties) return params
      const properties = {}
      const required = []
      for (const [k, v] of Object.entries(params)) {
        properties[k] = { ...v }
        if (v.required) {
          required.push(k)
          delete properties[k].required
        }
      }
      return {
        type: 'object',
        properties,
        ...(required.length > 0 ? { required } : {})
      }
    }

    const wrapTool = (def, defineToolFn) => {
      const presentCall = args => ({
        card: 'generic',
        kind: def.name.includes('search') || def.name.includes('get') ? 'read' : 'other',
        title: def.description || def.name,
        rawInput: args
      })

      if (typeof defineToolFn === 'function') {
        return defineToolFn({
          ...def,
          output: OUT_SPEC,
          presentCall
        })
      }

      return {
        ...def,
        parameters: toStandardJsonSchema(def.parameters),
        output: OUT_SPEC,
        presentCall
      }
    }

    const registerAll = (defineToolFn) => {
      try {
        // 1. keepass_status
        ctx.tools.register(wrapTool({
          name: 'keepass_status',
          description: '检查本地 KeePass 保险箱文件存在性、大小、就绪状态及总条目数。',
          parameters: {},
          async execute() {
            const db = getKdbxPath()
            const exists = existsSync(db)
            const size = exists ? statSync(db).size : 0
            const key = getMasterPassword()
            let unlocked = false
            let totalEntries = 0
            let errDetail = ''
            if (exists && key) {
              const check = runKeePassCli(['ls', '-q', db], key)
              unlocked = check.success
              if (unlocked) {
                totalEntries = check.stdout.split('\n').filter(Boolean).length
              } else {
                errDetail = check.stderr
              }
            }
            return JSON.stringify({
              db_path: db,
              exists,
              size_bytes: size,
              unlocked,
              auth_ready: Boolean(key),
              total_root_entries: totalEntries,
              error: errDetail || undefined
            }, null, 2)
          }
        }, defineToolFn))

        // 2. keepass_search
        ctx.tools.register(wrapTool({
          name: 'keepass_search',
          description: '按服务名、域名或账号关键词全局模糊搜索 KeePass 凭据库条目路径。',
          parameters: {
            query: { type: 'string', required: true, description: '搜索关键词，如 aliyun, deepseek, 3070 等' }
          },
          async execute(args) {
            const db = getKdbxPath()
            const key = getMasterPassword()
            if (!existsSync(db)) return `[KeePass Error]: 本地数据库文件不存在: ${db}`
            const res = runKeePassCli(['search', '-q', db, args.query], key)
            if (!res.success) return `[KeePass Error]: 搜索失败: ${res.stderr || '未找到匹配条目'}`
            const lines = res.stdout.split('\n').map(s => s.trim()).filter(Boolean)
            return JSON.stringify({ query: args.query, count: lines.length, matches: lines }, null, 2)
          }
        }, defineToolFn))

        // 3. keepass_get
        ctx.tools.register(wrapTool({
          name: 'keepass_get',
          description: '读取 KeePass 指定条目的详细信息。show_protected=true 时明文返回密码。',
          parameters: {
            entry_path: { type: 'string', required: true, description: '条目完整路径，如 /云服务/阿里云' },
            show_protected: { type: 'boolean', required: false, description: '是否明文读取敏感字段 (默认 false)' }
          },
          async execute(args) {
            const db = getKdbxPath()
            const key = getMasterPassword()
            if (!existsSync(db)) return `[KeePass Error]: 本地数据库文件不存在: ${db}`
            const cmd = ['show', db, args.entry_path]
            if (args.show_protected) cmd.push('-s')
            const res = runKeePassCli(cmd, key)
            if (!res.success) return `[KeePass Error]: 读取失败: ${res.stderr || '条目不存在'}`
            const attrs = {}
            for (const line of res.stdout.split('\n')) {
              const idx = line.indexOf(':')
              if (idx > 0) attrs[line.slice(0, idx).trim()] = line.slice(idx + 1).trim()
            }
            return JSON.stringify({ entry: args.entry_path, attributes: attrs }, null, 2)
          }
        }, defineToolFn))

        // 4. keepass_add
        ctx.tools.register(wrapTool({
          name: 'keepass_add',
          description: '向数据库新增凭据条目。写入前自动创建安全快照 (*.bak)。',
          parameters: {
            entry_path: { type: 'string', required: true, description: '新条目完整路径，如 /生产环境/DB' },
            username: { type: 'string', required: false, description: '用户名/账号' },
            password: { type: 'string', required: false, description: '指定密码 (留空则自动生成 >=20 位高熵密码)' },
            url: { type: 'string', required: false, description: '关联 URL' },
            notes: { type: 'string', required: false, description: '备注信息' }
          },
          async execute(args) {
            const db = getKdbxPath()
            const key = getMasterPassword()
            if (!existsSync(db)) return `[KeePass Error]: 数据库文件不存在: ${db}`
            const bak = makeSnapshot(db)
            const cmd = ['add', '-q', db, args.entry_path]
            if (args.username) cmd.push('-u', args.username)
            if (args.url) cmd.push('--url', args.url)
            if (args.password) {
              cmd.push('-p')
            } else {
              cmd.push('-g', '-L', '20')
            }
            const stdinInput = (key ? `${key}\n` : '\n') + (args.password ? `${args.password}\n` : '')
            try {
              const proc = spawnSync('keepassxc-cli', cmd, { input: stdinInput, encoding: 'utf8', timeout: 15000 })
              if (proc.status !== 0) return `[KeePass Error]: 添加失败: ${proc.stderr}`
              return JSON.stringify({ status: 'success', entry: args.entry_path, backup: bak }, null, 2)
            } catch (e) {
              return `[KeePass Error]: 执行异常: ${e.message}`
            }
          }
        }, defineToolFn))

        // 5. keepass_edit
        ctx.tools.register(wrapTool({
          name: 'keepass_edit',
          description: '修改已有凭据条目。修改前自动物理快照。',
          parameters: {
            entry_path: { type: 'string', required: true, description: '条目完整路径' },
            username: { type: 'string', required: false, description: '新用户名' },
            password: { type: 'string', required: false, description: '新密码' },
            url: { type: 'string', required: false, description: '新 URL' },
            notes: { type: 'string', required: false, description: '新备注' }
          },
          async execute(args) {
            const db = getKdbxPath()
            const key = getMasterPassword()
            if (!existsSync(db)) return `[KeePass Error]: 数据库文件不存在: ${db}`
            const bak = makeSnapshot(db)
            const cmd = ['edit', '-q', db, args.entry_path]
            if (args.username) cmd.push('-u', args.username)
            if (args.url) cmd.push('--url', args.url)
            if (args.notes) cmd.push('--notes', args.notes)
            if (args.password) cmd.push('-p')
            const stdinInput = (key ? `${key}\n` : '\n') + (args.password ? `${args.password}\n` : '')
            try {
              const proc = spawnSync('keepassxc-cli', cmd, { input: stdinInput, encoding: 'utf8', timeout: 15000 })
              if (proc.status !== 0) return `[KeePass Error]: 编辑失败: ${proc.stderr}`
              return JSON.stringify({ status: 'success', entry: args.entry_path, backup: bak }, null, 2)
            } catch (e) {
              return `[KeePass Error]: 执行异常: ${e.message}`
            }
          }
        }, defineToolFn))

        // 6. keepass_rm
        ctx.tools.register(wrapTool({
          name: 'keepass_rm',
          description: '安全删除指定条目或分组。删除前强制物理快照备份。',
          parameters: {
            entry_path: { type: 'string', required: true, description: '要删除的条目或组路径' }
          },
          async execute(args) {
            const db = getKdbxPath()
            const key = getMasterPassword()
            if (!existsSync(db)) return `[KeePass Error]: 数据库文件不存在: ${db}`
            const bak = makeSnapshot(db)
            const res = runKeePassCli(['rm', '-q', db, args.entry_path], key)
            if (!res.success) return `[KeePass Error]: 删除失败: ${res.stderr}`
            return JSON.stringify({ status: 'deleted', entry: args.entry_path, backup: bak }, null, 2)
          }
        }, defineToolFn))

        // 7. keepass_list_tree
        ctx.tools.register(wrapTool({
          name: 'keepass_list_tree',
          description: '树状遍历列出指定分组下的子分组与条目。',
          parameters: {
            group: { type: 'string', required: false, description: '起始组路径 (默认 "/")' },
            recursive: { type: 'boolean', required: false, description: '是否递归列出 (默认 true)' }
          },
          async execute(args) {
            const db = getKdbxPath()
            const key = getMasterPassword()
            if (!existsSync(db)) return `[KeePass Error]: 数据库文件不存在: ${db}`
            const cmd = ['ls', '-q']
            if (args.recursive !== false) cmd.push('-R')
            cmd.push(db, args.group || '/')
            const res = runKeePassCli(cmd, key)
            if (!res.success) return `[KeePass Error]: 列出失败: ${res.stderr}`
            const lines = res.stdout.split('\n').map(s => s.trim()).filter(Boolean)
            return JSON.stringify({ group: args.group || '/', count: lines.length, items: lines }, null, 2)
          }
        }, defineToolFn))

        // 8. keepass_analyze
        ctx.tools.register(wrapTool({
          name: 'keepass_analyze',
          description: '数据库健康安全体检：检测弱密码、重复密码及泄露风险。',
          parameters: {},
          async execute() {
            const db = getKdbxPath()
            const key = getMasterPassword()
            if (!existsSync(db)) return `[KeePass Error]: 数据库文件不存在: ${db}`
            const res = runKeePassCli(['analyze', '-q', db], key)
            if (!res.success) return `[KeePass Error]: 分析失败: ${res.stderr}`
            return JSON.stringify({ status: 'ok', report: res.stdout }, null, 2)
          }
        }, defineToolFn))

        // 9. keepass_export_attachment
        ctx.tools.register(wrapTool({
          name: 'keepass_export_attachment',
          description: '导出条目中的附件（如 SSH 私钥文件、证书）到指定本地目录。',
          parameters: {
            entry_path: { type: 'string', required: true, description: '条目完整路径' },
            attachment_name: { type: 'string', required: true, description: '附件文件名' },
            output_dir: { type: 'string', required: true, description: '目标保存目录' }
          },
          async execute(args) {
            const db = getKdbxPath()
            const key = getMasterPassword()
            if (!existsSync(db)) return `[KeePass Error]: 数据库文件不存在: ${db}`
            const targetDir = resolvePath(args.output_dir)
            mkdirSync(targetDir, { recursive: true })
            const targetFile = resolve(targetDir, args.attachment_name)
            const res = runKeePassCli(['attachment-export', db, args.entry_path, args.attachment_name, targetFile], key)
            if (!res.success) return `[KeePass Error]: 导出失败: ${res.stderr}`
            return JSON.stringify({ status: 'exported', entry: args.entry_path, file_path: targetFile }, null, 2)
          }
        }, defineToolFn))

        // 10. keepass_selfcheck
        ctx.tools.register(wrapTool({
          name: 'keepass_selfcheck',
          description: '执行 KeePass 凭据库全生命周期 CRUD 沙箱打靶安全自检（真实测试 status/add/get/edit/rm 能力，自动清理零残留，绝不读取任何生产凭据）。',
          parameters: {
            cleanup: { type: 'boolean', required: false, description: '测试完成后是否自动清理沙箱条目（默认为 true）' }
          },
          async execute(args) {
            const db = getKdbxPath()
            const key = getMasterPassword()
            if (!existsSync(db)) {
              return JSON.stringify({
                all_passed: false,
                error: `数据库文件不存在: ${db}`
              }, null, 2)
            }

            const shouldCleanup = args?.cleanup !== false
            const probeId = 'probe_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 6)
            const testPath = `/_selfcheck_sandbox/${probeId}`
            const testUser = `probe_user_${probeId}`
            const testPass = `ProbePass_${Date.now()}!#x9`
            const updatedPass = `UpdatedPass_${Date.now()}!#z8`

            const report = {
              timestamp: new Date().toISOString(),
              total_tools: 10,
              database: 'unknown',
              crud_stages: {
                status: 'pending',
                add: 'pending',
                get_decrypt: 'pending',
                edit: 'pending',
                rm_cleanup: 'pending'
              },
              all_passed: false
            }

            try {
              // 1. status 探针 (ls)
              const st = runKeePassCli(['ls', '-q', db], key)
              if (!st.success) {
                report.error = `keepass_status check failed: ${st.stderr || 'unlock failed'}`
                return JSON.stringify(report, null, 2)
              }
              report.database = 'unlocked'
              report.crud_stages.status = 'passed'

              // 2. add 探针 (写入沙箱测试条目)
              const addInput = (key ? `${key}\n` : '\n') + `${testPass}\n`
              const addProc = spawnSync('keepassxc-cli', ['add', '-q', db, testPath, '-u', testUser, '-p'], {
                input: addInput,
                encoding: 'utf8',
                timeout: 10000,
                env: { ...process.env, QT_QPA_PLATFORM: 'offscreen' }
              })
              if (addProc.status !== 0) {
                report.error = `keepass_add probe failed: ${(addProc.stderr || '').trim()}`
                return JSON.stringify(report, null, 2)
              }
              report.crud_stages.add = 'passed'

              // 3. get 探针 (真实解密读取沙箱条目并校验内容)
              const getRes = runKeePassCli(['show', '-q', '-s', '-a', 'UserName', db, testPath], key)
              const getPassRes = runKeePassCli(['show', '-q', '-s', '-a', 'Password', db, testPath], key)
              if (!getRes.success || !getPassRes.success) {
                report.error = `keepass_get decrypt failed: ${getRes.stderr || getPassRes.stderr}`
                return JSON.stringify(report, null, 2)
              }
              if (getRes.stdout !== testUser || getPassRes.stdout !== testPass) {
                report.error = `keepass_get decrypt mismatch: got user=${getRes.stdout}`
                return JSON.stringify(report, null, 2)
              }
              report.crud_stages.get_decrypt = 'passed'

              // 4. edit 探针 (更新属性)
              const editInput = (key ? `${key}\n` : '\n') + `${updatedPass}\n`
              const editProc = spawnSync('keepassxc-cli', ['edit', '-q', db, testPath, '-p'], {
                input: editInput,
                encoding: 'utf8',
                timeout: 10000,
                env: { ...process.env, QT_QPA_PLATFORM: 'offscreen' }
              })
              if (editProc.status !== 0) {
                report.error = `keepass_edit probe failed: ${(editProc.stderr || '').trim()}`
                return JSON.stringify(report, null, 2)
              }
              report.crud_stages.edit = 'passed'

              // 5. rm 探针 (物理清理沙箱测试条目)
              if (shouldCleanup) {
                const rmRes = runKeePassCli(['rm', '-q', db, testPath], key)
                if (!rmRes.success) {
                  report.error = `keepass_rm cleanup failed: ${rmRes.stderr}`
                  return JSON.stringify(report, null, 2)
                }
                report.crud_stages.rm_cleanup = 'passed'
                report.sandbox_cleaned = true
              }

              report.all_passed = true
              report.summary = 'KeePass Vault 真实能力全生命周期 CRUD 沙箱打靶 100% 通过（零生产数据泄漏，零脏数据残留）。'
              return JSON.stringify(report, null, 2)
            } catch (err) {
              report.all_passed = false
              report.error = String(err?.message || err)
              return JSON.stringify(report, null, 2)
            } finally {
              if (shouldCleanup) {
                try { runKeePassCli(['rm', '-q', db, testPath], key) } catch (_) {}
              }
            }
          }
        }, defineToolFn))
      } catch (e) {
        try {
          const logPath = resolve(getDshDir(), 'dsh-plugin-keepass-vault-error.log')
          writeFileSync(logPath, `[${new Date().toISOString()}] register tools failed: ${String(e?.message || e)}\n`, { flag: 'a', encoding: 'utf8' })
        } catch (_) {}
      }
    }

    try {
      import('@deepseek-ai/dsh-tools').then((mod) => {
        const fn = mod?.defineTool || mod?.default?.defineTool
        registerAll(fn)
      }).catch(() => {
        registerAll(null)
      })
    } catch (_) {
      registerAll(null)
    }
  }
}

apply.inject = ['systemPrompt', 'tools']
