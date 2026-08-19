<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteUser, listDepartments, listRoles, listTeams, listUsers, updateUser, type ManagedUser, type NamedOption, type TeamOption, type UserStatus } from '../api/users'
import { getApiErrorMessage } from '../api/http'
import PageHeader from '../components/PageHeader.vue'
import DataSurface from '../components/DataSurface.vue'
import EmptyState from '../components/EmptyState.vue'
import AsyncState from '../components/AsyncState.vue'
import UserActions from '../components/users/UserActions.vue'
import UserFormDialog from '../components/users/UserFormDialog.vue'
import PasswordResetDialog from '../components/users/PasswordResetDialog.vue'
import { useUserStore } from '../stores/user'
import { getUserRoleLabel } from '../utils/userRole'

const userStore = useUserStore()

const users = ref<ManagedUser[]>([])
const roles = ref<NamedOption[]>([])
const departments = ref<NamedOption[]>([])
const teams = ref<TeamOption[]>([])
const loading = ref(false)
const loadError = ref('')
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const localSearch = ref('')
const filters = reactive<{ status?: UserStatus; department_id?: number; role_id?: number }>({})
const userFormDialog = ref<InstanceType<typeof UserFormDialog>>()
const passwordResetDialog = ref<InstanceType<typeof PasswordResetDialog>>()
const deletingUserId = ref<number>()

const visibleUsers = computed(() => {
  const query = localSearch.value.trim().toLocaleLowerCase('zh-CN')
  if (!query) return users.value
  return users.value.filter((user) => user.username.toLocaleLowerCase('zh-CN').includes(query) || user.real_name.toLocaleLowerCase('zh-CN').includes(query))
})
const hasServerFilters = computed(() => Boolean(filters.status || filters.department_id || filters.role_id))
const emptyDescription = computed(() => localSearch.value.trim()
  ? '当前页没有匹配的姓名，请调整搜索内容。'
  : hasServerFilters.value ? '没有符合当前筛选条件的成员。' : '尚未创建企业成员。')
const currentUserId = computed(() => userStore.state.profile?.id)

async function loadUsers() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await listUsers({ page: page.value, page_size: pageSize.value, ...filters })
    users.value = response.items
    total.value = response.total
  } catch (error) { loadError.value = getApiErrorMessage(error, '用户列表加载失败，请重新加载。') }
  finally { loading.value = false }
}
async function loadOptions() {
  try {
    const [roleItems, departmentItems, teamItems] = await Promise.all([listRoles(), listDepartments(), listTeams()])
    roles.value = roleItems; departments.value = departmentItems; teams.value = teamItems
  } catch (error) { ElMessage.error(getApiErrorMessage(error, '组织与角色选项加载失败')) }
}
function applyFilters() { page.value = 1; void loadUsers() }
function resetFilters() { localSearch.value = ''; Object.assign(filters, { status: undefined, department_id: undefined, role_id: undefined }); applyFilters() }
async function toggleStatus(user: ManagedUser) {
  const nextStatus: UserStatus = user.status === 'active' ? 'inactive' : 'active'
  const action = nextStatus === 'active' ? '启用' : '禁用'
  try {
    await ElMessageBox.confirm(nextStatus === 'inactive' ? `禁用“${user.username}”后，其现有登录凭证将不可继续使用。` : `确定启用“${user.username}”吗？`, `${action}用户`, { confirmButtonText: `确认${action}`, cancelButtonText: '取消', type: nextStatus === 'inactive' ? 'warning' : 'info' })
    await updateUser(user.id, { status: nextStatus })
    ElMessage.success(`用户已${action}`)
    await loadUsers()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getApiErrorMessage(error, `${action}用户失败`))
  }
}
async function confirmDelete(user: ManagedUser) {
  if (user.id === currentUserId.value || deletingUserId.value != null) return
  try {
    await ElMessageBox.confirm(
      `确定要删除“${user.username}”吗？\n\n删除后该用户将无法登录系统。如果该用户仍有关联企业数据，系统将阻止删除并提示处理方式。`,
      '删除用户',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning', distinguishCancelAndClose: true },
    )
    deletingUserId.value = user.id
    await deleteUser(user.id)
    const lastPage = Math.max(1, Math.ceil(Math.max(0, total.value - 1) / pageSize.value))
    if (page.value > lastPage) page.value = lastPage
    ElMessage.success('用户已删除')
    await loadUsers()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getApiErrorMessage(error, '删除用户失败'))
  } finally {
    deletingUserId.value = undefined
  }
}
function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

watch(pageSize, () => { page.value = 1; void loadUsers() })
onMounted(async () => { await Promise.all([loadUsers(), loadOptions()]) })
</script>

<template>
  <section class="users-page">
    <PageHeader title="用户管理" description="管理企业成员、角色和访问权限。">
      <template #actions><el-button type="primary" @click="userFormDialog?.openCreate()">创建用户</el-button></template>
    </PageHeader>

    <DataSurface title="组织成员" :description="`共 ${total} 位成员`">
      <template #actions><span class="data-note">搜索仅作用于当前页</span></template>
      <div class="filter-toolbar" role="search" aria-label="用户筛选">
        <el-input v-model="localSearch" clearable class="search-field" placeholder="搜索当前页姓名" aria-label="搜索当前页姓名"><template #prefix><svg class="search-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m16 16 4 4" /></svg></template></el-input>
        <el-select v-model="filters.status" clearable placeholder="账号状态" aria-label="按账号状态筛选" @change="applyFilters"><el-option label="已启用" value="active" /><el-option label="已禁用" value="inactive" /></el-select>
        <el-select v-model="filters.role_id" clearable placeholder="角色" aria-label="按角色筛选" @change="applyFilters"><el-option v-for="role in roles" :key="role.id" :label="getUserRoleLabel(role.name)" :value="role.id" /></el-select>
        <el-select v-model="filters.department_id" clearable filterable placeholder="部门" aria-label="按部门筛选" @change="applyFilters"><el-option v-for="department in departments" :key="department.id" :label="department.name" :value="department.id" /></el-select>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <div class="member-content">
        <AsyncState v-if="loading" state="loading" title="正在加载成员" />
        <AsyncState v-else-if="loadError" state="error" title="成员列表无法加载" :description="loadError" @retry="loadUsers" />
        <template v-else-if="visibleUsers.length">
          <el-table :data="visibleUsers" row-key="id" class="member-table">
            <el-table-column label="成员" min-width="220"><template #default="{ row }"><div class="identity-cell"><span class="initial" aria-hidden="true">{{ row.username.slice(0, 1) }}</span><strong>{{ row.username }}</strong></div></template></el-table-column>
            <el-table-column label="角色" min-width="130"><template #default="{ row }"><span class="role-label">{{ getUserRoleLabel(row.role?.name) }}</span></template></el-table-column>
            <el-table-column label="组织归属" min-width="210"><template #default="{ row }"><div class="organization-cell"><strong>{{ row.department?.name || '未分配部门' }}</strong><span>{{ row.team?.name || '未分配团队' }}</span></div></template></el-table-column>
            <el-table-column label="状态" width="110"><template #default="{ row }"><span :class="['status-label', row.status]"><i aria-hidden="true" />{{ row.status === 'active' ? '已启用' : '已禁用' }}</span></template></el-table-column>
            <el-table-column label="创建时间" width="180"><template #default="{ row }"><div class="metadata-cell"><span>{{ formatDate(row.created_time) }}</span><small>内部 ID {{ row.id }}</small></div></template></el-table-column>
            <el-table-column label="操作" width="72" align="right"><template #default="{ row }"><UserActions :user="row" :can-delete="row.id !== currentUserId" :disabled="deletingUserId === row.id" @edit="userFormDialog?.openEdit($event)" @reset-password="passwordResetDialog?.open($event)" @toggle-status="toggleStatus" @delete="confirmDelete" /></template></el-table-column>
          </el-table>

          <div class="member-cards">
            <article v-for="user in visibleUsers" :key="user.id" class="member-card">
              <div class="member-card-heading"><div class="identity-cell"><span class="initial" aria-hidden="true">{{ user.username.slice(0, 1) }}</span><strong>{{ user.username }}</strong></div><UserActions :user="user" :can-delete="user.id !== currentUserId" :disabled="deletingUserId === user.id" @edit="userFormDialog?.openEdit($event)" @reset-password="passwordResetDialog?.open($event)" @toggle-status="toggleStatus" @delete="confirmDelete" /></div>
              <div class="member-card-facts"><div><span>角色</span><strong>{{ getUserRoleLabel(user.role?.name) }}</strong></div><div><span>状态</span><strong :class="['status-label', user.status]"><i aria-hidden="true" />{{ user.status === 'active' ? '已启用' : '已禁用' }}</strong></div></div>
              <p class="member-organization">{{ user.department?.name || '未分配部门' }}<span aria-hidden="true">/</span>{{ user.team?.name || '未分配团队' }}</p>
            </article>
          </div>
        </template>
        <EmptyState v-else title="暂无匹配成员" :description="emptyDescription" />
      </div>

      <div v-if="!loadError && total > 0" class="pagination-wrap"><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" :total="total" layout="total, sizes, prev, pager, next" @current-change="loadUsers" /></div>
    </DataSurface>

    <UserFormDialog ref="userFormDialog" :roles="roles" :departments="departments" :teams="teams" @saved="loadUsers" />
    <PasswordResetDialog ref="passwordResetDialog" />
  </section>
</template>

<style scoped>
.users-page { display: grid; gap: var(--space-6); max-width: 1380px; margin: 0 auto; }
.data-note { color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
.filter-toolbar { display: grid; grid-template-columns: minmax(240px, 1fr) repeat(3, 160px) auto; gap: var(--space-3); padding: var(--space-4); border-bottom: 1px solid var(--color-border); background: var(--color-surface); }
.search-icon { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-width: 1.75; }
.member-content { min-height: 160px; }
.identity-cell { display: flex; align-items: center; gap: var(--space-3); min-width: 0; }
.initial { display: grid; place-items: center; flex: 0 0 auto; width: 36px; height: 36px; color: var(--color-primary); border: 1px solid #bfdbfe; border-radius: var(--radius-md); background: var(--color-primary-subtle); font-size: var(--font-size-body); font-weight: 600; }
.identity-cell strong, .identity-cell span, .organization-cell strong, .organization-cell span, .metadata-cell span, .metadata-cell small { display: block; }
.identity-cell strong { overflow: hidden; color: var(--color-text); font-size: var(--font-size-body); font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.role-label { display: inline-flex; padding: 3px var(--space-2); color: var(--color-text); border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-background); font-size: var(--font-size-secondary); }
.organization-cell strong { color: var(--color-text); font-size: var(--font-size-body); font-weight: 500; }
.organization-cell span { margin-top: 3px; color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
.status-label { display: inline-flex; align-items: center; gap: var(--space-2); font-size: var(--font-size-secondary); font-weight: 500; }
.status-label i { width: 7px; height: 7px; flex: 0 0 auto; border-radius: 50%; background: currentColor; }
.status-label.active { color: var(--color-success); }
.status-label.inactive { color: var(--color-error); }
.metadata-cell span { color: var(--color-text-secondary); font-size: var(--font-size-secondary); font-variant-numeric: tabular-nums; }
.metadata-cell small { margin-top: 3px; color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
.pagination-wrap { display: flex; justify-content: flex-end; padding: var(--space-4); border-top: 1px solid var(--color-border); }
.member-cards { display: none; }
:deep(.el-table th.el-table__cell) { height: 44px; color: var(--color-text-secondary); background: var(--color-surface); font-size: var(--font-size-secondary); font-weight: 500; }
:deep(.el-table td.el-table__cell) { padding: var(--space-3) 0; color: var(--color-text-secondary); font-size: var(--font-size-body); }
:deep(.el-table__inner-wrapper::before) { display: none; }
@media (max-width: 1080px) { .filter-toolbar { grid-template-columns: 1fr 1fr; } }
@media (max-width: 760px) {
  .data-note { display: none; }
  .filter-toolbar { grid-template-columns: 1fr 1fr; }
  .search-field { grid-column: 1 / -1; }
  .member-table { display: none; }
  .member-cards { display: grid; }
  .member-card { padding: var(--space-4); border-bottom: 1px solid var(--color-border); }
  .member-card:last-child { border-bottom: 0; }
  .member-card-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); }
  .member-card-facts { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); margin-top: var(--space-4); padding-top: var(--space-3); border-top: 1px solid var(--color-border); }
  .member-card-facts > div > span { display: block; margin-bottom: var(--space-1); color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
  .member-card-facts strong { color: var(--color-text); font-size: var(--font-size-body); font-weight: 500; }
  .member-organization { display: flex; flex-wrap: wrap; gap: var(--space-2); margin: var(--space-3) 0 0; color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
  .pagination-wrap { justify-content: flex-start; }
  .pagination-wrap :deep(.el-pagination__total), .pagination-wrap :deep(.el-pagination__sizes), .pagination-wrap :deep(.el-pager) { display: none; }
}
@media (max-width: 520px) { .filter-toolbar { grid-template-columns: 1fr; } .search-field { grid-column: auto; } }
</style>
