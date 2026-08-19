import { useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { createTeam, listDepartments, listTeams, type DepartmentOption, type TeamOption } from '../api/users'

export function AdminTeams() {
  const [teams, setTeams] = useState<TeamOption[]>([])
  const [departments, setDepartments] = useState<DepartmentOption[]>([])
  const [filter, setFilter] = useState('')
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [description, setDescription] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function load() {
    try {
      const [teamItems, departmentItems] = await Promise.all([listTeams(filter ? Number(filter) : undefined), listDepartments()])
      setTeams(teamItems); setDepartments(departmentItems); setError('')
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 403 ? '无权访问小组管理' : '小组列表加载失败')
    }
  }
  useEffect(() => { void load() }, [filter])

  async function submit(event: FormEvent) {
    event.preventDefault(); setError('')
    try {
      await createTeam(name.trim(), Number(departmentId), description)
      setOpen(false); setName(''); setDescription(''); setMessage('小组创建成功'); await load()
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 409 ? '该部门已存在同名小组' : '小组创建失败')
    }
  }

  return <section className="space-y-6">
    <header className="flex items-end justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Administration</p><h2 className="mt-2 text-3xl font-semibold">小组管理</h2><p className="mt-2 text-sm text-on-surface-variant">在部门下创建和查看业务小组。</p></div><button onClick={() => setOpen(true)} className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white">创建小组</button></header>
    {message && <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{message}</div>}{error && <div role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
    <select value={filter} onChange={(e) => setFilter(e.target.value)} className="rounded-xl border border-slate-200 px-4 py-2"><option value="">全部部门</option>{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select>
    <div className="overflow-hidden rounded-2xl bg-white shadow-ambient"><table className="w-full text-left text-sm"><thead className="bg-slate-50"><tr>{['小组ID','小组名称','所属部门','描述'].map(x => <th key={x} className="px-5 py-4">{x}</th>)}</tr></thead><tbody>{teams.map(t => <tr key={t.id} className="border-t border-slate-100"><td className="px-5 py-4">{t.id}</td><td className="px-5 py-4 font-medium">{t.name}</td><td className="px-5 py-4">{t.department?.name ?? t.department_id}</td><td className="px-5 py-4">{t.description || '-'}</td></tr>)}</tbody></table></div>
    {open && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 p-4"><form onSubmit={submit} className="w-full max-w-lg rounded-2xl bg-white p-6"><h3 className="text-xl font-semibold">创建小组</h3><input required value={name} onChange={e => setName(e.target.value)} placeholder="小组名称" className="mt-5 w-full rounded-xl border p-3"/><select required value={departmentId} onChange={e => setDepartmentId(e.target.value)} className="mt-4 w-full rounded-xl border p-3"><option value="">选择部门</option>{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select><textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="描述（可选）" className="mt-4 w-full rounded-xl border p-3"/><div className="mt-5 flex justify-end gap-3"><button type="button" onClick={() => setOpen(false)} className="rounded-xl border px-5 py-2.5">取消</button><button className="rounded-xl bg-primary px-5 py-2.5 text-white">创建</button></div></form></div>}
  </section>
}
