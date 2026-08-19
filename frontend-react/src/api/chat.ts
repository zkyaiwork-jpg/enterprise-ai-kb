import apiClient from './client'

export type ChatRequest = {
  question: string
  session_id?: string
}

export type ChatSource = {
  filename: string | null
  folder_name?: string | null
  file_type?: string | null
  chunk_index: number | null
  content: string | null
  distance: number | null
  metadata?: Record<string, unknown> | null
  embedding_model?: string | null
  vector_database?: string | null
}

export type ChatResponse = {
  id: number
  session_id: string
  answer: string
  question: string
  sources: ChatSource[]
  created_at: string
}

export type ChatHistoryRecord = {
  id: number
  question: string
  answer: string
  sources: ChatSource[]
  created_at: string
}

export type ChatHistorySession = {
  session_id: string
  title: string
  created_at: string
  updated_at: string
  messages: ChatHistoryRecord[]
}

export type ChatHistoryResponse = {
  sessions: ChatHistorySession[]
}

export async function sendMessage(question: string, sessionId?: string): Promise<ChatResponse> {
  const payload: ChatRequest = { question }
  if (sessionId) payload.session_id = sessionId
  const response = await apiClient.post<ChatResponse>('/chat', payload)
  return response.data
}

export async function getChatHistory(): Promise<ChatHistoryResponse> {
  const response = await apiClient.get<ChatHistoryResponse>('/chat/history')
  return response.data
}
