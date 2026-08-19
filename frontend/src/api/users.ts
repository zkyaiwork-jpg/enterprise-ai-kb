import { http } from './http'

export type UserStatus = 'active' | 'inactive'

export interface NamedOption {
  id: number
  name: string
  description?: string | null
}

export interface TeamOption extends NamedOption {
  department_id: number
  department: NamedOption
}

export interface ManagedUser {
  id: number
  username: string
  real_name: string
  role: NamedOption | null
  department: NamedOption | null
  team: NamedOption | null
  status: UserStatus
  created_time: string
}

export interface UserListParams {
  page: number
  page_size: number
  status?: UserStatus
  department_id?: number
  role_id?: number
}

export interface UserListResponse {
  items: ManagedUser[]
  page: number
  page_size: number
  total: number
}

export interface UserCreatePayload {
  username: string
  password: string
  role_id: number
  department_id: number | null
  team_id: number | null
}

export interface UserUpdatePayload {
  username: string
  role_id: number
  department_id: number | null
  team_id: number | null
}

export async function listUsers(params: UserListParams): Promise<UserListResponse> {
  const { data } = await http.get<UserListResponse>('/users', { params })
  return data
}

export async function createUser(payload: UserCreatePayload): Promise<ManagedUser> {
  const { data } = await http.post<ManagedUser>('/users', payload)
  return data
}

export async function updateUser(userId: number, payload: Partial<UserUpdatePayload> & { status?: UserStatus }): Promise<ManagedUser> {
  const { data } = await http.patch<ManagedUser>(`/users/${userId}`, payload)
  return data
}

export async function resetUserPassword(userId: number, newPassword: string): Promise<void> {
  await http.post(`/users/${userId}/reset-password`, { new_password: newPassword })
}

export async function deleteUser(userId: number): Promise<void> {
  await http.delete(`/users/${userId}`)
}

export async function listRoles(): Promise<NamedOption[]> {
  const { data } = await http.get<{ items: NamedOption[] }>('/roles')
  return data.items
}

export async function listDepartments(): Promise<NamedOption[]> {
  const { data } = await http.get<{ items: NamedOption[] }>('/departments')
  return data.items
}

export async function listTeams(): Promise<TeamOption[]> {
  const { data } = await http.get<{ items: TeamOption[] }>('/teams')
  return data.items
}
