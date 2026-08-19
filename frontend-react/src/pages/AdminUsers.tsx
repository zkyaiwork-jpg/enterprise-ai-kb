import { useEffect, useState, type FormEvent, type ReactNode } from 'react'

import { ApiError } from '../api/client'
import {
  createUser,
  listDepartments,
  listRoles,
  listTeams,
  listUsers,
  resetUserPassword,
  updateUser,
  type DepartmentOption,
  type ManagedUser,
  type RoleOption,
  type TeamOption,
} from '../api/users'
import { getRoleLabel } from '../utils/roleLabels'

const PAGE_SIZE = 10

function errorMessage(reason: unknown): string {
  if (reason instanceof ApiError && reason.status === 403) return '无权访问用户管理'
  if (reason instanceof ApiError && reason.status === 409) return reason.message
  return '操作失败，请稍后重试'
}

function Dialog({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 p-4 backdrop-blur-[2px]" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section role="dialog" aria-modal="true" aria-label={title} className="max-h-[90vh] w-full max-w-lg overflow-auto rounded-2xl border border-slate-100 bg-white p-6 shadow-2xl">
        <div className="flex items-center justify-between gap-4">
          <h3 className="text-xl font-semibold">{title}</h3>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="关闭">×</button>
        </div>
        {children}
      </section>
    </div>
  )
}

const inputClass = 'mt-2 h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm outline-none transition focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50'

export function AdminUsers() {
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [roles, setRoles] = useState<RoleOption[]>([])
  const [departments, setDepartments] = useState<DepartmentOption[]>([])
  const [teams, setTeams] = useState<TeamOption[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState<ManagedUser | null>(null)
  const [resetting, setResetting] = useState<ManagedUser | null>(null)
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  async function load(targetPage = page) {
    setLoading(true)
    setError('')
    try {
      const [userResult, roleResult, departmentResult, teamResult] = await Promise.all([
        listUsers(targetPage, PAGE_SIZE), listRoles(), listDepartments(), listTeams(),
      ])
      setUsers(userResult.items)
      setTotal(userResult.total)
      setRoles(roleResult)
      setDepartments(departmentResult)
      setTeams(teamResult)
    } catch (reason) {
      setError(errorMessage(reason))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load(page) }, [page])

  async function toggleStatus(user: ManagedUser) {
    setError('')
    setMessage('')
    try {
      await updateUser(user.id, { status: user.status === 'active' ? 'inactive' : 'active' })
      setMessage(user.status === 'active' ? '用户已停用' : '用户已启用')
      await load()
    } catch (reason) {
      setError(errorMessage(reason))
    }
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">Administration</p>
          <h2 className="text-3xl font-semibold tracking-tight">用户管理</h2>
          <p className="mt-2 text-sm text-on-surface-variant">创建员工账号并维护角色、部门与账号状态。</p>
        </div>
        <button type="button" onClick={() => setCreateOpen(true)} disabled={Boolean(error) && !users.length} className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50">创建用户</button>
      </header>

      {message && <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{message}</div>}
      {error && <div role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-ambient">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b border-slate-100 bg-slate-50 text-on-surface-variant">
              <tr>{['用户名', '姓名', '角色', '部门', '状态', '创建时间', '操作'].map((label) => <th key={label} className="px-5 py-4 font-semibold">{label}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-4 font-medium">{user.username}</td>
                  <td className="px-5 py-4">{user.real_name}</td>
                  <td className="px-5 py-4">{getRoleLabel(user.role?.name)}</td>
                  <td className="px-5 py-4">{user.department?.name ?? '未分配'}</td>
                  <td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${user.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>{user.status === 'active' ? '正常' : '已停用'}</span></td>
                  <td className="px-5 py-4 text-on-surface-variant">{new Date(user.created_time).toLocaleString('zh-CN')}</td>
                  <td className="px-5 py-4"><div className="flex gap-3 whitespace-nowrap">
                    <button type="button" onClick={() => setEditing(user)} className="font-medium text-primary hover:underline">编辑</button>
                    <button type="button" onClick={() => void toggleStatus(user)} className="font-medium text-primary hover:underline">{user.status === 'active' ? '停用' : '启用'}</button>
                    <button type="button" onClick={() => setResetting(user)} className="font-medium text-primary hover:underline">重置密码</button>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {loading && <div className="p-8 text-center text-sm text-on-surface-variant">正在加载用户...</div>}
        {!loading && !error && users.length === 0 && <div className="p-8 text-center text-sm text-on-surface-variant">暂无用户</div>}
        <div className="flex items-center justify-between border-t border-slate-100 px-5 py-4 text-sm">
          <span className="text-on-surface-variant">共 {total} 位用户</span>
          <div className="flex items-center gap-3">
            <button type="button" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)} className="rounded-lg border border-slate-200 px-3 py-1.5 disabled:opacity-40">上一页</button>
            <span>{page} / {totalPages}</span>
            <button type="button" disabled={page >= totalPages || loading} onClick={() => setPage((value) => value + 1)} className="rounded-lg border border-slate-200 px-3 py-1.5 disabled:opacity-40">下一页</button>
          </div>
        </div>
      </div>

      {createOpen && <CreateUserDialog roles={roles} departments={departments} teams={teams} onClose={() => setCreateOpen(false)} onSuccess={async () => { setCreateOpen(false); setMessage('用户创建成功'); await load() }} />}
      {editing && <EditUserDialog user={editing} roles={roles} departments={departments} teams={teams} onClose={() => setEditing(null)} onSuccess={async () => { setEditing(null); setMessage('用户信息已更新'); await load() }} />}
      {resetting && <ResetPasswordDialog user={resetting} onClose={() => setResetting(null)} onSuccess={() => { setResetting(null); setMessage('密码重置成功，该用户原登录状态已失效') }} />}
    </section>
  )
}

function CreateUserDialog({ roles, departments, teams, onClose, onSuccess }: { roles: RoleOption[]; departments: DepartmentOption[]; teams: TeamOption[]; onClose: () => void; onSuccess: () => Promise<void> }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [realName, setRealName] = useState('')
  const [roleId, setRoleId] = useState(roles[0]?.id ?? 0)
  const [departmentId, setDepartmentId] = useState('')
  const [teamId, setTeamId] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError('')
    try {
      await createUser({ username: username.trim(), password, real_name: realName.trim(), role_id: roleId, department_id: departmentId ? Number(departmentId) : null, team_id: teamId ? Number(teamId) : null })
      setPassword(''); await onSuccess()
    } catch (reason) { setPassword(''); setError(errorMessage(reason)) } finally { setSaving(false) }
  }
  return <Dialog title="创建用户" onClose={onClose}><form onSubmit={submit} className="mt-6 grid gap-4 sm:grid-cols-2">
    <Field label="用户名"><input required minLength={3} value={username} onChange={(e) => setUsername(e.target.value)} className={inputClass} autoComplete="off" /></Field>
    <Field label="姓名"><input required value={realName} onChange={(e) => setRealName(e.target.value)} className={inputClass} /></Field>
    <Field label="初始密码"><input required minLength={8} maxLength={72} type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputClass} autoComplete="new-password" /></Field>
    <Field label="角色"><select required value={roleId} onChange={(e) => setRoleId(Number(e.target.value))} className={inputClass}>{roles.map((role) => <option key={role.id} value={role.id}>{getRoleLabel(role.name)}</option>)}</select></Field>
    <Field label="部门"><select value={departmentId} onChange={(e) => { setDepartmentId(e.target.value); setTeamId('') }} className={inputClass}><option value="">未分配</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
    <Field label="小组"><select value={teamId} onChange={(e) => setTeamId(e.target.value)} className={inputClass}><option value="">未分配</option>{teams.filter(item => String(item.department_id) === departmentId).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
    {error && <p role="alert" className="sm:col-span-2 text-sm text-red-700">{error}</p>}
    <Actions saving={saving} disabled={!roleId} onCancel={onClose} label="创建" />
  </form></Dialog>
}

function EditUserDialog({ user, roles, departments, teams, onClose, onSuccess }: { user: ManagedUser; roles: RoleOption[]; departments: DepartmentOption[]; teams: TeamOption[]; onClose: () => void; onSuccess: () => Promise<void> }) {
  const [realName, setRealName] = useState(user.real_name)
  const [roleId, setRoleId] = useState(user.role?.id ?? 0)
  const [departmentId, setDepartmentId] = useState(user.department?.id ? String(user.department.id) : '')
  const [teamId, setTeamId] = useState(user.team?.id ? String(user.team.id) : '')
  const [status, setStatus] = useState(user.status)
  const [error, setError] = useState(''); const [saving, setSaving] = useState(false)
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); setError(''); try { await updateUser(user.id, { real_name: realName.trim(), role_id: roleId, department_id: departmentId ? Number(departmentId) : null, team_id: teamId ? Number(teamId) : null, status }); await onSuccess() } catch (reason) { setError(errorMessage(reason)) } finally { setSaving(false) } }
  return <Dialog title={`编辑用户：${user.username}`} onClose={onClose}><form onSubmit={submit} className="mt-6 grid gap-4 sm:grid-cols-2">
    <Field label="姓名"><input required value={realName} onChange={(e) => setRealName(e.target.value)} className={inputClass} /></Field>
    <Field label="角色"><select value={roleId} onChange={(e) => setRoleId(Number(e.target.value))} className={inputClass}>{roles.map((role) => <option key={role.id} value={role.id}>{getRoleLabel(role.name)}</option>)}</select></Field>
    <Field label="部门"><select value={departmentId} onChange={(e) => { setDepartmentId(e.target.value); setTeamId('') }} className={inputClass}><option value="">未分配</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
    <Field label="小组"><select value={teamId} onChange={(e) => setTeamId(e.target.value)} className={inputClass}><option value="">未分配</option>{teams.filter(item => String(item.department_id) === departmentId).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
    <Field label="状态"><select value={status} onChange={(e) => setStatus(e.target.value as 'active' | 'inactive')} className={inputClass}><option value="active">正常</option><option value="inactive">已停用</option></select></Field>
    {error && <p role="alert" className="sm:col-span-2 text-sm text-red-700">{error}</p>}<Actions saving={saving} disabled={!roleId} onCancel={onClose} label="保存" />
  </form></Dialog>
}

function ResetPasswordDialog({ user, onClose, onSuccess }: { user: ManagedUser; onClose: () => void; onSuccess: () => void }) {
  const [password, setPassword] = useState(''); const [error, setError] = useState(''); const [saving, setSaving] = useState(false)
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); setError(''); try { await resetUserPassword(user.id, password); setPassword(''); onSuccess() } catch (reason) { setPassword(''); setError(errorMessage(reason)) } finally { setSaving(false) } }
  return <Dialog title={`重置密码：${user.username}`} onClose={onClose}><form onSubmit={submit} className="mt-6"><Field label="新密码"><input required minLength={8} maxLength={72} type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputClass} autoComplete="new-password" /></Field><p className="mt-2 text-xs text-on-surface-variant">重置后，该用户之前签发的登录凭证将立即失效。</p>{error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}<Actions saving={saving} disabled={!password} onCancel={onClose} label="确认重置" /></form></Dialog>
}

function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="block text-sm font-medium">{label}{children}</label> }
function Actions({ saving, disabled, onCancel, label }: { saving: boolean; disabled: boolean; onCancel: () => void; label: string }) { return <div className="mt-3 flex justify-end gap-3 sm:col-span-2"><button type="button" onClick={onCancel} disabled={saving} className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold">取消</button><button type="submit" disabled={saving || disabled} className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{saving ? '提交中...' : label}</button></div> }
