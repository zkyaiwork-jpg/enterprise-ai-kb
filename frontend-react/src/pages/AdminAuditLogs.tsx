import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { listAuditLogs, type AuditLogItem } from '../api/auditLogs'
import { ApiError } from '../api/client'

const PAGE_SIZE = 20

function auditError(reason: unknown): string {
  if (reason instanceof ApiError && reason.status === 403) return '无权访问审计日志'
  return '审计日志加载失败，请稍后重试'
}

export function AdminAuditLogs() {
  const [items, setItems] = useState<AuditLogItem[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [actionInput, setActionInput] = useState('')
  const [userIdInput, setUserIdInput] = useState('')
  const [resultInput, setResultInput] = useState('')
  const [filters, setFilters] = useState<{ action?: string; userId?: number; result?: 'success' | 'failed' }>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await listAuditLogs({ page, pageSize: PAGE_SIZE, ...filters })
      setItems(response.items)
      setTotal(response.total)
    } catch (reason) {
      setError(auditError(reason))
    } finally {
      setLoading(false)
    }
  }, [filters, page])

  useEffect(() => { void load() }, [load])

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const parsedUserId = userIdInput ? Number(userIdInput) : undefined
    setPage(1)
    setFilters({
      ...(actionInput.trim() ? { action: actionInput.trim() } : {}),
      ...(parsedUserId !== undefined && Number.isInteger(parsedUserId) && parsedUserId > 0 ? { userId: parsedUserId } : {}),
      ...(resultInput === 'success' || resultInput === 'failed' ? { result: resultInput } : {}),
    })
  }

  function clearFilters() {
    setActionInput('')
    setUserIdInput('')
    setResultInput('')
    setPage(1)
    setFilters({})
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">Administration</p>
          <h2 className="text-3xl font-semibold tracking-tight">审计日志</h2>
          <p className="mt-2 text-sm text-on-surface-variant">查看关键安全操作及其执行结果。</p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold shadow-sm hover:bg-slate-50 disabled:opacity-50"
        >
          <span className={`material-symbols-outlined text-lg ${loading ? 'animate-spin' : ''}`}>refresh</span>
          刷新
        </button>
      </header>

      <form onSubmit={applyFilters} className="grid gap-4 rounded-2xl border border-slate-100 bg-white p-5 shadow-ambient md:grid-cols-[1fr_180px_160px_auto] md:items-end">
        <label className="block text-sm font-medium">
          操作类型
          <input value={actionInput} onChange={(event) => setActionInput(event.target.value)} placeholder="例如 document_delete" className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm outline-none focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50" />
        </label>
        <label className="block text-sm font-medium">
          用户ID
          <input type="number" min="1" step="1" value={userIdInput} onChange={(event) => setUserIdInput(event.target.value)} placeholder="可选" className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm outline-none focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50" />
        </label>
        <label className="block text-sm font-medium">
          执行结果
          <select value={resultInput} onChange={(event) => setResultInput(event.target.value)} className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm outline-none focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50">
            <option value="">全部</option>
            <option value="success">成功</option>
            <option value="failed">失败</option>
          </select>
        </label>
        <div className="flex gap-2">
          <button type="submit" className="h-11 rounded-xl bg-primary px-5 text-sm font-semibold text-white hover:bg-blue-700">筛选</button>
          <button type="button" onClick={clearFilters} className="h-11 rounded-xl border border-slate-200 px-4 text-sm font-semibold hover:bg-slate-50">清除</button>
        </div>
      </form>

      {error && <div role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-ambient">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1250px] text-left text-sm">
            <thead className="border-b border-slate-100 bg-slate-50 text-on-surface-variant">
              <tr>{['时间', '操作用户', 'Action', '资源类型', '资源名称', '结果', '安全摘要', 'IP地址'].map((label) => <th key={label} className="px-4 py-4 font-semibold">{label}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => (
                <tr key={item.id} className="align-top hover:bg-slate-50/60">
                  <td className="whitespace-nowrap px-4 py-4 text-on-surface-variant">{new Date(item.created_time).toLocaleString('zh-CN')}</td>
                  <td className="whitespace-nowrap px-4 py-4">{item.user_id === null ? '系统' : `用户ID ${item.user_id}`}</td>
                  <td className="px-4 py-4 font-mono text-xs">{item.action}</td>
                  <td className="px-4 py-4">{item.resource_type}</td>
                  <td className="max-w-[190px] break-words px-4 py-4">{item.resource_name || '-'}</td>
                  <td className="px-4 py-4"><ResultBadge result={item.result} /></td>
                  <td className="max-w-[300px] whitespace-pre-wrap break-words px-4 py-4 text-on-surface-variant">{item.detail || '-'}</td>
                  <td className="whitespace-nowrap px-4 py-4 text-on-surface-variant">{item.ip_address || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {loading && <div className="p-8 text-center text-sm text-on-surface-variant">正在加载审计日志...</div>}
        {!loading && !error && items.length === 0 && <div className="p-8 text-center text-sm text-on-surface-variant">没有符合条件的审计日志</div>}
        <div className="flex flex-col gap-3 border-t border-slate-100 px-5 py-4 text-sm sm:flex-row sm:items-center sm:justify-between">
          <span className="text-on-surface-variant">共 {total} 条记录</span>
          <div className="flex items-center gap-3">
            <button type="button" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)} className="rounded-lg border border-slate-200 px-3 py-1.5 disabled:opacity-40">上一页</button>
            <span>{page} / {totalPages}</span>
            <button type="button" disabled={page >= totalPages || loading} onClick={() => setPage((value) => value + 1)} className="rounded-lg border border-slate-200 px-3 py-1.5 disabled:opacity-40">下一页</button>
          </div>
        </div>
      </div>
    </section>
  )
}

function ResultBadge({ result }: { result: AuditLogItem['result'] }) {
  return result === 'success'
    ? <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">成功</span>
    : <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700">失败</span>
}
