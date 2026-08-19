const ACCESS_TOKEN_KEY = 'enterprise-ai-kb.access-token'
const AUTH_CHANGED_EVENT = 'enterprise-ai-kb:auth-changed'
const FORBIDDEN_EVENT = 'enterprise-ai-kb:forbidden'

function storageAvailable() {
  return typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined'
}

export function getAccessToken(): string | null {
  return storageAvailable() ? window.sessionStorage.getItem(ACCESS_TOKEN_KEY) : null
}

export function setAccessToken(token: string): void {
  if (!storageAvailable()) return
  window.sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT))
}

export function clearAccessToken(): void {
  if (!storageAvailable()) return
  window.sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT))
}

export function subscribeAuthChange(listener: () => void): () => void {
  window.addEventListener(AUTH_CHANGED_EVENT, listener)
  return () => window.removeEventListener(AUTH_CHANGED_EVENT, listener)
}

export function notifyForbidden(): void {
  if (typeof window !== 'undefined') window.dispatchEvent(new Event(FORBIDDEN_EVENT))
}

export function subscribeForbidden(listener: () => void): () => void {
  window.addEventListener(FORBIDDEN_EVENT, listener)
  return () => window.removeEventListener(FORBIDDEN_EVENT, listener)
}
