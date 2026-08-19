import { http } from './http'

export interface LoginPayload {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface NamedEntity {
  id: number
  name: string
}

export interface CurrentUser {
  id: number
  username: string
  real_name: string
  role: NamedEntity | null
  department: NamedEntity | null
  team: NamedEntity | null
  status: string
  permissions: string[]
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const { data } = await http.post<TokenResponse>('/auth/login', payload)
  return data
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const { data } = await http.get<CurrentUser>('/auth/me')
  return data
}
