import apiClient from './client'

export type HealthStatus = {
  status: 'healthy' | 'degraded'
  api: 'ok' | 'error'
  vector_db: 'ok' | 'error'
  chat_db: 'ok' | 'error'
  ai: 'configured' | 'not_configured'
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await apiClient.get<HealthStatus>('/health')
  return response.data
}
