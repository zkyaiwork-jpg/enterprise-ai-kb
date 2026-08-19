import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'


type DesktopUserContextValue = {
  userName: string
  hasUserName: boolean
  loading: boolean
  setUserName: (userName: string) => void
}

const DesktopUserContext = createContext<DesktopUserContextValue | null>(null)

export function DesktopUserProvider({ children }: { children: ReactNode }) {
  const [userName, setUserName] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const desktopApi = window.desktopApp
    if (!desktopApi) {
      setLoading(false)
      return
    }
    void desktopApi.getUserInfo()
      .then((user) => setUserName(user.userName))
      .catch(() => setUserName(''))
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo(() => ({
    userName,
    hasUserName: Boolean(userName),
    loading,
    setUserName,
  }), [loading, userName])

  return <DesktopUserContext.Provider value={value}>{children}</DesktopUserContext.Provider>
}

export function useDesktopUser() {
  const context = useContext(DesktopUserContext)
  if (!context) throw new Error('useDesktopUser must be used inside DesktopUserProvider')
  return context
}
