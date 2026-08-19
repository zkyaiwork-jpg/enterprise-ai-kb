import { createBrowserRouter } from 'react-router-dom'

import { Layout } from './components/Layout'
import { Assistant } from './pages/Assistant'
import { Dashboard } from './pages/Dashboard'
import { Knowledge } from './pages/Knowledge'
import { Search } from './pages/Search'
import { Settings } from './pages/Settings'
import { Welcome } from './pages/Welcome'
import { Login } from './pages/Login'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { PublicOnlyRoute } from './components/auth/PublicOnlyRoute'
import { AdminUsers } from './pages/AdminUsers'
import { AdminDepartments } from './pages/AdminDepartments'
import { AdminModelConfig } from './pages/AdminModelConfig'
import { AdminAuditLogs } from './pages/AdminAuditLogs'
import { AdminTeams } from './pages/AdminTeams'

export const router = createBrowserRouter([
  { path: '/login', element: <PublicOnlyRoute><Login /></PublicOnlyRoute> },
  { path: '/welcome', element: <Welcome /> },
  {
    path: '/',
    element: <ProtectedRoute><Layout /></ProtectedRoute>,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'knowledge', element: <Knowledge /> },
      { path: 'assistant', element: <Assistant /> },
      { path: 'search', element: <Search /> },
      { path: 'settings', element: <Settings /> },
      { path: 'admin/users', element: <AdminUsers /> },
      { path: 'admin/departments', element: <AdminDepartments /> },
      { path: 'admin/teams', element: <AdminTeams /> },
      { path: 'admin/model-config', element: <AdminModelConfig /> },
      { path: 'admin/audit-logs', element: <AdminAuditLogs /> },
    ],
  },
])
