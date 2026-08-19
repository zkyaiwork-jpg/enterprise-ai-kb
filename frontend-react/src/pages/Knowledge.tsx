import { useCallback, useEffect, useMemo, useState } from 'react'

import { deleteDocument, getDocuments, updateDocument, uploadDocument, type DocumentMetadata, type DocumentVisibility } from '../api/documents'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { createFolder as createFolderRequest, getFolders, type Folder } from '../api/folders'
import { CategorySidebar, type Category } from '../components/knowledge/CategorySidebar'
import { CreateFolderModal } from '../components/knowledge/CreateFolderModal'
import { DocumentDetailDrawer } from '../components/knowledge/DocumentDetailDrawer'
import { DocumentTable, type DocumentItem } from '../components/knowledge/DocumentTable'
import { DocumentToolbar } from '../components/knowledge/DocumentToolbar'
import { UploadModal } from '../components/knowledge/UploadModal'
import { EditDocumentModal } from '../components/knowledge/EditDocumentModal'
import { listUploadTeams, type TeamOption } from '../api/users'

function formatFileSize(bytes: number | null, legacySize?: number | null) {
  const size = bytes ?? legacySize
  if (size === null || size === undefined || !Number.isFinite(size)) return '暂无数据'
  if (size < 1024) return `${size} B`
  if (size < 1024 ** 2) return `${(size / 1024).toFixed(size < 10 * 1024 ? 1 : 0)} KB`
  return `${(size / 1024 ** 2).toFixed(1)} MB`
}

function formatDate(value: string | null) {
  if (!value) return '暂无数据'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(date).replaceAll('/', '-')
}

function formatStatus(value: string | null) {
  const status = value?.toLowerCase()
  if (status === 'indexed') return '已索引'
  if (status === 'processing' || status === 'pending') return '处理中'
  if (status === 'failed' || status === 'error') return '失败'
  return value || '暂无数据'
}

function mapDocument(document: DocumentMetadata, index: number): DocumentItem {
  return {
    id: document.document_id || `${document.filename}-${index}`,
    name: document.filename,
    folderId: document.folder_id,
    folderName: document.folder_name || '未分配文件夹',
    type: (document.file_type || document.type || '未知').replace('.', '').toUpperCase(),
    size: formatFileSize(document.file_size, document.size),
    chunks: document.chunk_count,
    uploadedAt: formatDate(document.uploaded_at),
    status: formatStatus(document.status),
    visibility: document.visibility,
    uploaderId: document.uploader_id,
    departmentId: document.department_id,
    teamId: document.team_id,
  }
}

export function Knowledge() {
  const { hasPermission, currentUser } = useAuth()
  const allowedVisibilities = useMemo<DocumentVisibility[]>(() => [
    'private',
    ...(hasPermission('file_publish_team') ? ['team' as const] : []),
    ...(hasPermission('file_publish_department') ? ['department' as const] : []),
    ...(hasPermission('file_publish_company') ? ['company' as const] : []),
  ], [hasPermission])
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [folders, setFolders] = useState<Folder[]>([])
  const [teams, setTeams] = useState<TeamOption[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [activeCategory, setActiveCategory] = useState<number | 'all'>('all')
  const [search, setSearch] = useState('')
  const [selectedDocument, setSelectedDocument] = useState<DocumentItem | null>(null)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [folderModalOpen, setFolderModalOpen] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<DocumentItem | null>(null)
  const [editingDocument, setEditingDocument] = useState<DocumentItem | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteFeedback, setDeleteFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const loadDocuments = useCallback(async () => {
      setLoading(true)
      setError(false)
      try {
        const [documentResponse, folderResponse, teamResponse] = await Promise.all([getDocuments(), getFolders(), hasPermission('file_upload') ? listUploadTeams() : Promise.resolve([])])
        setDocuments((documentResponse.documents ?? []).map(mapDocument))
        setFolders(folderResponse)
        setTeams(teamResponse)
      } catch {
        setDocuments([])
        setError(true)
      } finally {
        setLoading(false)
      }
  }, [hasPermission])

  useEffect(() => {
    void loadDocuments()
  }, [loadDocuments])

  const handleUpload = async (file: File, folderId: number, visibility: DocumentVisibility, teamId?: number) => {
    try {
      await uploadDocument(file, folderId, visibility, teamId)
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 403) throw new Error('无权将文件发布到该可见范围')
      if (reason instanceof ApiError && reason.status === 409) throw new Error('同名文件已存在，请更换文件名或使用编辑功能')
      throw new Error('文档上传失败，请稍后重试')
    }
    await loadDocuments()
  }

  const handleEdit = async (documentId: number, payload: { original_name?: string; visibility?: DocumentVisibility }) => {
    await updateDocument(documentId, payload)
    setEditingDocument(null)
    setDeleteFeedback({ type: 'success', message: '文档信息修改成功，列表已刷新。' })
    await loadDocuments()
  }

  const handleCreateFolder = async (name: string) => {
    await createFolderRequest(name)
    const updatedFolders = await getFolders()
    setFolders(updatedFolders)
  }

  const handleDelete = async () => {
    if (!pendingDelete || deletingId) return
    setDeletingId(pendingDelete.id)
    setDeleteFeedback(null)
    try {
      await deleteDocument(pendingDelete.name)
      await loadDocuments()
      if (selectedDocument?.id === pendingDelete.id) setSelectedDocument(null)
      setPendingDelete(null)
      setDeleteFeedback({ type: 'success', message: '文档删除成功，知识库列表已刷新。' })
    } catch (error) {
      setDeleteFeedback({ type: 'error', message: error instanceof ApiError && error.status === 403 ? '无权删除该文件' : '文档删除失败，请稍后重试。' })
    } finally {
      setDeletingId(null)
    }
  }

  const categories = useMemo<Category[]>(() => {
    const counts = new Map<number, number>()
    documents.forEach((document) => {
      if (document.folderId !== null) counts.set(document.folderId, (counts.get(document.folderId) ?? 0) + 1)
    })
    return [
      { id: 'all', name: '全部文档', count: documents.length, icon: 'folder_open' },
      ...folders.map((folder) => ({ id: folder.id, name: folder.name, count: counts.get(folder.id) ?? 0, icon: 'folder' })),
    ]
  }, [documents, folders])

  const filteredDocuments = useMemo(() => documents.filter((document) => {
    const categoryMatch = activeCategory === 'all' || document.folderId === activeCategory
    return categoryMatch && document.name.toLowerCase().includes(search.trim().toLowerCase())
  }), [activeCategory, documents, search])

  const hasFilters = activeCategory !== 'all' || search.trim().length > 0

  return (
    <div className="pb-6">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Knowledge Base</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-on-surface">知识库</h1><p className="mt-2 text-sm text-on-surface-variant">管理和查看企业文档资源</p></div>
        {hasPermission('file_upload') && <button type="button" onClick={() => setUploadOpen(true)} className="inline-flex w-fit items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-[#0044ad]"><span className="material-symbols-outlined text-[20px]">add</span>上传文档</button>}
      </header>

      {deleteFeedback && (
        <div className={`mt-5 flex items-start justify-between gap-4 rounded-xl px-4 py-3 text-sm ${deleteFeedback.type === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`} role="status">
          <span className="flex items-start gap-2"><span className="material-symbols-outlined mt-0.5 text-[19px]">{deleteFeedback.type === 'success' ? 'check_circle' : 'error'}</span>{deleteFeedback.message}</span>
          <button type="button" onClick={() => setDeleteFeedback(null)} aria-label="关闭提示" className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full hover:bg-white/60"><span className="material-symbols-outlined text-[17px]">close</span></button>
        </div>
      )}

      <div className="mt-7 grid items-start gap-5 lg:grid-cols-[220px_minmax(0,1fr)]">
        <CategorySidebar categories={categories} activeCategory={activeCategory} onChange={setActiveCategory} onCreate={() => setFolderModalOpen(true)} />
        <section className="min-w-0 overflow-hidden rounded-2xl border border-white bg-white shadow-ambient">
          <DocumentToolbar search={search} onSearchChange={setSearch} />

          {loading ? (
            <div className="flex min-h-[300px] flex-col items-center justify-center px-6 text-center">
              <span className="material-symbols-outlined animate-pulse text-4xl text-primary">cloud_sync</span>
              <p className="mt-4 text-sm font-medium text-on-surface">正在加载知识库...</p>
            </div>
          ) : error ? (
            <div className="flex min-h-[300px] flex-col items-center justify-center px-6 text-center">
              <span className="material-symbols-outlined text-4xl text-error">cloud_off</span>
              <p className="mt-4 text-sm font-semibold text-on-surface">知识库加载失败</p>
              <p className="mt-2 text-xs text-on-surface-variant">请确认后端服务已经启动，稍后刷新页面重试。</p>
            </div>
          ) : (
            <DocumentTable
              documents={filteredDocuments}
              onView={setSelectedDocument}
              onDelete={(document) => {
                setDeleteFeedback(null)
                setPendingDelete(document)
              }}
              onEdit={setEditingDocument}
              canEdit={hasPermission('file_edit')}
              canDelete={hasPermission('file_delete')}
              deletingId={deletingId}
              emptyTitle={hasFilters ? '未找到相关文档' : '暂无文档'}
              emptyDescription={hasFilters ? '请更换关键词或文档分类' : '上传文档后将在这里展示'}
            />
          )}

          {!loading && !error && <footer className="flex items-center justify-between border-t border-[#e7eaf3] bg-[#fbfcff] px-4 py-3 text-xs text-on-surface-variant"><span>显示 {filteredDocuments.length} 份文档</span><span>数据来自企业知识库</span></footer>}
        </section>
      </div>

      <DocumentDetailDrawer document={selectedDocument} onClose={() => setSelectedDocument(null)} />
      <UploadModal open={uploadOpen} folders={folders} onClose={() => setUploadOpen(false)} onUpload={handleUpload} allowedVisibilities={allowedVisibilities} teams={teams} currentTeamId={currentUser?.role?.name === 'employee' || currentUser?.role?.name === 'leader' ? currentUser.team?.id : undefined} />
      <EditDocumentModal document={editingDocument} onClose={() => setEditingDocument(null)} onSave={handleEdit} allowedVisibilities={allowedVisibilities} />
      <CreateFolderModal open={folderModalOpen} onClose={() => setFolderModalOpen(false)} onCreate={handleCreateFolder} />

      {pendingDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button type="button" aria-label="关闭删除确认" onClick={() => !deletingId && setPendingDelete(null)} className="absolute inset-0 bg-[#172033]/25 backdrop-blur-[2px]" />
          <section role="alertdialog" aria-modal="true" aria-labelledby="delete-dialog-title" className="relative w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl sm:p-8">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-50 text-error"><span className="material-symbols-outlined">delete</span></span>
            <h2 id="delete-dialog-title" className="mt-5 text-xl font-semibold text-on-surface">确定删除该文档？</h2>
            <p className="mt-2 break-all text-sm leading-6 text-on-surface-variant">即将删除“{pendingDelete.name}”。删除后，该文档将不再出现在知识库中。</p>
            <div className="mt-7 flex justify-end gap-3">
              <button type="button" onClick={() => setPendingDelete(null)} disabled={deletingId !== null} className="rounded-xl border border-[#dfe3ee] px-5 py-2.5 text-sm font-semibold text-on-surface-variant hover:bg-surface-container-low disabled:cursor-not-allowed disabled:opacity-50">取消</button>
              <button type="button" onClick={() => void handleDelete()} disabled={deletingId !== null} className="inline-flex min-w-[112px] items-center justify-center gap-2 rounded-xl bg-error px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#9f1515] disabled:cursor-wait disabled:bg-[#d58b86]"><span className="material-symbols-outlined text-[18px]">{deletingId ? 'progress_activity' : 'delete'}</span>{deletingId ? '删除中...' : '确认删除'}</button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
