import type { ChatSource } from '../../api/chat'

function getRelevance(distance: number | null) {
  if (distance === null || !Number.isFinite(distance)) {
    return { label: '暂无相关度', className: 'bg-slate-100 text-slate-600' }
  }
  if (distance <= 0.2) return { label: '高度相关', className: 'bg-emerald-50 text-emerald-700' }
  if (distance <= 0.5) return { label: '相关', className: 'bg-blue-50 text-primary' }
  return { label: '一般相关', className: 'bg-amber-50 text-amber-700' }
}

export function SourceCard({ source }: { source: ChatSource }) {
  const relevance = getRelevance(source.distance)

  return (
    <article className="min-w-0 flex-1 rounded-xl border border-[#dfe6f3] bg-white p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-on-surface-variant">来源</p>
      <div className="mt-3 space-y-2 text-xs text-on-surface">
        <p className="flex items-center gap-2"><span className="material-symbols-outlined text-[18px] text-primary">folder</span><span className="break-all">{source.folder_name || '未分配文件夹'}</span></p>
        <p className="flex items-center gap-2"><span className="material-symbols-outlined text-[18px] text-primary">description</span><span className="break-all font-semibold">{source.filename || '未知来源文件'}</span></p>
      </div>

      <details className="group mt-4 border-t border-[#edf0f6] pt-3">
        <summary className="flex cursor-pointer list-none items-center justify-between text-xs font-semibold text-primary">
          查看技术详情
          <span className="material-symbols-outlined text-[18px] transition-transform group-open:rotate-180">expand_more</span>
        </summary>
        <div className="mt-3 rounded-lg bg-[#f8faff] p-3 text-[11px] leading-5 text-on-surface-variant">
          <p className="mb-2 font-semibold text-on-surface">检索详情</p>
          <dl className="grid grid-cols-[88px_minmax(0,1fr)] gap-x-2 gap-y-1.5">
            <dt>文件夹</dt><dd className="break-all">{source.folder_name || '未分配文件夹'}</dd>
            <dt>文件</dt><dd className="break-all">{source.filename || '未知来源文件'}</dd>
            <dt>文件类型</dt><dd>{source.file_type?.toUpperCase() || '暂无数据'}</dd>
            <dt>Chunk</dt><dd>{source.chunk_index ?? '暂无数据'}</dd>
            <dt>Distance</dt><dd>{source.distance !== null && source.distance !== undefined && Number.isFinite(source.distance) ? source.distance.toFixed(3) : '暂无数据'}</dd>
            <dt>Similarity</dt><dd>未单独计算（使用 Distance 排序）</dd>
            <dt>相关程度</dt><dd><span className={`rounded-full px-2 py-0.5 font-medium ${relevance.className}`}>{relevance.label}</span></dd>
            <dt>Embedding模型</dt><dd className="break-all">{source.embedding_model || 'BAAI/bge-small-zh-v1.5'}</dd>
            <dt>向量数据库</dt><dd>{source.vector_database || 'ChromaDB'}</dd>
            <dt>Metadata</dt><dd className="break-all font-mono text-[10px]">{source.metadata ? JSON.stringify(source.metadata) : '暂无数据'}</dd>
          </dl>
          <div className="mt-3 border-t border-[#e5e9f2] pt-3">
            <p className="font-medium text-on-surface">原始Chunk内容</p>
            <p className="mt-1.5 whitespace-pre-line">{source.content || '暂无引用文本片段'}</p>
          </div>
        </div>
      </details>
    </article>
  )
}
