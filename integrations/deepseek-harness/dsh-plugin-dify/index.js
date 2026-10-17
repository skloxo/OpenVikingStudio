/**
 * dsh-plugin-dify
 * Dify 智能体与工作流中枢 DSH 独立桥接器。
 */
export const name = 'dsh-plugin-dify'
export const inject = ['agents', 'tools', 'systemPrompt']

export function apply(ctx, config = {}) {
  // 注入 Dify 专属工作流导轨
  if (ctx.systemPrompt) {
    try {
      ctx.systemPrompt.context({
        name: 'dify-workflow-guide',
        order: 20,
        text: () => '【Dify 工作流导轨】已接入 Dify 智能体中枢，可通过 API 直通工作流与知识库。'
      })
    } catch (_) {}
  }
}
