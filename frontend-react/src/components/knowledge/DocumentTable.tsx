export type DocumentItem = {
  id: string
  name: string
  folderId: number | null
  folderName: string
  type: string
  size: string
  chunks: number | null
  uploadedAt: string
  status: string
  visibility: 'private' | 'team' | 'department' | 'company' | null
  uploaderId: number | null
  departmentId: number | null
  teamId: number | null
}

type DocumentTableProps = {
  documents: DocumentItem[]
  onView: (document: DocumentItem) => void
  onDelete: (document: DocumentItem) => void
  onEdit: (document: DocumentItem) => void
  canEdit: boolean
  canDelete: boolean
  deletingId?: string | null
  emptyTitle?: string
  emptyDescription?: string
}

function getFileIcon(type: string) {
  if (type === 'PDF') return { className: 'bg-rose-50 text-rose-600', icon: 'picture_as_pdf' }
  if (type === 'DOCX' || type === 'DOC') return { className: 'bg-blue-50 text-blue-700', icon: 'description' }
  return { className: 'bg-slate-100 text-slate-600', icon: 'draft' }
}

function getStatusStyle(status: string) {
  if (status === '已索引') return { badge: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-500' }
  if (status === '失败') return { badge: 'bg-red-50 text-red-700', dot: 'bg-red-500' }
  return { badge: 'bg-amber-50 text-amber-700', dot: 'bg-amber-500' }
}

export function DocumentTable({
  documents,
  onView,
  onDelete,
  onEdit,
  canEdit,
  canDelete,
  deletingId = null,
  emptyTitle = '暂无文档',
  emptyDescription = '上传文档后将在这里展示',
}: DocumentTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[980px] border-collapse text-left">
        <thead>
          <tr className="border-b border-[#e7eaf3] bg-[#f8faff] text-xs font-semibold text-on-surface-variant">
            {['文档名称', '所属文件夹', '可见范围', '小组', '类型', '大小', '知识片段', '上传时间', '状态', '操作'].map((heading) => (
              <th key={heading} className="whitespace-nowrap px-4 py-3.5 font-semibold">{heading}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#edf0f6]">
          {documents.map((document) => {
            const fileIcon = getFileIcon(document.type)
            const statusStyle = getStatusStyle(document.status)
            return (
              <tr key={document.id} className="group bg-white transition-colors hover:bg-[#f9fbff]">
                <td className="px-4 py-4">
                  <button type="button" onClick={() => onView(document)} className="flex items-center gap-3 text-left">
                    <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${fileIcon.className}`}>
                      <span className="material-symbols-outlined text-[19px]">{fileIcon.icon}</span>
                    </span>
                    <span className="max-w-[220px] truncate text-sm font-semibold text-on-surface hover:text-primary">{document.name}</span>
                  </button>
                </td>
                <td className="px-4 py-4 text-sm text-on-surface-variant">{document.folderName}</td>
                <td className="px-4 py-4"><VisibilityBadge visibility={document.visibility} /></td>
                <td className="px-4 py-4 text-sm text-on-surface-variant">{document.teamId ?? '-'}</td>
                <td className="px-4 py-4"><span className="rounded-md bg-surface-container-low px-2 py-1 text-xs font-semibold text-on-surface-variant">{document.type}</span></td>
                <td className="px-4 py-4 text-sm text-on-surface-variant">{document.size}</td>
                <td className="px-4 py-4 text-sm text-on-surface-variant">{document.chunks ?? '暂无数据'}</td>
                <td className="px-4 py-4 text-sm text-on-surface-variant">{document.uploadedAt}</td>
                <td className="px-4 py-4">
                  <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${statusStyle.badge}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${statusStyle.dot}`} />
                    {document.status}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-3">
                    <button type="button" onClick={() => onView(document)} className="text-sm font-medium text-primary hover:text-[#003fa4]">查看</button>
                    {canEdit && /^\d+$/.test(document.id) && <button type="button" onClick={() => onEdit(document)} className="text-sm font-medium text-primary hover:text-[#003fa4]">编辑</button>}
                    {canDelete && <button
                      type="button"
                      onClick={() => onDelete(document)}
                      disabled={deletingId !== null}
                      className="min-w-[64px] text-sm font-medium text-on-surface-variant hover:text-error disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {deletingId === document.id ? '删除中...' : '删除'}
                    </button>}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {documents.length === 0 && (
        <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
          <span className="material-symbols-outlined text-4xl text-outline-variant">folder_off</span>
          <p className="mt-3 text-sm font-medium text-on-surface">{emptyTitle}</p>
          <p className="mt-1 text-xs text-on-surface-variant">{emptyDescription}</p>
        </div>
      )}
    </div>
  )
}

function VisibilityBadge({ visibility }: { visibility: DocumentItem['visibility'] }) {
  const labels = { private: '仅自己', team: '小组', department: '部门', company: '全公司' }
  return <span className="whitespace-nowrap rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-primary">{visibility ? labels[visibility] : '历史数据'}</span>
}
