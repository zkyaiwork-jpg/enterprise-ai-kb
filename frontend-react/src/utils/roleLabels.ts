export const ROLE_LABELS = {
  admin: '管理员',
  manager: '部门主管',
  leader: '组长',
  employee: '普通员工',
} as const

export type BuiltInRoleCode = keyof typeof ROLE_LABELS

export function getRoleLabel(roleCode: string | null | undefined): string {
  if (!roleCode) return '—'
  return ROLE_LABELS[roleCode as BuiltInRoleCode] ?? roleCode
}
