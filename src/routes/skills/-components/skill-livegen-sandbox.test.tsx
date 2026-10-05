// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SkillLiveGenSandbox } from './skill-livegen-sandbox'
import type { SimulationResult, ValidationResult } from './skill-livegen-types'

describe('SkillLiveGenSandbox (Card-89)', () => {
  afterEach(() => {
    cleanup()
  })

  const baseValidation: ValidationResult = {
    valid: true,
    name: 'safe-test-skill',
    description: 'Safe test skill description',
    tags: ['test', 'safe'],
    allowed_tools: ['calculator'],
    body_lines: 42,
    line_status: 'sweet_spot',
    errors: [],
    warnings: [],
  }

  const baseSimulationPass: SimulationResult = {
    skill_name: 'safe-test-skill',
    total_queries: 2,
    passed_queries: 2,
    pass_rate: 1.0,
    sandbox_passed: true,
    sandbox_duration_ms: 12.5,
    security_blocked_count: 0,
    security_issues: [],
    stdout: '[TRIAL_OK] Result=42',
    stderr: '',
    results: [
      {
        query: '计算 40 + 2',
        matched: true,
        confidence: 0.95,
        matched_keywords: ['计算'],
        explanation: '命中关键词',
      },
    ],
  }

  it('renders static validation gates correctly', () => {
    render(
      <SkillLiveGenSandbox
        validationData={baseValidation}
        simulationData={null}
        publishFeedback={null}
        testQueriesText="query 1"
        setTestQueriesText={vi.fn()}
        draftContent="test content"
        onRunSimulation={vi.fn()}
        onPublish={vi.fn()}
        isSimulating={false}
        isPublishing={false}
      />,
    )

    expect(screen.getByText('规范合规门禁')).toBeDefined()
    expect(screen.getByText('合规准入')).toBeDefined()
    expect(screen.getByText('safe-test-skill')).toBeDefined()
    // 未跑沙箱前，上架按钮应处于禁用状态 (数据安全防线)
    const publishBtn = screen.getByRole('button', { name: /一键上架至 Viking 记忆中枢/i })
    expect(publishBtn).toHaveProperty('disabled', true)
    expect(screen.getByText(/须先启动沙箱受限试跑并通过后方可上架/i)).toBeDefined()
  })

  it('displays real sandbox execution metrics and unlocks publish when passed', () => {
    const handlePublish = vi.fn()
    render(
      <SkillLiveGenSandbox
        validationData={baseValidation}
        simulationData={baseSimulationPass}
        publishFeedback={null}
        testQueriesText="query 1"
        setTestQueriesText={vi.fn()}
        draftContent="test content"
        onRunSimulation={vi.fn()}
        onPublish={handlePublish}
        isSimulating={false}
        isPublishing={false}
      />,
    )

    // 客观指标回显
    expect(screen.getByText('沙箱受限试跑与契约演练台')).toBeDefined()
    expect(screen.getByText('沙箱通过')).toBeDefined()
    expect(screen.getByText('12.5 ms')).toBeDefined()
    expect(screen.getByText('0 项高危')).toBeDefined()

    // 终端抽屉展示
    const terminalBtn = screen.getByRole('button', { name: /查看沙箱输出/i })
    expect(terminalBtn).toBeDefined()
    fireEvent.click(terminalBtn)
    expect(screen.getByText(/\[TRIAL_OK\] Result=42/i)).toBeDefined()

    // 沙箱通过后允许发布
    const publishBtn = screen.getByRole('button', { name: /一键上架至 Viking 记忆中枢/i })
    expect(publishBtn).toHaveProperty('disabled', false)
    fireEvent.click(publishBtn)
    expect(handlePublish).toHaveBeenCalled()
  })

  it('blocks publish when sandbox security gate intercepts dangerous code', () => {
    const dangerousSim: SimulationResult = {
      ...baseSimulationPass,
      sandbox_passed: false,
      security_blocked_count: 1,
      security_issues: ['CodeBlock#1: 安全拦截: 禁止调用高危指令 os.system()'],
      stderr: '[SECURITY GATE ABORT] 检测到高危代码注入',
    }

    render(
      <SkillLiveGenSandbox
        validationData={baseValidation}
        simulationData={dangerousSim}
        publishFeedback={null}
        testQueriesText="query 1"
        setTestQueriesText={vi.fn()}
        draftContent="test content"
        onRunSimulation={vi.fn()}
        onPublish={vi.fn()}
        isSimulating={false}
        isPublishing={false}
      />,
    )

    expect(screen.getByText('沙箱异常/阻断')).toBeDefined()
    expect(screen.getByText('1 项高危')).toBeDefined()

    const publishBtn = screen.getByRole('button', { name: /一键上架至 Viking 记忆中枢/i })
    expect(publishBtn).toHaveProperty('disabled', true)
    expect(screen.getByText(/已物理阻断上架/i)).toBeDefined()
  })
})
