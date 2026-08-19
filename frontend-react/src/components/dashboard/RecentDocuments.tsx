export type RecentDocument = {
  id: string
  name: string
  category: string
  chunks: number | null
  type: string
  status: string
}

type RecentDocumentsProps = {
  documents: RecentDocument[]
  loading?: boolean
  error?: boolean
}

export function RecentDocuments({ documents, loading = false, error = false }: RecentDocumentsProps) {
  return (
    <section className="rounded-2xl border border-white bg-white p-6 shadow-ambient">
      <div className="flex items-center justify-between gap-4">
        <div><h2 className="text-lg font-semibold text-on-surface">最近上传</h2><p className="mt-1 text-sm text-on-surface-variant">近期加入知识库的企业文档</p></div>
        {!loading && !error && <span className="text-sm font-medium text-primary">共 {documents.length} 份</span>}
      </div>

      {loading ? (
        <div className="flex min-h-[180px] items-center justify-center text-sm text-on-surface-variant"><span className="material-symbols-outlined mr-2 animate-pulse text-primary">cloud_sync</span>正在加载最近文档...</div>
      ) : error ? (
        <div className="flex min-h-[180px] flex-col items-center justify-center text-center"><span className="material-symbols-outlined text-3xl text-error">cloud_off</span><p className="mt-3 text-sm font-medium text-on-surface">最近文档加载失败</p></div>
      ) : documents.length === 0 ? (
        <div className="flex min-h-[180px] flex-col items-center justify-center text-center"><span className="material-symbols-outlined text-3xl text-outline-variant">folder_open</span><p className="mt-3 text-sm font-medium text-on-surface">暂无最近上传文档</p><p className="mt-1 text-xs text-on-surface-variant">上传文档后将在这里展示</p></div>
      ) : (
        <div className="mt-6 space-y-3">
          {documents.map((document) => {
            const indexed = document.status.toLowerCase() === 'indexed'
            const isPdf = document.type.toUpperCase() === 'PDF'
            return (
              <article key={document.id} className="flex flex-col gap-4 rounded-2xl border border-[#e7eaf3] px-4 py-4 sm:flex-row sm:items-center">
                <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${isPdf ? 'bg-rose-50 text-rose-600' : 'bg-blue-50 text-primary'}`}><span className="material-symbols-outlined">{isPdf ? 'picture_as_pdf' : 'description'}</span></span>
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-sm font-semibold text-on-surface">{document.name}</h3>
                  <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-on-surface-variant"><span>{document.category}</span><span className="h-1 w-1 rounded-full bg-outline-variant" /><span>{document.chunks === null ? '片段暂无数据' : `${document.chunks}片段`}</span><span className="rounded-md bg-surface-container-low px-2 py-0.5 font-medium">{document.type}</span></div>
                </div>
                <span className={`inline-flex w-fit items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium ${indexed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}><span className={`h-1.5 w-1.5 rounded-full ${indexed ? 'bg-emerald-500' : 'bg-amber-500'}`} />{indexed ? '已索引' : document.status || '暂无状态'}</span>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
