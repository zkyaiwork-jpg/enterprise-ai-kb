import apiClient from './client'

export interface ModelConfigView {
  provider: string | null
  model_name: string | null
  base_url: string | null
  is_active: boolean
  api_key_configured: boolean
  updated_time: string | null
}

export interface ModelConfigUpdate {
  provider: string
  model_name: string
  base_url: string
  api_key?: string
  is_active: boolean
}

export async function getModelConfig(): Promise<ModelConfigView> {
  const response = await apiClient.get<ModelConfigView>('/model-config')
  return response.data
}

export async function saveModelConfig(payload: ModelConfigUpdate): Promise<ModelConfigView> {
  const response = await apiClient.put<ModelConfigView>('/model-config', payload)
  return response.data
}

export async function testModelConnection(): Promise<void> {
  await apiClient.post('/model-config/test')
}
