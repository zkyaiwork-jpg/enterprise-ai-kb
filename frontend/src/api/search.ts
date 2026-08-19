import { http } from './http'

export interface KnowledgeSearchResult {
  content: string
  distance: number
  filename?: string | null
  folder_id?: number | null
  folder_name?: string | null
  file_type?: string | null
  chunk_index?: number | null
  metadata?: Record<string, unknown> | null
  rerank_score?: number
  embedding_model?: string
  vector_database?: string
}

export interface KnowledgeSearchResponse {
  results: KnowledgeSearchResult[]
}

export interface KnowledgeSearchParams {
  query: string
  limit?: number
  folder_id?: number
  file_type?: string
}

export async function searchKnowledge(params: KnowledgeSearchParams): Promise<KnowledgeSearchResponse> {
  const { data } = await http.get<KnowledgeSearchResponse>('/search', { params })
  return data
}
