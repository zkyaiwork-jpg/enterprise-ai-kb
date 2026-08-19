import { FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDesktopUser } from '../hooks/useDesktopUser'


export function Settings() {
  const navigate = useNavigate()
  const { userName, setUserName } = useDesktopUser()
  const [apiKey, setApiKey] = useState('')
  const [configured, setConfigured] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [userDialogOpen, setUserDialogOpen] = useState(false)
  const [newUserName, setNewUserName] = useState('')
  const [userSaving, setUserSaving] = useState(false)
  const [userMessage, setUserMessage] = useState('')
  const [userError, setUserError] = useState('')
  const desktopApi = window.desktopApp

  useEffect(() => {
    if (!desktopApi) {
      setLoading(false)
      return
    }
    void desktopApi.getSettingsStatus()
      .then((status) => setConfigured(status.hasDeepseekApiKey))
      .catch(() => setError('无法读取桌面端配置。'))
      .finally(() => setLoading(false))
  }, [desktopApi])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedKey = apiKey.trim()
    if (!normalizedKey || !desktopApi) return

    setSaving(true)
    setMessage('')
    setError('')
    try {
      const result = await desktopApi.saveDeepseekApiKey(normalizedKey)
      if (result.success && result.backendReady) {
        setConfigured(true)
        setApiKey('')
        setMessage('API Key 已安全保存，AI 服务已启动。')
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '保存失败，请稍后重试。')
    } finally {
      setSaving(false)
    }
  }

  function openUserDialog() {
    setNewUserName(userName)
    setUserMessage('')
    setUserError('')
    setUserDialogOpen(true)
  }

  function closeUserDialog() {
    if (userSaving) return
    setUserDialogOpen(false)
    setUserError('')
  }

  async function handleUserNameSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedUserName = newUserName.trim()
    if (!normalizedUserName) {
      setUserError('请输入有效的姓名。')
      return
    }
    if (!desktopApi) {
      setUserError('用户名配置仅在 Electron 桌面应用中可用。')
      return
    }

    setUserSaving(true)
    setUserError('')
    try {
      const result = await desktopApi.saveUserName(normalizedUserName)
      setUserName(result.userName)
      setUserDialogOpen(false)
      setUserMessage('用户名修改成功。')
    } catch (reason) {
      setUserError(reason instanceof Error ? reason.message : '用户名保存失败，请稍后重试。')
    } finally {
      setUserSaving(false)
    }
  }

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">Settings</p>
        <h2 className="text-3xl font-semibold tracking-tight text-on-surface">系统设置</h2>
        <p className="mt-3 text-sm text-on-surface-variant">配置 AI 服务凭证。密钥仅保存在当前 Windows 用户的本地配置目录。</p>
      </header>

      <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-ambient sm:p-8" aria-labelledby="user-settings-title">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-50 text-lg font-semibold text-primary">
              {userName.trim().charAt(0) || '用'}
            </div>
            <div>
              <h3 id="user-settings-title" className="text-lg font-semibold text-on-surface">用户信息</h3>
              <p className="mt-1 text-sm text-on-surface-variant">
                当前用户名：<span className="font-medium text-on-surface">{userName || '未设置'}</span>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={openUserDialog}
            className="rounded-xl border border-primary/20 bg-blue-50 px-5 py-2.5 text-sm font-semibold text-primary transition hover:bg-blue-100"
          >
            修改用户名
          </button>
        </div>
        {userMessage && <div className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{userMessage}</div>}
      </section>

      <form onSubmit={handleSubmit} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-ambient sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-on-surface">DeepSeek API Key</h3>
            <p className="mt-1 text-sm text-on-surface-variant">用于企业知识库 RAG 问答，不会写入安装包或日志。</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${configured ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
            {loading ? '检查中' : configured ? '已配置' : '未配置'}
          </span>
        </div>

        {desktopApi ? (
          <>
            <label className="mt-6 block text-sm font-medium text-on-surface" htmlFor="deepseek-api-key">API Key</label>
            <input
              id="deepseek-api-key"
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder={configured ? '输入新 Key 以更换当前配置' : '请输入 DeepSeek API Key'}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-on-surface outline-none transition focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50"
            />
            <p className="mt-2 text-xs text-on-surface-variant">页面不会读回或显示已保存的密钥明文。</p>

            {message && <div className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{message}</div>}
            {error && <div className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

            <div className="mt-6 flex flex-wrap gap-3">
              <button type="submit" disabled={saving || !apiKey.trim()} className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50">
                {saving ? '正在保存并启动...' : configured ? '更新并重启 AI 服务' : '保存并启动 AI 服务'}
              </button>
              {configured && <button type="button" onClick={() => navigate('/')} className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-on-surface hover:bg-slate-50">返回工作台</button>}
            </div>
          </>
        ) : (
          <div className="mt-6 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">密钥配置仅在 Electron 桌面应用中可用。
          </div>
        )}
      </form>

      {userDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 p-4 backdrop-blur-[2px]"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeUserDialog()
          }}
        >
          <form
            onSubmit={handleUserNameSubmit}
            className="w-full max-w-md rounded-2xl border border-slate-100 bg-white p-6 shadow-2xl sm:p-7"
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-user-name-title"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 id="edit-user-name-title" className="text-xl font-semibold text-on-surface">修改用户名</h3>
                <p className="mt-2 text-sm text-on-surface-variant">新名称将立即用于工作台欢迎语和顶部用户信息。</p>
              </div>
              <button
                type="button"
                onClick={closeUserDialog}
                disabled={userSaving}
                aria-label="关闭"
                className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50"
              >
                ×
              </button>
            </div>

            <label className="mt-6 block text-sm font-medium text-on-surface" htmlFor="user-name">姓名</label>
            <input
              id="user-name"
              type="text"
              autoFocus
              maxLength={50}
              value={newUserName}
              onChange={(event) => setNewUserName(event.target.value)}
              placeholder="请输入姓名"
              className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-on-surface outline-none transition focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50"
            />
            {userError && <div className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{userError}</div>}

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={closeUserDialog}
                disabled={userSaving}
                className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-on-surface transition hover:bg-slate-50 disabled:opacity-50"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={userSaving || !newUserName.trim()}
                className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {userSaving ? '正在保存...' : '保存'}
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  )
}
