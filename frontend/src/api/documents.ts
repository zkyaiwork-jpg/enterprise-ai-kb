import { http } from './http'

export type DocumentVisibility = 'private' | 'team' | 'department' | 'company'

export interface DocumentItem {
  document_id: number
  filename: string
  file_type?: string
  file_size?: number
  category?: string | null
  folder_id?: number | null
  folder_name?: string | null
  uploader_id?: number | null
  department_id?: number | null
  team_id?: number | null
  visibility: DocumentVisibility
  status?: string
  chunk_count?: number
  uploaded_at?: string
  size?: number
  type?: string
}

export interface TeamOption {
  id: number
  name: string
  department_id: number
  department: { id: number; name: string }
}

export interface FolderOption {
  id: number
  name: string
  created_at: string
}

export interface DocumentUpdatePayload {
  visibility: DocumentVisibility
  team_id?: number
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const { data } = await http.get<{ documents: DocumentItem[] }>('/documents')
  return data.documents
}

export async function uploadDocument(payload: FormData): Promise<void> {
  await http.post('/upload', payload, { headers: { 'Content-Type': undefined } })
}

export async function updateDocument(documentId: number, payload: DocumentUpdatePayload): Promise<void> {
  await http.patch(`/documents/${documentId}`, payload)
}

export async function deleteDocument(filename: string): Promise<void> {
  await http.delete(`/documents/${encodeURIComponent(filename)}`)
}

export async function listAvailableUploadTeams(): Promise<TeamOption[]> {
  const { data } = await http.get<{ items: TeamOption[] }>('/teams/available-for-upload')
  return data.items
}

export async function listFolders(): Promise<FolderOption[]> {
  const { data } = await http.get<FolderOption[]>('/folders')
  return data
}
