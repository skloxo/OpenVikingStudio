import test from 'node:test'
import assert from 'node:assert/strict'
import { apply } from '../../packages/plugins/keepass-vault/index.js'

test('DSH keepass-vault adapter output.render contract', async () => {
  const registeredTools = []
  const mockTools = {
    register: (tool) => {
      registeredTools.push(tool)
    }
  }

  const mockCtx = {
    tools: mockTools,
    systemPrompt: {
      context: () => {}
    }
  }

  // 执行 apply
  apply(mockCtx, {})

  // 等待微任务完成（如果有动态 import）
  await new Promise(r => setTimeout(r, 100))

  assert.equal(registeredTools.length, 3, '应注册 3 个原子工具')

  const names = registeredTools.map(t => t.name)
  assert.ok(names.includes('keepass_search'))
  assert.ok(names.includes('keepass_get'))
  assert.ok(names.includes('keepass_status'))

  for (const tool of registeredTools) {
    assert.ok(tool.output, `工具 ${tool.name} 必须包含 output`)
    assert.equal(typeof tool.output.render, 'function', `工具 ${tool.name} 的 output.render 必须是函数，杜绝 userRender is not a function 异常`)

    // 测试各种返回值的 render 结果
    const testValues = ['普通字符串', { json: true }, null, undefined, 12345]
    for (const val of testValues) {
      const rendered = tool.output.render({}, val)
      assert.ok(Array.isArray(rendered), `工具 ${tool.name} 的 output.render 必须返回数组`)
      assert.ok(rendered.length > 0, `工具 ${tool.name} 的 output.render 数组不能为空`)
      assert.equal(rendered[0].type, 'text', `工具 ${tool.name} 的 Block 类型必须为 text`)
      assert.equal(typeof rendered[0].text, 'string', `工具 ${tool.name} 的 Block 内容必须为字符串`)
    }

    // 测试 presentCall
    if (typeof tool.presentCall === 'function') {
      const callPres = tool.presentCall({ query: 'test' })
      assert.ok(callPres, `工具 ${tool.name} presentCall 应返回展示卡片元数据`)
      assert.equal(callPres.card, 'generic')
      assert.ok(['read', 'other'].includes(callPres.kind))
      assert.ok(typeof callPres.title === 'string' && callPres.title.length > 0)
    }
  }
})
