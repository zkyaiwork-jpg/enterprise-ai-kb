import apiClient from './client'

export type Folder = {
  id: number
  name: string
  created_at: string
}

export async function getFolders(): Promise<Folder[]> {
  const response = await apiClient.get<Folder[]>('/folders')
  return response.data
}

export async function createFolder(name: string): Promise<Folder> {
  const response = await apiClient.post<Folder>('/folders', { name })
  return response.data
}
