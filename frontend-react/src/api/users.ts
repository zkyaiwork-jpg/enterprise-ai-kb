import apiClient from './client'

export interface RoleOption { id: number; name: string; description?: string | null }
export interface DepartmentOption {
  id: number
  name: string
  description?: string | null
  created_time?: string
}
export interface TeamOption {
  id: number
  name: string
  department_id: number
  department?: DepartmentOption
  description?: string | null
  created_time?: string
}
export interface ManagedUser {
  id: number
  username: string
  real_name: string
  role: RoleOption | null
  department: DepartmentOption | null
  team: TeamOption | null
  status: 'active' | 'inactive'
  created_time: string
}

export interface UserListResponse {
  items: ManagedUser[]
  page: number
  page_size: number
  total: number
}

export interface CreateUserPayload {
  username: string
  password: string
  real_name: string
  role_id: number
  department_id: number | null
  team_id: number | null
}

export interface UpdateUserPayload {
  real_name?: string
  role_id?: number
  department_id?: number | null
  team_id?: number | null
  status?: 'active' | 'inactive'
}

export async function listUsers(page: number, pageSize: number): Promise<UserListResponse> {
  const response = await apiClient.get<UserListResponse>('/users', { params: { page, page_size: pageSize } })
  return response.data
}

export async function listRoles(): Promise<RoleOption[]> {
  const response = await apiClient.get<{ items: RoleOption[] }>('/roles')
  return response.data.items
}

export async function listDepartments(): Promise<DepartmentOption[]> {
  const response = await apiClient.get<{ items: DepartmentOption[] }>('/departments')
  return response.data.items
}

export async function createDepartment(name: string, description: string): Promise<DepartmentOption> {
  const response = await apiClient.post<DepartmentOption>('/departments', {
    name,
    description: description.trim() || null,
  })
  return response.data
}

export async function listTeams(departmentId?: number): Promise<TeamOption[]> {
  const response = await apiClient.get<{ items: TeamOption[] }>('/teams', { params: departmentId ? { department_id: departmentId } : {} })
  return response.data.items
}

export async function listUploadTeams(): Promise<TeamOption[]> {
  const response = await apiClient.get<{ items: TeamOption[] }>('/teams/available-for-upload')
  return response.data.items
}

export async function createTeam(name: string, departmentId: number, description: string): Promise<TeamOption> {
  const response = await apiClient.post<TeamOption>('/teams', { name, department_id: departmentId, description: description.trim() || null })
  return response.data
}

export async function createUser(payload: CreateUserPayload): Promise<ManagedUser> {
  const response = await apiClient.post<ManagedUser>('/users', payload)
  return response.data
}

export async function updateUser(userId: number, payload: UpdateUserPayload): Promise<ManagedUser> {
  const response = await apiClient.patch<ManagedUser>(`/users/${userId}`, payload)
  return response.data
}

export async function resetUserPassword(userId: number, newPassword: string): Promise<void> {
  await apiClient.post(`/users/${userId}/reset-password`, { new_password: newPassword })
}
