import { http } from './http'

export interface ChatSource {
  filename?: string | null
  folder_name?: string | null
  file_type?: string | null
  chunk_index?: number | null
  content?: string | null
  distance?: number | null
  metadata?: Record<string, unknown> | null
}

export interface ChatRequest {
  question: string
  conversation_id?: number
}

export interface ChatResponse {
  id: number
  conversation_id: number
  session_id: string
  answer: string
  question: string
  sources: ChatSource[]
  created_at: string
}

export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>('/chat', payload)
  return data
}
