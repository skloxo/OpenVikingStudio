import { describe, expect, it } from 'vitest'
import { isHeartbeatSession } from './thread-list'
import type { SessionListItem } from '@ov-server/api/v1/sessions'

describe('isHeartbeatSession anti-entropy detection', () => {
  it('correctly identifies standard interactive sessions', () => {
    const session: SessionListItem = {
      is_dir: true,
      mod_time: '2026-09-15T12:00:00Z',
      session_id: 'user_conversation_123',
      uri: 'viking://user/default/session/user_conversation_123',
      category: 'interactive',
      is_heartbeat: false,
    }
    expect(isHeartbeatSession(session, '代码重构与设计讨论')).toBe(false)
  })

  it('identifies cron_ and heartbeat_ prefixed sessions as heartbeats', () => {
    const cronSession: SessionListItem = {
      is_dir: true,
      mod_time: '2026-09-15T12:00:00Z',
      session_id: 'cron_nightly_backup_998',
      uri: 'viking://user/default/session/cron_nightly_backup_998',
    }
    expect(isHeartbeatSession(cronSession)).toBe(true)

    const hbSession: SessionListItem = {
      is_dir: true,
      mod_time: '2026-09-15T12:00:00Z',
      session_id: 'heartbeat_fleet_ping',
      uri: 'viking://user/default/session/heartbeat_fleet_ping',
    }
    expect(isHeartbeatSession(hbSession)).toBe(true)
  })

  it('identifies probe_ and memory-store- sessions as automated probes', () => {
    const probe: SessionListItem = {
      is_dir: true,
      mod_time: '2026-09-15T12:00:00Z',
      session_id: 'probe_health_check',
      uri: 'viking://user/default/session/probe_health_check',
    }
    expect(isHeartbeatSession(probe)).toBe(true)

    const memStore: SessionListItem = {
      is_dir: true,
      mod_time: '2026-09-15T12:00:00Z',
      session_id: 'memory-store-1781246459725-pizo3e',
      uri: 'viking://user/default/session/memory-store-1781246459725-pizo3e',
    }
    expect(isHeartbeatSession(memStore)).toBe(true)
  })

  it('identifies UUID sessions with OpenClaw heartbeat titles as heartbeats', () => {
    const uuidSession: SessionListItem = {
      is_dir: true,
      mod_time: '2026-09-15T12:00:00Z',
      session_id: 'b0b04c12-7553-4acd-8087-2da19e87a19f',
      uri: 'viking://user/default/session/b0b04c12-7553-4acd-8087-2da19e87a19f',
    }
    expect(isHeartbeatSession(uuidSession, '[OpenClaw heartbeat poll]')).toBe(true)
    expect(isHeartbeatSession(uuidSession, '定时巡检与心跳会话')).toBe(true)
  })

  it('respects backend category heartbeat and is_heartbeat flag', () => {
    const taggedSession: SessionListItem = {
      is_dir: true,
      mod_time: '2026-09-15T12:00:00Z',
      session_id: 'random_id_without_prefix',
      uri: 'viking://user/default/session/random_id_without_prefix',
      category: 'heartbeat',
      is_heartbeat: true,
    }
    expect(isHeartbeatSession(taggedSession)).toBe(true)
  })
})
