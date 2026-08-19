import { http } from './http'

export interface DepartmentItem {
  id: number
  name: string
  description: string | null
  created_time: string
}

export interface TeamItem {
  id: number
  name: string
  department_id: number
  department: { id: number; name: string }
  description: string | null
  created_time: string
}

export async function listDepartments(): Promise<DepartmentItem[]> {
  const { data } = await http.get<{ items: DepartmentItem[] }>('/departments')
  return data.items
}

export async function createDepartment(payload: { name: string; description: string | null }): Promise<DepartmentItem> {
  const { data } = await http.post<DepartmentItem>('/departments', payload)
  return data
}

export async function listTeams(departmentId?: number): Promise<TeamItem[]> {
  const { data } = await http.get<{ items: TeamItem[] }>('/teams', { params: { department_id: departmentId } })
  return data.items
}

export async function createTeam(payload: { name: string; department_id: number; description: string | null }): Promise<TeamItem> {
  const { data } = await http.post<TeamItem>('/teams', payload)
  return data
}
