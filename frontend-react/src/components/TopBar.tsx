import { useDesktopUser } from '../hooks/useDesktopUser'
import { useAuth } from '../auth/AuthContext'

export function TopBar() {
  const { userName } = useDesktopUser()
  const { logout } = useAuth()
  const displayName = userName || '用户'

  return (
    <header className="sticky top-0 z-10 flex h-16 items-center gap-5 border-b border-outline-variant bg-white px-5 md:px-6">
      <div className="flex min-w-0 flex-1 items-center">
        <div className="relative w-full max-w-[620px]">
          <span className="material-symbols-outlined pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-xl text-on-surface-variant">
            search
          </span>
          <input
            type="search"
            aria-label="全局搜索"
            placeholder="搜索文档、问题或关键词..."
            className="h-10 w-full rounded-full border border-outline-variant bg-surface-container-low pl-11 pr-4 text-sm text-on-surface outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
          />
        </div>
      </div>

      <div className="flex items-center gap-1 sm:gap-2">
        <button
          type="button"
          aria-label="通知"
          className="relative flex h-10 w-10 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-primary"
        >
          <span className="material-symbols-outlined text-[22px]">notifications</span>
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-error ring-2 ring-white" />
        </button>
        <button
          type="button"
          aria-label="消息"
          className="flex h-10 w-10 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-primary"
        >
          <span className="material-symbols-outlined text-[22px]">chat</span>
        </button>

        <div className="mx-2 hidden h-8 w-px bg-outline-variant sm:block" />

        <button
          type="button"
          className="flex items-center gap-2 rounded-full py-1 pl-1 pr-2 transition-colors hover:bg-surface-container-low"
          aria-label="用户菜单"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-fixed text-sm font-semibold text-primary">
            {displayName.slice(0, 1)}
          </span>
          <span className="hidden text-left sm:block">
            <span className="block text-sm font-semibold leading-tight text-on-surface">{displayName}</span>
          </span>
          <span className="material-symbols-outlined hidden text-base text-on-surface-variant sm:block">
            expand_more
          </span>
        </button>
        <button
          type="button"
          onClick={logout}
          className="hidden rounded-lg px-3 py-2 text-sm text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-primary sm:block"
        >
          退出登录
        </button>
      </div>
    </header>
  )
}
