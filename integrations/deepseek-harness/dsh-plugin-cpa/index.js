/**
 * dsh-plugin-cpa
 * CPA 跨模型算力协同中枢 DSH 独立桥接器。
 */
export const name = 'dsh-plugin-cpa'
export const inject = ['agents', 'tools', 'systemPrompt']

export function apply(ctx, config = {}) {
  // 注入 CPA 算力导轨
  if (ctx.systemPrompt) {
    try {
      ctx.systemPrompt.context({
        name: 'cpa-squad-guide',
        order: 18,
        text: () => '【CPA 算力协同导轨】已接入 2080Ti CPA 多模型算力中枢，支持跨模型咨询与并发 Fanout。'
      })
    } catch (_) {}
  }
}
