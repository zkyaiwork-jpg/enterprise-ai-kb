import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '../components/Layout.vue'
import { useUserStore } from '../stores/user'
import { getToken } from '../utils/token'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/Login.vue'),
      meta: { public: true, title: '登录' },
    },
    {
      path: '/',
      component: AppLayout,
      meta: { title: '首页' },
      children: [
        { path: '', name: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '首页' } },
        { path: 'chat', name: 'chat', component: () => import('../views/Chat.vue'), meta: { title: 'AI 问答' } },
        { path: 'documents', name: 'documents', component: () => import('../views/Documents.vue'), meta: { title: '文档管理' } },
        { path: 'search', name: 'search', component: () => import('../views/Search.vue'), meta: { title: '智能检索', permission: 'file_view' } },
        { path: 'users', name: 'users', component: () => import('../views/Users.vue'), meta: { title: '用户管理', permission: 'user_manage' } },
        { path: 'departments', name: 'departments', component: () => import('../views/Departments.vue'), meta: { title: '部门管理', permission: 'user_manage' } },
        { path: 'teams', name: 'teams', component: () => import('../views/Teams.vue'), meta: { title: '团队管理', permission: 'user_manage' } },
        { path: 'audit', name: 'audit', component: () => import('../views/Audit.vue'), meta: { title: '审计日志', permission: 'audit_view' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const token = getToken()
  if (to.meta.public) return token ? '/' : true
  if (!token) return { path: '/login', query: { redirect: to.fullPath } }

  const userStore = useUserStore()
  if (!userStore.state.profile) {
    try {
      await userStore.loadProfile()
    } catch {
      userStore.logout()
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }

  const permission = to.meta.permission
  if (typeof permission === 'string' && !userStore.hasPermission(permission)) {
    return '/'
  }
  return true
})

export default router
