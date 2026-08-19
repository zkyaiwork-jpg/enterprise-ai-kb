import apiClient from './client'

export type DocumentVisibility = 'private' | 'team' | 'department' | 'company'

export type DocumentMetadata = {
  document_id: string | null
  filename: string
  file_type: string | null
  file_size: number | null
  category: string | null
  folder_id: number | null
  folder_name: string | null
  status: string | null
  chunk_count: number | null
  uploaded_at: string | null
  uploader_id: number | null
  department_id: number | null
  team_id: number | null
  visibility: DocumentVisibility | null
  // 后端保留的兼容字段。
  size?: number | null
  type?: string | null
}

export type DocumentsResponse = {
  documents: DocumentMetadata[]
}

export type UploadDocumentResponse = {
  filename: string
  path: string | null
  content: string | null
  chunks: unknown[] | number | null
  vector_count: number | null
  message: string | null
  document_id: string | null
  category: string | null
  folder_id: number | null
  folder_name: string | null
  status: string | null
  file_type: string | null
  file_size: number | null
  uploaded_at: string | null
  uploader_id?: number | null
  department_id?: number | null
  team_id?: number | null
  visibility?: DocumentVisibility | null
}

export type DeleteDocumentResponse = {
  filename?: string
  message?: string
  deleted?: boolean
}

export async function getDocuments(): Promise<DocumentsResponse> {
  const response = await apiClient.get<DocumentsResponse>('/documents')
  return response.data
}

export async function uploadDocument(file: File, folderId: number | undefined, visibility: DocumentVisibility = 'private', teamId?: number): Promise<UploadDocumentResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (folderId !== undefined) formData.append('folder_id', String(folderId))
  formData.append('visibility', visibility)
  if (teamId !== undefined) formData.append('team_id', String(teamId))
  const response = await apiClient.post<UploadDocumentResponse>('/upload', formData)
  return response.data
}

export type UpdateDocumentResponse = {
  document_id: number
  filename: string
  original_name: string
  visibility: DocumentVisibility
  updated_time: string
}

export async function updateDocument(
  documentId: number,
  payload: { original_name?: string; visibility?: DocumentVisibility; team_id?: number },
): Promise<UpdateDocumentResponse> {
  const response = await apiClient.patch<UpdateDocumentResponse>(`/documents/${documentId}`, payload)
  return response.data
}

export async function deleteDocument(filename: string): Promise<DeleteDocumentResponse> {
  const response = await apiClient.delete<DeleteDocumentResponse>(`/documents/${encodeURIComponent(filename)}`)
  return response.data
}
