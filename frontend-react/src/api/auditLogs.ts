import apiClient from './client'

export interface AuditLogItem {
  id: number
  user_id: number | null
  action: string
  resource_type: string
  resource_id: string | null
  resource_name: string | null
  result: 'success' | 'failed'
  detail: string | null
  ip_address: string | null
  created_time: string
}

export interface AuditLogFilters {
  page: number
  pageSize: number
  action?: string
  userId?: number
  result?: 'success' | 'failed'
}

export interface AuditLogListResponse {
  items: AuditLogItem[]
  page: number
  page_size: number
  total: number
}

export async function listAuditLogs(filters: AuditLogFilters): Promise<AuditLogListResponse> {
  const response = await apiClient.get<AuditLogListResponse>('/audit-logs', {
    params: {
      page: filters.page,
      page_size: filters.pageSize,
      ...(filters.action ? { action: filters.action } : {}),
      ...(filters.userId !== undefined ? { user_id: filters.userId } : {}),
      ...(filters.result ? { result: filters.result } : {}),
    },
  })
  return response.data
}
