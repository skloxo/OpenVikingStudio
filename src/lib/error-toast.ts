import { toast } from 'sonner'
import i18n from '#/i18n'
import { copyTextToClipboard } from './clipboard'

export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return String((error as { message: unknown }).message)
  }
  return String(error)
}

export function getLocalizedErrorMessage(
  error: unknown,
  fallback?: string,
): string {
  const record =
    typeof error === 'object' && error !== null
      ? (error as {
          statusCode?: number
          code?: string
          response?: { status?: number }
        })
      : undefined
  const status = record?.statusCode ?? record?.response?.status
  const code = record?.code

  if (status === 401 || code === 'UNAUTHENTICATED') {
    return i18n.t('studio:errors.authenticationFailed')
  }
  if (status === 403 || code === 'PERMISSION_DENIED' || code === 'FORBIDDEN') {
    return i18n.t('studio:errors.permissionDenied')
  }
  if (status === 404 || code === 'NOT_FOUND') {
    return i18n.t('studio:errors.resourceNotFound')
  }
  if (status === 409 || code === 'ALREADY_EXISTS' || code === 'CONFLICT') {
    return i18n.t('studio:errors.requestConflict')
  }
  if (status === 413) return i18n.t('studio:errors.payloadTooLarge')
  if (status === 429 || code === 'RATE_LIMITED') {
    return i18n.t('studio:errors.rateLimited')
  }
  if (
    status === 408 ||
    status === 504 ||
    code === 'ECONNABORTED' ||
    code === 'ETIMEDOUT'
  ) {
    return i18n.t('studio:errors.requestTimedOut')
  }
  if (code === 'ERR_NETWORK' || code === 'NETWORK_ERROR') {
    return i18n.t('studio:errors.networkFailed')
  }
  if (status !== undefined && status >= 500) {
    return i18n.t('studio:errors.serviceUnavailable')
  }
  if (status === 400 || status === 422 || code === 'INVALID_ARGUMENT') {
    return i18n.t('studio:errors.requestInvalid')
  }
  return fallback || i18n.t('studio:errors.requestFailed')
}

export function showErrorToast(error: unknown, fallback?: string) {
  const message = getLocalizedErrorMessage(error, fallback)
  const diagnostic = getErrorMessage(error)
  const payload = diagnostic && diagnostic !== message ? `${message}\n${diagnostic}` : message

  toast.error(message, {
    description: diagnostic !== message ? diagnostic : undefined,
    action: {
      label: i18n.t('adminConsole:actions.copyError'),
      onClick: () => {
        void copyTextToClipboard(payload)
          .then(() => toast.success(i18n.t('adminConsole:actions.errorCopied')))
          .catch(() => {})
      },
    },
  })
}
