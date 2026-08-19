import { computed, reactive } from 'vue'
import { getCurrentUser, login as loginRequest, type CurrentUser, type LoginPayload } from '../api/auth'
import { getToken, removeToken, setToken } from '../utils/token'

const state = reactive<{
  profile: CurrentUser | null
  loading: boolean
}>({
  profile: null,
  loading: false,
})

async function loadProfile(): Promise<CurrentUser | null> {
  if (!getToken()) return null
  state.loading = true
  try {
    state.profile = await getCurrentUser()
    return state.profile
  } finally {
    state.loading = false
  }
}

async function login(payload: LoginPayload): Promise<void> {
  const token = await loginRequest(payload)
  setToken(token.access_token)
  try {
    await loadProfile()
  } catch (error) {
    removeToken()
    throw error
  }
}

function logout(): void {
  removeToken()
  state.profile = null
}

function hasPermission(permission: string): boolean {
  return state.profile?.permissions.includes(permission) ?? false
}

export function useUserStore() {
  return {
    state,
    isAuthenticated: computed(() => Boolean(getToken())),
    displayName: computed(() => state.profile?.real_name || state.profile?.username || '用户'),
    loadProfile,
    login,
    logout,
    hasPermission,
  }
}
