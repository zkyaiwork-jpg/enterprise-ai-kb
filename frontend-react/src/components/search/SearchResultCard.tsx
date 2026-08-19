export type SearchResult = {
  id: string
  filename: string | null
  folderName: string | null
  fileType: string | null
  chunkIndex: number | null
  distance: number | null
  content: string
  metadata: Record<string, unknown> | null
  embeddingModel: string | null
  vectorDatabase: string | null
}

function getRelevance(distance: number | null) {
  if (distance === null || !Number.isFinite(distance)) return { label: '暂无相关度', className: 'bg-slate-100 text-slate-600' }
  if (distance <= 0.2) return { label: '高度相关', className: 'bg-emerald-50 text-emerald-700' }
  if (distance <= 0.5) return { label: '相关', className: 'bg-blue-50 text-primary' }
  return { label: '一般相关', className: 'bg-amber-50 text-amber-700' }
}

export function SearchResultCard({ result }: { result: SearchResult }) {
  const relevance = getRelevance(result.distance)
  const isPdf = result.filename?.toLowerCase().endsWith('.pdf') ?? false
  const displayContent = cleanKnowledgeContent(result.content)

  return (
    <article className="rounded-2xl border border-white bg-white p-5 shadow-ambient transition-colors hover:border-blue-100 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${isPdf ? 'bg-rose-50 text-rose-600' : 'bg-blue-50 text-primary'}`}>
          <span className="material-symbols-outlined text-[22px]">{isPdf ? 'picture_as_pdf' : 'description'}</span>
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 className="break-all text-base font-semibold text-on-surface">{result.filename || '未知来源文件'}</h3>
              <div className="mt-3 rounded-xl bg-blue-50/70 px-3.5 py-3 text-xs text-on-surface-variant">
                <p className="font-semibold text-on-surface">来源</p>
                <div className="mt-2 flex flex-col gap-1.5 sm:flex-row sm:flex-wrap sm:gap-x-5">
                  <span className="inline-flex items-center gap-1.5"><span className="material-symbols-outlined text-[17px] text-primary">folder</span>{result.folderName || '未分配文件夹'}</span>
                  <span className="inline-flex items-center gap-1.5"><span className="material-symbols-outlined text-[17px] text-primary">description</span>{result.filename || '未知来源文件'}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-xl border border-[#e7ebf3] bg-[#f9fbff] px-4 py-3.5">
            <p className="whitespace-pre-line text-sm leading-7 text-on-surface">{displayContent || '暂无可展示的匹配文本'}</p>
          </div>

          <details className="group mt-4 border-t border-[#e7ebf3] pt-4">
            <summary className="flex cursor-pointer list-none items-center justify-between text-sm font-semibold text-primary hover:text-[#003fa4]">
              查看技术详情
              <span className="material-symbols-outlined text-[19px] transition-transform group-open:rotate-180">expand_more</span>
            </summary>
            <div className="mt-3 rounded-xl bg-[#f8faff] p-4 text-xs text-on-surface-variant">
              <p className="font-semibold text-on-surface">检索详情</p>
              <dl className="mt-3 grid grid-cols-[100px_minmax(0,1fr)] gap-x-3 gap-y-2">
                <dt>Chunk</dt><dd>{result.chunkIndex ?? '暂无数据'}</dd>
                <dt>Distance</dt><dd>{result.distance !== null && Number.isFinite(result.distance) ? result.distance.toFixed(3) : '暂无数据'}</dd>
                <dt>Similarity</dt><dd>未单独计算（使用 Distance 排序）</dd>
                <dt>相关程度</dt><dd><span className={`rounded-full px-2 py-0.5 font-medium ${relevance.className}`}>{relevance.label}</span></dd>
                <dt>文件类型</dt><dd>{result.fileType?.toUpperCase() || '暂无数据'}</dd>
                <dt>Embedding模型</dt><dd className="break-all">{result.embeddingModel || 'BAAI/bge-small-zh-v1.5'}</dd>
                <dt>向量数据库</dt><dd>{result.vectorDatabase || 'ChromaDB'}</dd>
                <dt>Metadata</dt><dd className="break-all font-mono text-[11px]">{result.metadata ? JSON.stringify(result.metadata) : '暂无数据'}</dd>
              </dl>
              <div className="mt-4 border-t border-[#e5e9f2] pt-3">
                <p className="font-medium text-on-surface">原始Chunk内容</p>
                <p className="mt-1.5 whitespace-pre-line leading-5">{result.content || '暂无原始Chunk内容'}</p>
              </div>
            </div>
          </details>
        </div>
      </div>
    </article>
  )
}
import { cleanKnowledgeContent } from '../../utils/knowledgeContent'
