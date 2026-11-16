import { beforeEach, describe, expect, it, vi } from 'vitest'

const { toastErrorMock, toastSuccessMock, copyMock } = vi.hoisted(() => ({
  toastErrorMock: vi.fn(),
  toastSuccessMock: vi.fn(),
  copyMock: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('sonner', () => ({
  toast: {
    error: toastErrorMock,
    success: toastSuccessMock,
  },
}))

vi.mock('./clipboard', () => ({
  copyTextToClipboard: copyMock,
}))

import '#/i18n'
import { getLocalizedErrorMessage, showErrorToast } from './error-toast'

describe('error-toast helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('maps HTTP status codes and semantic error codes cleanly', () => {
    expect(getLocalizedErrorMessage({ statusCode: 401 })).toBeTruthy()
    expect(getLocalizedErrorMessage({ code: 'PERMISSION_DENIED' })).toBeTruthy()
    expect(getLocalizedErrorMessage({ statusCode: 503 })).toBeTruthy()
  })

  it('triggers toast.error with a copyable diagnostic action (#7695)', async () => {
    showErrorToast(new Error('ov.conf syntax error at line 12'), 'Fallback')
    expect(toastErrorMock).toHaveBeenCalledTimes(1)
    const [, options] = toastErrorMock.mock.calls[0]
    expect(options.description).toContain('ov.conf syntax error')
    expect(typeof options.action.onClick).toBe('function')
    options.action.onClick()
    await Promise.resolve()
    expect(copyMock).toHaveBeenCalledTimes(1)
  })
})
