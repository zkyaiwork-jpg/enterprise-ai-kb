import { useEffect, useState } from 'react'

import { getFolders, type Folder } from '../api/folders'
import { searchDocuments } from '../api/search'
import { SearchEmpty } from '../components/search/SearchEmpty'
import { SearchFilters, type SearchFilterValues } from '../components/search/SearchFilters'
import { SearchHeader } from '../components/search/SearchHeader'
import { SearchResultList } from '../components/search/SearchResultList'
import type { SearchResult } from '../components/search/SearchResultCard'

const initialFilters: SearchFilterValues = { folderId: 'all', fileType: '全部', time: '不限' }

export function Search() {
  const [filters, setFilters] = useState<SearchFilterValues>(initialFilters)
  const [folders, setFolders] = useState<Folder[]>([])
  const [status, setStatus] = useState<'initial' | 'loading' | 'results' | 'empty' | 'error'>('initial')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    void getFolders().then(setFolders).catch(() => setFolders([]))
  }, [])

  const runSearch = async (value: string) => {
    if (status === 'loading') return
    setQuery(value)
    setResults([])
    setErrorMessage('')
    setStatus('loading')

    try {
      const response = await searchDocuments({
        query: value,
        folder_id: filters.folderId === 'all' ? undefined : filters.folderId,
        file_type: filters.fileType === '全部' ? undefined : filters.fileType,
      })
      const mappedResults = (response.results ?? []).map((result, index) => ({
        id: `${result.filename ?? 'source'}-${result.chunk_index ?? index}-${index}`,
        filename: result.filename,
        folderName: result.folder_name,
        fileType: result.file_type,
        chunkIndex: result.chunk_index,
        distance: result.distance,
        content: result.content,
        metadata: result.metadata,
        embeddingModel: result.embedding_model,
        vectorDatabase: result.vector_database,
      }))
      setResults(mappedResults)
      setStatus(mappedResults.length > 0 ? 'results' : 'empty')
    } catch (error) {
      setResults([])
      setErrorMessage(error instanceof Error ? error.message : '检索请求失败，请稍后重试。')
      setStatus('error')
    }
  }

  return (
    <div className="space-y-6 pb-6">
      <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Semantic Search</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-on-surface">智能检索</h1><p className="mt-2 text-sm text-on-surface-variant">通过AI语义理解快速定位企业知识。</p></div>
      <SearchHeader onSearch={(value) => void runSearch(value)} loading={status === 'loading'} />
      <SearchFilters values={filters} folders={folders} onChange={setFilters} />

      {status === 'initial' && <SearchEmpty state="initial" />}
      {status === 'loading' && <SearchEmpty state="loading" />}
      {status === 'empty' && <SearchEmpty state="empty" />}
      {status === 'error' && <SearchEmpty state="error" detail={errorMessage} />}
      {status === 'results' && <SearchResultList results={results} query={query} />}
    </div>
  )
}
