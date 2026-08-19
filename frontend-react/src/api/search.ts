import apiClient from './client'

export type SearchDocumentsParams = {
  query: string
  limit?: number
  folder_id?: number
  file_type?: string
}

export type SearchDocumentResult = {
  filename: string | null
  folder_id: number | null
  folder_name: string | null
  file_type: string | null
  content: string
  chunk_index: number | null
  distance: number | null
  metadata: Record<string, unknown> | null
  embedding_model: string | null
  vector_database: string | null
}

export type SearchDocumentsResponse = {
  results: SearchDocumentResult[]
}

export async function searchDocuments(params: SearchDocumentsParams): Promise<SearchDocumentsResponse> {
  const response = await apiClient.get<SearchDocumentsResponse>('/search', { params })
  return response.data
}
