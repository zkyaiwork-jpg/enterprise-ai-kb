import { RouterProvider } from 'react-router-dom'

import { router } from './router'
import { DesktopTitleBar } from './components/DesktopTitleBar'
import { DesktopUserProvider } from './hooks/useDesktopUser'
import { AuthProvider } from './auth/AuthContext'

export default function App() {
  const isDesktop = Boolean(window.desktopApp)

  return (
    <DesktopUserProvider>
      <AuthProvider>
        {isDesktop && <DesktopTitleBar />}
        <div className={isDesktop ? 'desktop-content' : undefined}>
          <RouterProvider router={router} />
        </div>
      </AuthProvider>
    </DesktopUserProvider>
  )
}
