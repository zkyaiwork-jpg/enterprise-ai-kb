<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createTeam, listDepartments, listTeams, type DepartmentItem, type TeamItem } from '../api/organization'
import { getApiErrorMessage } from '../api/http'
import PageHeader from '../components/PageHeader.vue'
import DataSurface from '../components/DataSurface.vue'
import EmptyState from '../components/EmptyState.vue'
import CapabilityNotice from '../components/CapabilityNotice.vue'
import AsyncState from '../components/AsyncState.vue'

const teams = ref<TeamItem[]>([]), departments = ref<DepartmentItem[]>([])
const loading = ref(false), departmentFilter = ref<number>(), dialogVisible = ref(false), saving = ref(false), formRef = ref<FormInstance>()
const loadError = ref('')
const form = reactive({ name: '', department_id: undefined as number | undefined, description: '' })
const rules: FormRules = { name: [{ required: true, message: '请输入团队名称', trigger: 'blur' }, { max: 100, message: '团队名称不能超过 100 个字符', trigger: 'blur' }], department_id: [{ required: true, message: '请选择所属部门', trigger: 'change' }] }
async function loadTeams() { loading.value = true; loadError.value = ''; try { teams.value = await listTeams(departmentFilter.value) } catch (error) { loadError.value = getApiErrorMessage(error, '团队列表加载失败，请重新加载。') } finally { loading.value = false } }
async function loadDepartments() { try { departments.value = await listDepartments() } catch (error) { ElMessage.error(getApiErrorMessage(error, '部门选项加载失败')) } }
function openCreate() { Object.assign(form, { name: '', department_id: departmentFilter.value, description: '' }); dialogVisible.value = true }
async function submit() {
  if (!(await formRef.value?.validate().catch(() => false)) || !form.department_id) return
  saving.value = true
  try { await createTeam({ name: form.name.trim(), department_id: form.department_id, description: form.description.trim() || null }); ElMessage.success('团队创建成功'); dialogVisible.value = false; await loadTeams() }
  catch (error) { ElMessage.error(getApiErrorMessage(error, '团队创建失败')) }
  finally { saving.value = false }
}
function formatDate(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false }) }
onMounted(async () => { await Promise.all([loadTeams(), loadDepartments()]) })
</script>

<template>
  <section class="organization-page">
    <PageHeader title="团队管理" description="查看部门下的团队并创建团队。"><template #actions><el-button type="primary" :disabled="departments.length === 0" @click="openCreate">创建团队</el-button></template></PageHeader>
    <CapabilityNotice title="当前开放范围" description="目前支持查看、按部门筛选和创建团队；编辑、删除及团队成员关系尚无可用接口，因此本页不提供相关操作。" />
    <DataSurface title="团队列表" :description="`共 ${teams.length} 个团队`"><template #actions><el-select v-model="departmentFilter" clearable filterable placeholder="全部部门" aria-label="按部门筛选团队" @change="loadTeams"><el-option v-for="department in departments" :key="department.id" :label="department.name" :value="department.id" /></el-select></template>
      <div class="entity-content">
        <AsyncState v-if="loading" state="loading" title="正在加载团队" />
        <AsyncState v-else-if="loadError" state="error" title="团队列表无法加载" :description="loadError" @retry="loadTeams" />
        <template v-else-if="teams.length">
          <el-table :data="teams" row-key="id" class="entity-table">
            <el-table-column label="团队" min-width="200"><template #default="{ row }"><div class="entity-name"><strong>{{ row.name }}</strong><span>内部 ID {{ row.id }}</span></div></template></el-table-column>
            <el-table-column label="所属部门" min-width="180"><template #default="{ row }"><strong class="department-name">{{ row.department.name }}</strong></template></el-table-column>
            <el-table-column label="说明" min-width="280"><template #default="{ row }">{{ row.description || '未填写说明' }}</template></el-table-column>
            <el-table-column label="创建时间" width="190"><template #default="{ row }"><time :datetime="row.created_time">{{ formatDate(row.created_time) }}</time></template></el-table-column>
          </el-table>
          <div class="entity-list-mobile"><article v-for="team in teams" :key="team.id"><div class="mobile-heading"><div><strong>{{ team.name }}</strong><span>内部 ID {{ team.id }}</span></div><b>{{ team.department.name }}</b></div><p>{{ team.description || '未填写说明' }}</p><time :datetime="team.created_time">{{ formatDate(team.created_time) }}</time></article></div>
        </template>
        <EmptyState v-else title="暂无团队" :description="departmentFilter ? '该部门下暂无团队。' : '当前没有可显示的团队。'" />
      </div>
    </DataSurface>
    <el-dialog v-model="dialogVisible" title="创建团队" width="500px" destroy-on-close><el-form ref="formRef" :model="form" :rules="rules" label-position="top"><el-form-item label="团队名称" prop="name"><el-input v-model="form.name" maxlength="100" /></el-form-item><el-form-item label="所属部门" prop="department_id"><el-select v-model="form.department_id" filterable><el-option v-for="department in departments" :key="department.id" :label="department.name" :value="department.id" /></el-select></el-form-item><el-form-item label="团队说明"><el-input v-model="form.description" type="textarea" :rows="4" /></el-form-item></el-form><template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submit">创建团队</el-button></template></el-dialog>
  </section>
</template>

<style scoped>
.organization-page { display: grid; gap: var(--space-6); max-width: 1280px; margin: 0 auto; }.entity-content { min-height: 160px; }.entity-name strong, .entity-name span { display: block; }.entity-name strong, .department-name { color: var(--color-text); font-size: var(--font-size-body); font-weight: 600; }.entity-name span { margin-top: var(--space-1); color: var(--color-text-secondary); font-size: var(--font-size-secondary); }time { color: var(--color-text-secondary); font-size: var(--font-size-secondary); font-variant-numeric: tabular-nums; }.entity-list-mobile { display: none; }:deep(.el-select) { width: 180px; }:deep(.el-table th.el-table__cell) { height: 44px; color: var(--color-text-secondary); background: var(--color-surface); font-size: var(--font-size-secondary); font-weight: 500; }:deep(.el-table td.el-table__cell) { padding: var(--space-3) 0; color: var(--color-text-secondary); font-size: var(--font-size-body); }:deep(.el-table__inner-wrapper::before) { display: none; }
@media (max-width: 700px) { .entity-table { display: none; }.entity-list-mobile { display: grid; }.entity-list-mobile article { padding: var(--space-4); border-bottom: 1px solid var(--color-border); }.entity-list-mobile article:last-child { border-bottom: 0; }.mobile-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); }.entity-list-mobile strong, .entity-list-mobile span { display: block; }.entity-list-mobile strong { color: var(--color-text); font-size: var(--font-size-body); }.entity-list-mobile span, .entity-list-mobile p { color: var(--color-text-secondary); font-size: var(--font-size-secondary); }.entity-list-mobile span { margin-top: var(--space-1); }.entity-list-mobile b { padding: 3px var(--space-2); border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: var(--font-size-secondary); font-weight: 500; }.entity-list-mobile p { margin: var(--space-3) 0; line-height: 1.6; } }
</style>
