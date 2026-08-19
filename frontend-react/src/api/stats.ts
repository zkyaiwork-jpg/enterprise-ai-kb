import apiClient from './client'

export type SystemStats = {
  document_count: number
  chunk_count: number
  question_count: number
  ai_status: 'online' | 'offline'
}

export async function getStats(): Promise<SystemStats> {
  const response = await apiClient.get<SystemStats>('/stats')
  return response.data
}
