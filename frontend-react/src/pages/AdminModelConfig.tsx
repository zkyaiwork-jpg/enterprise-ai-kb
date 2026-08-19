import { useEffect, useState, type FormEvent } from 'react'

import { ApiError } from '../api/client'
import {
  getModelConfig,
  saveModelConfig,
  testModelConnection,
  type ModelConfigView,
} from '../api/modelConfig'

const DEFAULT_MODEL = 'deepseek-chat'
const DEFAULT_BASE_URL = 'https://api.deepseek.com/'

function safeError(reason: unknown): string {
  if (reason instanceof ApiError && reason.status === 403) {
    return '无权访问模型配置'
  }
  return '模型配置操作失败，请稍后重试'
}

const inputClass = 'mt-2 h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm outline-none transition focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50'

export function AdminModelConfig() {
  const [config, setConfig] = useState<ModelConfigView | null>(null)
  const [provider] = useState('deepseek')
  const [modelName, setModelName] = useState(DEFAULT_MODEL)
  const [baseUrl, setBaseUrl] = useState(DEFAULT_BASE_URL)
  const [apiKey, setApiKey] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  function applyConfig(value: ModelConfigView) {
    setConfig(value)
    setModelName(value.model_name || DEFAULT_MODEL)
    setBaseUrl(value.base_url || DEFAULT_BASE_URL)
    setIsActive(value.provider ? value.is_active : true)
  }

  useEffect(() => {
    let active = true
    void getModelConfig()
      .then((value) => { if (active) applyConfig(value) })
      .catch((reason) => { if (active) setError(safeError(reason)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    setError('')
    const newApiKey = apiKey.trim()
    try {
      const value = await saveModelConfig({
        provider,
        model_name: modelName.trim(),
        base_url: baseUrl.trim(),
        ...(newApiKey ? { api_key: newApiKey } : {}),
        is_active: isActive,
      })
      applyConfig(value)
      setMessage(newApiKey ? '模型配置已保存，API Key已更新' : '模型配置已保存，现有API Key保持不变')
    } catch (reason) {
      setError(safeError(reason))
    } finally {
      setApiKey('')
      setSaving(false)
    }
  }

  async function testConnection() {
    setTesting(true)
    setMessage('')
    setError('')
    try {
      await testModelConnection()
      setMessage('模型连接成功')
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 403) {
        setError('无权访问模型配置')
      } else {
        setError('模型连接失败')
      }
    } finally {
      setTesting(false)
    }
  }

  const configured = config?.api_key_configured ?? false
  const exists = Boolean(config?.provider)

  return (
    <section className="mx-auto max-w-4xl space-y-6">
      <header>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">Administration</p>
        <h2 className="text-3xl font-semibold tracking-tight">模型配置</h2>
        <p className="mt-2 text-sm text-on-surface-variant">统一管理企业大模型服务配置和调用凭证。</p>
      </header>

      {message && <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{message}</div>}
      {error && <div role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {!loading && !error && !exists && (
        <div className="rounded-2xl border border-blue-100 bg-blue-50 px-6 py-5 text-sm text-blue-800">
          尚未配置企业模型服务，请填写下方配置并提供首次使用的API Key。
        </div>
      )}

      <section className="grid gap-4 sm:grid-cols-3">
        <StatusCard
          icon="power_settings_new"
          label="模型服务"
          value={config?.is_active ? '已启用' : '已停用'}
          active={Boolean(config?.is_active)}
        />
        <StatusCard
          icon="key"
          label="API Key"
          value={configured ? '已配置' : '未配置'}
          active={configured}
        />
        <StatusCard
          icon="update"
          label="最后更新时间"
          value={config?.updated_time ? new Date(config.updated_time).toLocaleString('zh-CN') : '暂无记录'}
          active={Boolean(config?.updated_time)}
        />
      </section>

      <form onSubmit={submit} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-ambient sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold">DeepSeek配置</h3>
            <p className="mt-1 text-sm text-on-surface-variant">API Key不会被读取或回显；留空表示保留已保存的凭证。</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${isActive ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
            {isActive ? '启用中' : '已停用'}
          </span>
        </div>

        <div className="mt-6 grid gap-5 sm:grid-cols-2">
          <label className="block text-sm font-medium">
            Provider
            <select value={provider} disabled className={`${inputClass} disabled:cursor-not-allowed disabled:opacity-70`}>
              <option value="deepseek">deepseek</option>
            </select>
          </label>
          <label className="block text-sm font-medium">
            模型名称
            <input required maxLength={100} value={modelName} onChange={(event) => setModelName(event.target.value)} className={inputClass} />
          </label>
          <label className="block text-sm font-medium sm:col-span-2">
            Base URL
            <input required type="url" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} className={inputClass} />
          </label>
          <label className="block text-sm font-medium sm:col-span-2">
            {configured ? '更新API Key（选填）' : 'API Key'}
            <input
              type="password"
              required={!configured}
              autoComplete="new-password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder={configured ? '留空以保留现有API Key' : '请输入企业API Key'}
              className={inputClass}
            />
            <span className="mt-2 block text-xs text-on-surface-variant">
              此输入值只存在于当前页面内存，提交后立即清空。
            </span>
          </label>
          <label className="flex items-center gap-3 text-sm font-medium sm:col-span-2">
            <input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} className="h-4 w-4 rounded border-slate-300 text-primary" />
            启用该模型配置
          </label>
        </div>

        <div className="mt-7 flex flex-wrap gap-3">
          <button
            type="submit"
            disabled={loading || saving || !modelName.trim() || !baseUrl.trim() || (!configured && !apiKey.trim())}
            className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存配置'}
          </button>
          <button
            type="button"
            onClick={() => void testConnection()}
            disabled={loading || testing || !exists || !config?.is_active || !configured}
            className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {testing ? '测试中...' : '测试连接'}
          </button>
        </div>
      </form>
    </section>
  )
}

function StatusCard({ icon, label, value, active }: { icon: string; label: string; value: string; active: boolean }) {
  return (
    <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-ambient">
      <div className="flex items-center gap-3">
        <span className={`material-symbols-outlined flex h-10 w-10 items-center justify-center rounded-xl ${active ? 'bg-blue-50 text-primary' : 'bg-slate-100 text-slate-400'}`}>{icon}</span>
        <div className="min-w-0">
          <p className="text-xs font-medium text-on-surface-variant">{label}</p>
          <p className="mt-1 truncate text-sm font-semibold">{value}</p>
        </div>
      </div>
    </article>
  )
}
