// @vitest-environment jsdom
// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { BundleScenariosBrowser } from './bundle-scenarios-browser'

describe('BundleScenariosBrowser (Card-163)', () => {
  afterEach(() => {
    cleanup()
  })

  const sampleScenarios = [
    'git-workflow',
    'git-rebase',
    'git-commit-linter',
    'docker-compose-ops',
    'docker-build-push',
    'python-fastapi-template',
    'python-poetry-lock',
    'misc-tool-single',
  ]

  it('renders empty placeholder when scenarios list is empty', () => {
    render(<BundleScenariosBrowser scenarios={[]} bundleName="test-bundle" />)
    expect(screen.getByText('暂无专精工序场景')).toBeDefined()
  })

  it('renders dynamic clusters and instant count telemetry correctly', () => {
    const { container } = render(
      <BundleScenariosBrowser
        scenarios={sampleScenarios}
        bundleName="developer-productivity"
      />,
    )

    // 默认全部工序为 8
    expect(screen.getByText('全部工序')).toBeDefined()
    expect(screen.getByTestId('scenarios-total-count').textContent).toBe('8')
    expect(screen.getByTestId('scenarios-match-count').textContent).toBe('8')

    // 验证动态聚类生成的标签 (git: 3, docker: 2, python: 2, other: 1)
    expect(screen.getByText('git')).toBeDefined()
    expect(screen.getByText('docker')).toBeDefined()
    expect(screen.getByText('python')).toBeDefined()
    expect(screen.getByText('其他工序')).toBeDefined()

    // 验证初始渲染了全部 8 项工序 Badge
    const badges = container.querySelectorAll('[data-scenario]')
    expect(badges.length).toBe(8)
  })

  it('filters scenarios instantly on typing search query', () => {
    const { container } = render(
      <BundleScenariosBrowser
        scenarios={sampleScenarios}
        bundleName="developer-productivity"
      />,
    )

    const searchInput = screen.getByPlaceholderText(/毫秒级检索 8 项工序/)
    fireEvent.change(searchInput, { target: { value: 'docker' } })

    // 此时只应显示 docker-compose-ops 和 docker-build-push
    const docker1 = container.querySelector('[data-scenario="docker-compose-ops"]')
    const docker2 = container.querySelector('[data-scenario="docker-build-push"]')
    const gitSc = container.querySelector('[data-scenario="git-workflow"]')

    expect(docker1).not.toBeNull()
    expect(docker2).not.toBeNull()
    expect(gitSc).toBeNull()

    // 匹配计数精准为 2
    expect(screen.getByTestId('scenarios-match-count').textContent).toBe('2')
    expect(screen.getByTestId('scenarios-total-count').textContent).toBe('8')
  })

  it('filters scenarios by clicking faceted sub-cluster buttons', () => {
    const { container } = render(
      <BundleScenariosBrowser
        scenarios={sampleScenarios}
        bundleName="developer-productivity"
      />,
    )

    // 点击 git 分簇
    const gitClusterBtn = screen.getByText('git').closest('button')
    expect(gitClusterBtn).not.toBeNull()
    if (gitClusterBtn) {
      fireEvent.click(gitClusterBtn)
    }

    // 应当只显示 3 项 git 工序
    expect(container.querySelector('[data-scenario="git-workflow"]')).not.toBeNull()
    expect(container.querySelector('[data-scenario="git-rebase"]')).not.toBeNull()
    expect(container.querySelector('[data-scenario="git-commit-linter"]')).not.toBeNull()
    expect(container.querySelector('[data-scenario="docker-compose-ops"]')).toBeNull()
    expect(container.querySelector('[data-scenario="python-fastapi-template"]')).toBeNull()
    expect(screen.getByTestId('scenarios-match-count').textContent).toBe('3')
  })

  it('shows empty state with reset button on zero matches', () => {
    const { container } = render(
      <BundleScenariosBrowser
        scenarios={sampleScenarios}
        bundleName="developer-productivity"
      />,
    )

    const searchInput = screen.getByPlaceholderText(/毫秒级检索 8 项工序/)
    fireEvent.change(searchInput, { target: { value: 'non-existent-xyz' } })

    expect(screen.getByText(/未找到与 "non-existent-xyz" 匹配的专精工序/)).toBeDefined()
    expect(screen.getByTestId('scenarios-match-count').textContent).toBe('0')

    // 点击重置
    const resetBtn = screen.getByText('重置所有筛选')
    fireEvent.click(resetBtn)

    // 恢复全量 8 个
    const badges = container.querySelectorAll('[data-scenario]')
    expect(badges.length).toBe(8)
    expect(screen.getByTestId('scenarios-match-count').textContent).toBe('8')
  })

  it('copies scenario URI to clipboard when clicked', () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    })

    const { container } = render(
      <BundleScenariosBrowser
        scenarios={sampleScenarios}
        bundleName="developer-productivity"
      />,
    )

    const scenarioBadge = container.querySelector('[data-scenario="git-workflow"]')
    expect(scenarioBadge).not.toBeNull()
    if (scenarioBadge) {
      fireEvent.click(scenarioBadge)
    }

    expect(writeTextMock).toHaveBeenCalledWith(
      'viking://agent/skills/developer-productivity/scenarios/git-workflow.md',
    )
  })

  it('strictly adheres to NO GREEN EVER rule', () => {
    const { container } = render(
      <BundleScenariosBrowser
        scenarios={sampleScenarios}
        bundleName="developer-productivity"
      />,
    )

    const html = container.innerHTML
    expect(html).not.toMatch(/text-green-/)
    expect(html).not.toMatch(/bg-green-/)
    expect(html).not.toMatch(/border-green-/)
  })
})
