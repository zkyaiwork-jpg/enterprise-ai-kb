import apiClient from './client'

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface CurrentUser {
  id: number
  username: string
  real_name: string
  role: { id: number; name: string } | null
  department: { id: number; name: string } | null
  team: { id: number; name: string } | null
  status: string
  permissions: string[]
}

export async function loginRequest(username: string, password: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/login', { username, password })
  return response.data
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const response = await apiClient.get<CurrentUser>('/auth/me')
  return response.data
}
