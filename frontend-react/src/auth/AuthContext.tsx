import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { getCurrentUser, loginRequest, type CurrentUser } from '../api/auth'
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
  subscribeAuthChange,
  subscribeForbidden,
} from './authStorage'

interface AuthContextValue {
  isAuthenticated: boolean
  token: string | null
  currentUser: CurrentUser | null
  hasPermission: (permission: string) => boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  forbiddenMessage: string | null
  clearForbiddenMessage: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getAccessToken())
  const [forbiddenMessage, setForbiddenMessage] = useState<string | null>(null)
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)

  useEffect(() => subscribeAuthChange(() => setToken(getAccessToken())), [])
  useEffect(() => subscribeForbidden(() => setForbiddenMessage('无权执行此操作')), [])
  useEffect(() => {
    if (!token) {
      setCurrentUser(null)
      return
    }
    let active = true
    void getCurrentUser()
      .then((profile) => { if (active) setCurrentUser(profile) })
      .catch(() => { if (active) setCurrentUser(null) })
    return () => { active = false }
  }, [token])

  const login = useCallback(async (username: string, password: string) => {
    const result = await loginRequest(username, password)
    setAccessToken(result.access_token)
  }, [])

  const logout = useCallback(() => {
    clearAccessToken()
    setCurrentUser(null)
    setForbiddenMessage(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated: Boolean(token),
      token,
      currentUser,
      hasPermission: (permission) => currentUser?.permissions.includes(permission) ?? false,
      login,
      logout,
      forbiddenMessage,
      clearForbiddenMessage: () => setForbiddenMessage(null),
    }),
    [currentUser, forbiddenMessage, login, logout, token],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
