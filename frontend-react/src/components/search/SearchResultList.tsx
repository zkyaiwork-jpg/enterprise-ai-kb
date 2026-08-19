import { SearchResultCard, type SearchResult } from './SearchResultCard'

type SearchResultListProps = {
  results: SearchResult[]
  query: string
}

export function SearchResultList({ results, query }: SearchResultListProps) {
  return (
    <section>
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div><h2 className="text-lg font-semibold text-on-surface">检索结果</h2><p className="mt-1 text-xs text-on-surface-variant">为“{query}”找到 {results.length} 条相关知识</p></div>
        <span className="flex items-center gap-1.5 text-xs text-on-surface-variant"><span className="material-symbols-outlined text-[16px] text-primary">neurology</span>按语义相关度排序</span>
      </div>
      <div className="space-y-4">{results.map((result) => <SearchResultCard key={result.id} result={result} />)}</div>
    </section>
  )
}
