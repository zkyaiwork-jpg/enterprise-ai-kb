import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await login(username.trim(), password)
      setPassword('')
      const from = (location.state as { from?: string } | null)?.from
      navigate(from && from !== '/login' ? from : '/', { replace: true })
    } catch {
      setPassword('')
      setError('用户名或密码错误')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f5f9ff] px-5 py-10 text-on-surface">
      <section className="w-full max-w-md rounded-3xl border border-outline-variant bg-white p-8 shadow-[0_20px_60px_rgba(28,78,121,0.12)] sm:p-10">
        <div className="mb-8 text-center">
          <span className="material-symbols-outlined mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-fixed text-3xl text-primary">
            shield_person
          </span>
          <h1 className="text-2xl font-bold">登录企业知识库</h1>
          <p className="mt-2 text-sm text-on-surface-variant">使用管理员分配的企业账号登录</p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium">
            用户名
            <input
              autoComplete="username"
              autoFocus
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="mt-2 h-12 w-full rounded-xl border border-outline-variant bg-white px-4 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
              placeholder="请输入用户名"
            />
          </label>
          <label className="block text-sm font-medium">
            密码
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 h-12 w-full rounded-xl border border-outline-variant bg-white px-4 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
              placeholder="请输入密码"
            />
          </label>

          {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

          <button
            type="submit"
            disabled={submitting || !username.trim() || !password}
            className="h-12 w-full rounded-xl bg-primary font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? '正在登录...' : '登录'}
          </button>
        </form>
      </section>
    </main>
  )
}
