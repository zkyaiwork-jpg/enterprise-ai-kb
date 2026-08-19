import { useEffect, useMemo, useState } from 'react'

import { getDocuments, type DocumentMetadata } from '../api/documents'
import { API_BASE_URL, ApiError } from '../api/client'
import { getStats, type SystemStats } from '../api/stats'
import { getHealth, type HealthStatus } from '../api/health'
import { HeroCard } from '../components/dashboard/HeroCard'
import { QuickActions } from '../components/dashboard/QuickActions'
import { RecentDocuments, type RecentDocument } from '../components/dashboard/RecentDocuments'
import { StatCard } from '../components/dashboard/StatCard'
import { useDesktopUser } from '../hooks/useDesktopUser'

export function Dashboard() {
  const { userName } = useDesktopUser()
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [documents, setDocuments] = useState<DocumentMetadata[]>([])
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [statsError, setStatsError] = useState(false)
  const [documentsError, setDocumentsError] = useState(false)
  const [serviceStatus, setServiceStatus] = useState<'starting' | 'healthy' | 'error'>('starting')

  useEffect(() => {
    let active = true
    let pollTimer: ReturnType<typeof setTimeout> | undefined
    const maxHealthAttempts = 120

    async function loadDashboardData() {
      const [statsResult, documentsResult] = await Promise.allSettled([
        getStats(),
        getDocuments(),
      ])
      if (!active) return

      if (statsResult.status === 'fulfilled') setStats(statsResult.value)
      else {
        const reason = statsResult.reason
        console.error('Dashboard stats request failed', {
          url: `${API_BASE_URL}/stats`,
          message: reason instanceof Error ? reason.message : String(reason),
          status: reason instanceof ApiError ? reason.status ?? null : null,
        })
        setStatsError(true)
      }

      if (documentsResult.status === 'fulfilled') setDocuments(documentsResult.value.documents ?? [])
      else {
        const reason = documentsResult.reason
        console.error('Dashboard documents request failed', {
          url: `${API_BASE_URL}/documents`,
          message: reason instanceof Error ? reason.message : String(reason),
          status: reason instanceof ApiError ? reason.status ?? null : null,
        })
        setDocumentsError(true)
      }

      setLoading(false)
    }

    async function pollHealth(attempt: number) {
      try {
        const result = await getHealth()
        if (!active) return
        setHealth(result)
        if (result.status === 'healthy') {
          setServiceStatus('healthy')
          await loadDashboardData()
          return
        }
      } catch (reason) {
        if (!active) return
        if (attempt === maxHealthAttempts - 1) {
          console.error('Dashboard health polling failed', {
            url: `${API_BASE_URL}/health`,
            message: reason instanceof Error ? reason.message : String(reason),
            status: reason instanceof ApiError ? reason.status ?? null : null,
          })
        }
      }

      if (attempt >= maxHealthAttempts - 1) {
        setServiceStatus('error')
        setLoading(false)
        return
      }
      pollTimer = setTimeout(() => { void pollHealth(attempt + 1) }, 1_000)
    }

    void pollHealth(0)
    return () => {
      active = false
      if (pollTimer) clearTimeout(pollTimer)
    }
  }, [])

  const recentDocuments = useMemo<RecentDocument[]>(() => [...documents]
    .sort((a, b) => {
      const aTime = a.uploaded_at ? new Date(a.uploaded_at).getTime() : 0
      const bTime = b.uploaded_at ? new Date(b.uploaded_at).getTime() : 0
      return bTime - aTime
    })
    .slice(0, 5)
    .map((document, index) => ({
      id: document.document_id || `${document.filename}-${index}`,
      name: document.filename,
      category: document.folder_name || '未分配文件夹',
      chunks: document.chunk_count,
      type: (document.file_type || document.type || '未知').replace('.', '').toUpperCase(),
      status: document.status || '',
    })), [documents])

  const statCards = [
    { label: '文档总数', value: loading ? '—' : statsError ? '不可用' : String(stats?.document_count ?? 0), icon: 'folder_open' },
    { label: '知识片段', value: loading ? '—' : statsError ? '不可用' : String(stats?.chunk_count ?? 0), icon: 'dataset', iconClassName: 'bg-cyan-50 text-cyan-700' },
    { label: 'AI问答', value: loading ? '—' : statsError ? '不可用' : String(stats?.question_count ?? 0), icon: 'forum', iconClassName: 'bg-violet-50 text-violet-600' },
    { label: 'AI服务状态', value: serviceStatus === 'starting' ? 'AI服务启动中' : serviceStatus === 'error' ? '启动失败' : health?.ai === 'configured' ? '正常' : '未配置', icon: 'online_prediction', iconClassName: serviceStatus === 'healthy' && health?.ai === 'configured' ? 'bg-emerald-50 text-emerald-700' : serviceStatus === 'starting' ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700', status: serviceStatus === 'healthy' ? health?.ai === 'configured' ? 'online' as const : 'offline' as const : serviceStatus === 'error' ? 'offline' as const : undefined },
  ]

  return (
    <div className="space-y-6 pb-4">
      <HeroCard userName={userName || '用户'} />

      {serviceStatus === 'error' && <div className="flex items-center gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert"><span className="material-symbols-outlined text-[19px]">error</span>AI服务启动失败，请检查日志。</div>}
      {statsError && <div className="flex items-center gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert"><span className="material-symbols-outlined text-[19px]">error</span>工作台统计加载失败。</div>}

      <section aria-label="工作台统计" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {statCards.map((stat) => <StatCard key={stat.label} {...stat} />)}
      </section>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(300px,1fr)]">
        <RecentDocuments documents={recentDocuments} loading={loading} error={documentsError} />
        <QuickActions />
      </div>
    </div>
  )
}
