import { http } from './http'

export type AuditResult = 'success' | 'failed'

export interface AuditLogItem {
  id: number
  user_id: number | null
  action: string
  resource_type: string
  resource_id: string | null
  resource_name: string | null
  result: AuditResult
  detail: string | null
  ip_address: string | null
  created_time: string
}

export interface AuditLogResponse {
  items: AuditLogItem[]
  page: number
  page_size: number
  total: number
}

export async function listAuditLogs(params: { page: number; page_size: number; action?: string; user_id?: number; result?: AuditResult }): Promise<AuditLogResponse> {
  const { data } = await http.get<AuditLogResponse>('/audit-logs', { params })
  return data
}
