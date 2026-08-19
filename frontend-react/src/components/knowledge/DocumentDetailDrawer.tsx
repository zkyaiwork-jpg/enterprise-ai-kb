import type { DocumentItem } from './DocumentTable'

type DocumentDetailDrawerProps = {
  document: DocumentItem | null
  onClose: () => void
}

export function DocumentDetailDrawer({ document, onClose }: DocumentDetailDrawerProps) {
  if (!document) return null

  const details = [
    ['文件类型', document.type],
    ['文件大小', document.size],
    ['所属文件夹', document.folderName],
    ['上传时间', document.uploadedAt],
    ['Chunk数量', document.chunks?.toString() ?? '暂无数据'],
    ['索引状态', document.status],
  ]

  return (
    <div className="fixed inset-0 z-50">
      <button type="button" aria-label="关闭文档详情" onClick={onClose} className="absolute inset-0 bg-[#172033]/20 backdrop-blur-[2px]" />
      <aside role="dialog" aria-modal="true" aria-labelledby="document-detail-title" className="absolute right-0 top-0 flex h-full w-full max-w-[440px] flex-col bg-white shadow-[-12px_0_40px_rgba(28,39,63,0.12)]">
        <header className="flex items-start justify-between gap-4 border-b border-[#e7eaf3] p-6">
          <div className="flex min-w-0 gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-primary"><span className="material-symbols-outlined">description</span></span>
            <div className="min-w-0">
              <h2 id="document-detail-title" className="break-words text-lg font-semibold text-on-surface">{document.name}</h2>
              <span className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />{document.status}</span>
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label="关闭" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-low"><span className="material-symbols-outlined">close</span></button>
        </header>
        <div className="flex-1 overflow-y-auto p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-on-surface-variant">文档元数据</p>
          <dl className="mt-5 grid grid-cols-2 gap-x-5 gap-y-6">
            <div className="col-span-2"><dt className="text-xs text-on-surface-variant">文件名称</dt><dd className="mt-1.5 break-words text-sm font-medium text-on-surface">{document.name}</dd></div>
            {details.map(([label, value]) => <div key={label}><dt className="text-xs text-on-surface-variant">{label}</dt><dd className="mt-1.5 text-sm font-medium text-on-surface">{value}</dd></div>)}
            <div className="col-span-2"><dt className="text-xs text-on-surface-variant">document_id</dt><dd className="mt-1.5 break-all rounded-lg bg-surface-container-low p-3 font-mono text-xs text-on-surface">{document.id}</dd></div>
          </dl>
          <div className="mt-8 rounded-2xl border border-dashed border-outline-variant bg-[#f8faff] p-6 text-center">
            <span className="material-symbols-outlined text-3xl text-outline-variant">preview</span>
            <p className="mt-2 text-sm text-on-surface-variant">文档内容预览将在接入后端后提供</p>
          </div>
        </div>
      </aside>
    </div>
  )
}
