import axios, { AxiosError } from 'axios'
import { getToken, removeToken } from '../utils/token'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 120_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      removeToken()
      if (window.location.pathname !== '/login') {
        const redirect = encodeURIComponent(
          `${window.location.pathname}${window.location.search}`,
        )
        window.location.assign(`/login?redirect=${redirect}`)
      }
    }
    return Promise.reject(error)
  },
)

export function getApiErrorMessage(error: unknown, fallback = '请求失败，请稍后重试'): string {
  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data as { detail?: unknown } | undefined
    const detail = responseData?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (item as { msg?: string } | null)?.msg)
        .filter(Boolean)
        .join('；') || fallback
    }
    if (!error.response) return '无法连接后端服务，请检查 FastAPI 是否已启动'
  }
  return error instanceof Error && error.message ? error.message : fallback
}
