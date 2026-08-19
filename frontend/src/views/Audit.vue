<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { listAuditLogs, type AuditLogItem, type AuditResult } from '../api/audit'
import { getApiErrorMessage } from '../api/http'
import PageHeader from '../components/PageHeader.vue'
import DataSurface from '../components/DataSurface.vue'
import EmptyState from '../components/EmptyState.vue'
import AsyncState from '../components/AsyncState.vue'

const logs = ref<AuditLogItem[]>([])
const loading = ref(false)
const loadError = ref('')
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive<{ action: string; user_id?: number; result?: AuditResult }>({ action: '' })
const hasFilters = computed(() => Boolean(filters.action.trim() || filters.user_id || filters.result))

const actionLabels: Record<string, string> = {
  auth_login_success: '登录成功', auth_login_failed: '登录失败', document_upload: '上传文档', document_update: '修改文档', document_delete: '删除文档',
  user_create: '创建用户', user_update: '更新用户', user_status_change: '变更用户状态', user_password_reset: '重置用户密码',
  department_create: '创建部门', team_create: '创建团队', model_config_update: '更新模型配置', model_config_test: '测试模型配置', system_bootstrap_admin: '初始化管理员',
}
const resourceLabels: Record<string, string> = { user: '用户', document: '文档', department: '部门', team: '团队', model_config: '模型配置', auth: '认证', system: '系统' }

async function loadLogs() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await listAuditLogs({ page: page.value, page_size: pageSize.value, action: filters.action.trim() || undefined, user_id: filters.user_id, result: filters.result })
    logs.value = response.items; total.value = response.total
  } catch (error) { loadError.value = getApiErrorMessage(error, '审计日志加载失败，请重新加载。') }
  finally { loading.value = false }
}
function applyFilters() { page.value = 1; void loadLogs() }
function resetFilters() { Object.assign(filters, { action: '', user_id: undefined, result: undefined }); applyFilters() }
function formatDate(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false }) }
function actionLabel(action: string) { return actionLabels[action] || action }
function resourceLabel(type: string) { return resourceLabels[type] || type }
watch(pageSize, () => { page.value = 1; void loadLogs() })
onMounted(loadLogs)
</script>

<template>
  <section class="audit-page">
    <PageHeader title="审计日志" description="查看系统中的关键操作与执行结果。" />
    <DataSurface title="操作记录" :description="`共 ${total} 条记录`">
      <div class="filter-toolbar" role="search" aria-label="审计日志筛选">
        <el-input v-model="filters.action" clearable placeholder="操作编码，例如 document_upload" aria-label="按操作编码筛选" @keyup.enter="applyFilters" />
        <el-input-number v-model="filters.user_id" :min="1" :controls="false" placeholder="操作用户 ID" aria-label="按操作用户 ID 筛选" />
        <el-select v-model="filters.result" clearable placeholder="操作结果" aria-label="按操作结果筛选"><el-option label="成功" value="success" /><el-option label="失败" value="failed" /></el-select>
        <el-button type="primary" @click="applyFilters">查询</el-button><el-button @click="resetFilters">重置</el-button>
      </div>
      <div class="audit-content">
        <AsyncState v-if="loading" state="loading" title="正在加载审计日志" />
        <AsyncState v-else-if="loadError" state="error" title="审计日志无法加载" :description="loadError" @retry="loadLogs" />
        <template v-else-if="logs.length">
          <el-table :data="logs" row-key="id" class="audit-table">
            <el-table-column label="操作时间" width="190"><template #default="{ row }"><time :datetime="row.created_time">{{ formatDate(row.created_time) }}</time></template></el-table-column>
            <el-table-column label="操作用户" width="130"><template #default="{ row }"><div class="user-reference"><strong>{{ row.user_id === null ? '系统' : `用户 ID ${row.user_id}` }}</strong><span v-if="row.ip_address">{{ row.ip_address }}</span></div></template></el-table-column>
            <el-table-column label="操作类型" min-width="190"><template #default="{ row }"><div class="action-reference"><strong>{{ actionLabel(row.action) }}</strong><span>{{ row.action }}</span></div></template></el-table-column>
            <el-table-column label="操作对象" min-width="220"><template #default="{ row }"><div class="resource-reference"><strong>{{ row.resource_name || resourceLabel(row.resource_type) }}</strong><span>{{ resourceLabel(row.resource_type) }}<template v-if="row.resource_id"> · ID {{ row.resource_id }}</template></span></div></template></el-table-column>
            <el-table-column label="结果" width="100"><template #default="{ row }"><span :class="['result-label', row.result]"><i aria-hidden="true" />{{ row.result === 'success' ? '成功' : '失败' }}</span></template></el-table-column>
            <el-table-column type="expand"><template #default="{ row }"><dl class="audit-detail"><div><dt>记录 ID</dt><dd>{{ row.id }}</dd></div><div><dt>详细信息</dt><dd>{{ row.detail || '无' }}</dd></div><div><dt>IP 地址</dt><dd>{{ row.ip_address || '未记录' }}</dd></div></dl></template></el-table-column>
          </el-table>
          <div class="audit-list-mobile"><article v-for="log in logs" :key="log.id"><header><div><strong>{{ actionLabel(log.action) }}</strong><span>{{ log.action }}</span></div><span :class="['result-label', log.result]"><i aria-hidden="true" />{{ log.result === 'success' ? '成功' : '失败' }}</span></header><dl><div><dt>时间</dt><dd>{{ formatDate(log.created_time) }}</dd></div><div><dt>用户</dt><dd>{{ log.user_id === null ? '系统' : `用户 ID ${log.user_id}` }}</dd></div><div><dt>对象</dt><dd>{{ log.resource_name || resourceLabel(log.resource_type) }}<template v-if="log.resource_id"> · ID {{ log.resource_id }}</template></dd></div><div v-if="log.detail"><dt>详情</dt><dd>{{ log.detail }}</dd></div></dl></article></div>
        </template>
        <EmptyState v-else title="暂无审计记录" :description="hasFilters ? '没有符合当前筛选条件的操作记录。' : '系统尚未返回可显示的审计记录。'" />
      </div>
      <div v-if="!loadError && total > 0" class="pagination-wrap"><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" :total="total" layout="total, sizes, prev, pager, next" @current-change="loadLogs" /></div>
    </DataSurface>
  </section>
</template>

<style scoped>
.audit-page { display: grid; gap: var(--space-6); max-width: 1380px; margin: 0 auto; }
.filter-toolbar { display: grid; grid-template-columns: minmax(260px, 1fr) 160px 150px auto auto; gap: var(--space-3); padding: var(--space-4); border-bottom: 1px solid var(--color-border); background: var(--color-surface); }
.filter-toolbar :deep(.el-input-number) { width: 100%; }.filter-toolbar :deep(.el-input-number .el-input__inner) { text-align: left; }.audit-content { min-height: 180px; }
time { color: var(--color-text-secondary); font-size: var(--font-size-secondary); font-variant-numeric: tabular-nums; }.user-reference strong, .user-reference span, .action-reference strong, .action-reference span, .resource-reference strong, .resource-reference span { display: block; }.user-reference strong, .action-reference strong, .resource-reference strong { color: var(--color-text); font-size: var(--font-size-body); font-weight: 500; }.user-reference span, .action-reference span, .resource-reference span { margin-top: var(--space-1); color: var(--color-text-secondary); font-size: var(--font-size-secondary); }.result-label { display: inline-flex; align-items: center; gap: var(--space-2); font-size: var(--font-size-secondary); font-weight: 500; }.result-label i { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }.result-label.success { color: var(--color-success); }.result-label.failed { color: var(--color-error); }.audit-detail { display: grid; grid-template-columns: 120px 1fr 180px; gap: var(--space-6); margin: 0; padding: var(--space-3) var(--space-10); }.audit-detail div { min-width: 0; }.audit-detail dt { margin-bottom: var(--space-1); color: var(--color-text-secondary); font-size: var(--font-size-secondary); }.audit-detail dd { overflow-wrap: anywhere; margin: 0; color: var(--color-text); font-size: var(--font-size-body); line-height: 1.6; }.pagination-wrap { display: flex; justify-content: flex-end; padding: var(--space-4); border-top: 1px solid var(--color-border); }.audit-list-mobile { display: none; }:deep(.el-table th.el-table__cell) { height: 44px; color: var(--color-text-secondary); background: var(--color-surface); font-size: var(--font-size-secondary); font-weight: 500; }:deep(.el-table td.el-table__cell) { padding: var(--space-3) 0; color: var(--color-text-secondary); font-size: var(--font-size-body); }:deep(.el-table__inner-wrapper::before) { display: none; }
@media (max-width: 1000px) { .filter-toolbar { grid-template-columns: 1fr 1fr; } }
@media (max-width: 760px) { .filter-toolbar { grid-template-columns: 1fr; }.audit-table { display: none; }.audit-list-mobile { display: grid; }.audit-list-mobile article { padding: var(--space-4); border-bottom: 1px solid var(--color-border); }.audit-list-mobile article:last-child { border-bottom: 0; }.audit-list-mobile header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); }.audit-list-mobile header strong, .audit-list-mobile header span { display: block; }.audit-list-mobile header strong { color: var(--color-text); font-size: var(--font-size-body); }.audit-list-mobile header div > span { margin-top: var(--space-1); color: var(--color-text-secondary); font-size: var(--font-size-secondary); }.audit-list-mobile dl { display: grid; gap: var(--space-2); margin: var(--space-4) 0 0; }.audit-list-mobile dl div { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: var(--space-3); }.audit-list-mobile dt, .audit-list-mobile dd { margin: 0; font-size: var(--font-size-secondary); line-height: 1.6; }.audit-list-mobile dt { color: var(--color-text-secondary); }.audit-list-mobile dd { overflow-wrap: anywhere; color: var(--color-text); }.pagination-wrap { justify-content: flex-start; }.pagination-wrap :deep(.el-pagination__total), .pagination-wrap :deep(.el-pagination__sizes), .pagination-wrap :deep(.el-pager) { display: none; } }
</style>
