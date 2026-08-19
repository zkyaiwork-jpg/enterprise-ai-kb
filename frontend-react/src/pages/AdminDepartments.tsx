import { useEffect, useState, type FormEvent } from 'react'

import { ApiError } from '../api/client'
import {
  createDepartment,
  listDepartments,
  type DepartmentOption,
} from '../api/users'

function departmentError(reason: unknown): string {
  if (reason instanceof ApiError && reason.status === 403) {
    return '无权访问部门管理'
  }
  if (reason instanceof ApiError && reason.status === 409) {
    return '部门名称已存在，请使用其他名称'
  }
  return '操作失败，请稍后重试'
}

export function AdminDepartments() {
  const [departments, setDepartments] = useState<DepartmentOption[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)

  async function loadDepartments() {
    setLoading(true)
    setError('')
    try {
      setDepartments(await listDepartments())
    } catch (reason) {
      setError(departmentError(reason))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDepartments()
  }, [])

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
            Administration
          </p>
          <h2 className="text-3xl font-semibold tracking-tight">部门管理</h2>
          <p className="mt-2 text-sm text-on-surface-variant">
            查看企业部门并创建新的员工归属部门。
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setMessage('')
            setDialogOpen(true)
          }}
          disabled={Boolean(error) && departments.length === 0}
          className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          创建部门
        </button>
      </header>

      {message && (
        <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {message}
        </div>
      )}
      {error && (
        <div role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-ambient">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-slate-100 bg-slate-50 text-on-surface-variant">
              <tr>
                <th className="px-5 py-4 font-semibold">部门ID</th>
                <th className="px-5 py-4 font-semibold">部门名称</th>
                <th className="px-5 py-4 font-semibold">描述</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {departments.map((department) => (
                <tr key={department.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-4 text-on-surface-variant">{department.id}</td>
                  <td className="px-5 py-4 font-medium">{department.name}</td>
                  <td className="px-5 py-4 text-on-surface-variant">
                    {department.description || '暂无描述'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {loading && (
          <div className="p-8 text-center text-sm text-on-surface-variant">正在加载部门...</div>
        )}
        {!loading && !error && departments.length === 0 && (
          <div className="p-8 text-center text-sm text-on-surface-variant">暂无部门</div>
        )}
        <div className="border-t border-slate-100 px-5 py-4 text-sm text-on-surface-variant">
          共 {departments.length} 个部门 · 删除和编辑功能后续支持
        </div>
      </div>

      {dialogOpen && (
        <CreateDepartmentDialog
          onClose={() => setDialogOpen(false)}
          onSuccess={async () => {
            setDialogOpen(false)
            setMessage('部门创建成功')
            await loadDepartments()
          }}
        />
      )}
    </section>
  )
}

function CreateDepartmentDialog({
  onClose,
  onSuccess,
}: {
  onClose: () => void
  onSuccess: () => Promise<void>
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedName = name.trim()
    if (!normalizedName) {
      setError('部门名称不能为空')
      return
    }

    setSaving(true)
    setError('')
    try {
      await createDepartment(normalizedName, description)
      await onSuccess()
    } catch (reason) {
      setError(departmentError(reason))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 p-4 backdrop-blur-[2px]"
      onMouseDown={(event) => {
        if (!saving && event.target === event.currentTarget) onClose()
      }}
    >
      <form
        onSubmit={submit}
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-department-title"
        className="w-full max-w-lg rounded-2xl border border-slate-100 bg-white p-6 shadow-2xl"
      >
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 id="create-department-title" className="text-xl font-semibold">创建部门</h3>
            <p className="mt-1 text-sm text-on-surface-variant">新部门将可用于员工账号的部门归属。</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            aria-label="关闭"
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 disabled:opacity-50"
          >
            ×
          </button>
        </div>

        <label className="mt-6 block text-sm font-medium">
          部门名称
          <input
            autoFocus
            required
            maxLength={100}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="请输入部门名称"
            className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm outline-none transition focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50"
          />
        </label>
        <label className="mt-4 block text-sm font-medium">
          描述
          <textarea
            rows={4}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="选填，简要说明部门职责"
            className="mt-2 w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50"
          />
        </label>

        {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={saving || !name.trim()}
            className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? '创建中...' : '创建'}
          </button>
        </div>
      </form>
    </div>
  )
}
