import { http } from './http'

export interface DashboardStats {
  document_count: number
  chunk_count: number
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await http.get<DashboardStats>('/stats')
  return data
}
