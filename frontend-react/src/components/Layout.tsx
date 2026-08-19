import { Outlet } from 'react-router-dom'

import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { useAuth } from '../auth/AuthContext'

export function Layout() {
  const { forbiddenMessage, clearForbiddenMessage } = useAuth()

  return (
    <div className="min-h-screen bg-[#f5f9ff] text-on-surface">
      <Sidebar />
      <div className="min-h-screen min-w-0 md:ml-[280px]">
        <TopBar />
        <main className="px-5 py-8 md:px-8 md:py-10">
          <div className="mx-auto max-w-[1440px]">
            <Outlet />
          </div>
        </main>
      </div>
      {forbiddenMessage && (
        <button
          type="button"
          onClick={clearForbiddenMessage}
          className="fixed bottom-6 right-6 z-50 rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white shadow-xl"
          aria-label="关闭权限提示"
        >
          {forbiddenMessage}
        </button>
      )}
    </div>
  )
}
