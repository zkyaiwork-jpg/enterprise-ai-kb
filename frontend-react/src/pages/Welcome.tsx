import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { useDesktopUser } from '../hooks/useDesktopUser'


export function Welcome() {
  const navigate = useNavigate()
  const { setUserName } = useDesktopUser()
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedName = name.trim()
    const desktopApi = window.desktopApp
    if (!normalizedName || !desktopApi || saving) return

    setSaving(true)
    setError('')
    try {
      const result = await desktopApi.saveUserName(normalizedName)
      if (result.success) {
        setUserName(result.userName)
        navigate('/', { replace: true })
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '姓名保存失败，请稍后重试。')
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-[#eaf2ff] via-[#f5f9ff] to-white px-5 py-10">
      <section className="w-full max-w-lg rounded-[28px] border border-white bg-white p-8 shadow-ambient sm:p-10">
        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-white shadow-sm">
          <span className="material-symbols-outlined text-[28px]">auto_awesome</span>
        </span>
        <p className="mt-7 text-xs font-semibold uppercase tracking-[0.16em] text-primary">Enterprise AI Knowledge System</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-on-surface">欢迎使用企业AI知识库助手</h1>
        <p className="mt-3 text-sm text-on-surface-variant">请输入您的姓名</p>

        <form onSubmit={handleSubmit} className="mt-8">
          <label htmlFor="welcome-user-name" className="text-sm font-medium text-on-surface">姓名</label>
          <input
            id="welcome-user-name"
            autoFocus
            maxLength={50}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="请输入姓名"
            className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3.5 text-sm text-on-surface outline-none transition focus:border-primary focus:bg-white focus:ring-4 focus:ring-blue-50"
          />
          {error && <div className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
          {!window.desktopApp && <div className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">用户初始化仅在 Electron 桌面应用中可用。</div>}
          <button
            type="submit"
            disabled={saving || !name.trim() || !window.desktopApp}
            className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#0044ad] disabled:bg-[#aebbd1]"
          >
            {saving ? '正在保存...' : '开始使用'}
          </button>
        </form>
      </section>
    </main>
  )
}
