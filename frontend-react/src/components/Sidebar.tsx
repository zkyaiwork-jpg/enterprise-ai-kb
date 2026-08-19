import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const navigation = [
  { label: '工作台', to: '/', icon: 'home', end: true },
  { label: '知识库', to: '/knowledge', icon: 'database', permission: 'file_view' },
  { label: 'AI助手', to: '/assistant', icon: 'smart_toy', permission: 'file_view' },
  { label: '智能检索', to: '/search', icon: 'search', permission: 'file_view' },
]

const linkClassName = ({ isActive }: { isActive: boolean }) =>
  [
    'flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors',
    isActive
      ? 'bg-surface-container text-primary'
      : 'text-on-surface-variant hover:bg-surface-container-low hover:text-primary',
  ].join(' ')

export function Sidebar() {
  const { hasPermission } = useAuth()
  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-[280px] flex-col border-r border-outline-variant bg-white px-4 py-6 md:flex">
      <div className="mb-10 flex items-center gap-3 px-2">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-container text-on-primary shadow-sm">
          <span className="material-symbols-outlined text-2xl">psychology</span>
        </div>
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold tracking-tight text-primary">
            企业AI知识库助手
          </h1>
          <p className="mt-0.5 truncate text-[11px] text-on-surface-variant">
            Enterprise AI Knowledge System
          </p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1.5" aria-label="主导航">
        {navigation.filter((item) => !item.permission || hasPermission(item.permission)).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={linkClassName}
          >
            <span className="material-symbols-outlined text-xl">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-outline-variant pt-4">
        {hasPermission('user_manage') && (
          <>
            <NavLink to="/admin/users" className={linkClassName}>
              <span className="material-symbols-outlined text-xl">manage_accounts</span>
              <span>用户管理</span>
            </NavLink>
            <NavLink to="/admin/departments" className={linkClassName}>
              <span className="material-symbols-outlined text-xl">corporate_fare</span>
              <span>部门管理</span>
            </NavLink>
            <NavLink to="/admin/teams" className={linkClassName}>
              <span className="material-symbols-outlined text-xl">groups</span>
              <span>小组管理</span>
            </NavLink>
          </>
        )}
        {hasPermission('model_manage') && (
          <NavLink to="/admin/model-config" className={linkClassName}>
            <span className="material-symbols-outlined text-xl">model_training</span>
            <span>模型配置</span>
          </NavLink>
        )}
        {hasPermission('audit_view') && (
          <NavLink to="/admin/audit-logs" className={linkClassName}>
            <span className="material-symbols-outlined text-xl">policy</span>
            <span>审计日志</span>
          </NavLink>
        )}
        <NavLink to="/settings" className={linkClassName}>
          <span className="material-symbols-outlined text-xl">settings</span>
          <span>设置</span>
        </NavLink>
      </div>
    </aside>
  )
}
