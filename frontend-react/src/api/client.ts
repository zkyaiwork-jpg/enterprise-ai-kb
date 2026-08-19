import axios, { AxiosError } from 'axios'

import { clearAccessToken, getAccessToken, notifyForbidden } from '../auth/authStorage'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export class ApiError extends Error {
  status?: number
  details?: unknown

  constructor(message: string, status?: number, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: {
    Accept: 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.set('Authorization', `Bearer ${token}`)
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new ApiError('请求超时，请稍后重试。'))
    }

    if (!error.response) {
      return Promise.reject(new ApiError('后端服务未连接，请确认 FastAPI 服务已启动。'))
    }

    if (error.response.status === 401 && error.config?.url !== '/auth/login') {
      clearAccessToken()
    } else if (error.response.status === 403) {
      notifyForbidden()
    }

    const message = error.response.data?.detail || error.response.data?.message || error.message || '请求失败，请稍后重试。'
    return Promise.reject(new ApiError(message, error.response.status, error.response.data))
  },
)

export default apiClient
