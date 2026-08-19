import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'

const actions = [
  { label: '上传文档', description: '添加知识资料', icon: 'upload_file', to: '/knowledge', tone: 'bg-blue-50 text-primary', permission: 'file_view' },
  { label: 'AI问答', description: '询问企业知识', icon: 'smart_toy', to: '/assistant', tone: 'bg-violet-50 text-violet-600', permission: 'file_view' },
  { label: '智能搜索', description: '语义检索内容', icon: 'manage_search', to: '/search', tone: 'bg-cyan-50 text-cyan-700', permission: 'file_view' },
  { label: '知识库管理', description: '管理企业文档', icon: 'folder_managed', to: '/knowledge', tone: 'bg-amber-50 text-amber-700', permission: 'file_view' },
]

export function QuickActions() {
  const { hasPermission } = useAuth()
  return (
    <section className="rounded-2xl border border-white bg-white p-6 shadow-ambient">
      <h2 className="text-lg font-semibold text-on-surface">快捷操作</h2>
      <p className="mt-1 text-sm text-on-surface-variant">快速开始常用工作</p>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        {actions.filter((action) => hasPermission(action.permission)).map((action) => (
          <Link
            key={action.label}
            to={action.to}
            className="group rounded-2xl border border-[#e7eaf3] p-4 transition-colors hover:border-[#c9d8f8] hover:bg-[#f8faff]"
          >
            <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${action.tone}`}>
              <span className="material-symbols-outlined text-[21px]">{action.icon}</span>
            </span>
            <h3 className="mt-4 text-sm font-semibold text-on-surface group-hover:text-primary">{action.label}</h3>
            <p className="mt-1 text-xs text-on-surface-variant">{action.description}</p>
          </Link>
        ))}
      </div>
    </section>
  )
}
