const roleLabels: Record<string, string> = {
  admin: '管理员',
  manager: '经理',
  leader: '组长',
  employee: '员工',
}

export function getUserRoleLabel(value?: string | null): string {
  if (!value) return '未分配'
  return roleLabels[value.toLowerCase()] || value
}
