<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createDepartment, listDepartments, type DepartmentItem } from '../api/organization'
import { getApiErrorMessage } from '../api/http'
import PageHeader from '../components/PageHeader.vue'
import DataSurface from '../components/DataSurface.vue'
import EmptyState from '../components/EmptyState.vue'
import CapabilityNotice from '../components/CapabilityNotice.vue'
import AsyncState from '../components/AsyncState.vue'

const departments = ref<DepartmentItem[]>([])
const loading = ref(false)
const loadError = ref('')
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '' })
const rules: FormRules = { name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }, { max: 100, message: '部门名称不能超过 100 个字符', trigger: 'blur' }] }

async function loadDepartments() {
  loading.value = true
  loadError.value = ''
  try { departments.value = await listDepartments() }
  catch (error) { loadError.value = getApiErrorMessage(error, '部门列表加载失败，请重新加载。') }
  finally { loading.value = false }
}
function openCreate() { Object.assign(form, { name: '', description: '' }); dialogVisible.value = true }
async function submit() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  saving.value = true
  try {
    await createDepartment({ name: form.name.trim(), description: form.description.trim() || null })
    ElMessage.success('部门创建成功'); dialogVisible.value = false; await loadDepartments()
  } catch (error) { ElMessage.error(getApiErrorMessage(error, '部门创建失败')) }
  finally { saving.value = false }
}
function formatDate(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false }) }
onMounted(loadDepartments)
</script>

<template>
  <section class="organization-page">
    <PageHeader title="部门管理" description="查看企业部门结构并创建部门。"><template #actions><el-button type="primary" @click="openCreate">创建部门</el-button></template></PageHeader>
    <CapabilityNotice title="当前开放范围" description="目前支持查看和创建部门；编辑、删除及部门成员关联尚无可用接口，因此本页不提供相关操作。" />
    <DataSurface title="部门列表" :description="`共 ${departments.length} 个部门`">
      <div class="entity-content">
        <AsyncState v-if="loading" state="loading" title="正在加载部门" />
        <AsyncState v-else-if="loadError" state="error" title="部门列表无法加载" :description="loadError" @retry="loadDepartments" />
        <template v-else-if="departments.length">
          <el-table :data="departments" row-key="id" class="entity-table">
            <el-table-column label="部门" min-width="220"><template #default="{ row }"><div class="entity-name"><strong>{{ row.name }}</strong><span>内部 ID {{ row.id }}</span></div></template></el-table-column>
            <el-table-column label="说明" min-width="320"><template #default="{ row }">{{ row.description || '未填写说明' }}</template></el-table-column>
            <el-table-column label="创建时间" width="190"><template #default="{ row }"><time :datetime="row.created_time">{{ formatDate(row.created_time) }}</time></template></el-table-column>
          </el-table>
          <div class="entity-list-mobile"><article v-for="department in departments" :key="department.id"><div><strong>{{ department.name }}</strong><span>内部 ID {{ department.id }}</span></div><p>{{ department.description || '未填写说明' }}</p><time :datetime="department.created_time">{{ formatDate(department.created_time) }}</time></article></div>
        </template>
        <EmptyState v-else title="暂无部门" description="当前没有可显示的部门，可使用右上角按钮创建。" />
      </div>
    </DataSurface>
    <el-dialog v-model="dialogVisible" title="创建部门" width="480px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top"><el-form-item label="部门名称" prop="name"><el-input v-model="form.name" maxlength="100" /></el-form-item><el-form-item label="部门说明"><el-input v-model="form.description" type="textarea" :rows="4" /></el-form-item></el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submit">创建部门</el-button></template>
    </el-dialog>
  </section>
</template>

<style scoped>
.organization-page { display: grid; gap: var(--space-6); max-width: 1280px; margin: 0 auto; }
.entity-content { min-height: 160px; }
.entity-name strong, .entity-name span { display: block; }
.entity-name strong { color: var(--color-text); font-size: var(--font-size-body); font-weight: 600; }
.entity-name span { margin-top: var(--space-1); color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
time { color: var(--color-text-secondary); font-size: var(--font-size-secondary); font-variant-numeric: tabular-nums; }
.entity-list-mobile { display: none; }
:deep(.el-table th.el-table__cell) { height: 44px; color: var(--color-text-secondary); background: var(--color-surface); font-size: var(--font-size-secondary); font-weight: 500; }
:deep(.el-table td.el-table__cell) { padding: var(--space-3) 0; color: var(--color-text-secondary); font-size: var(--font-size-body); }
:deep(.el-table__inner-wrapper::before) { display: none; }
@media (max-width: 700px) { .entity-table { display: none; } .entity-list-mobile { display: grid; } .entity-list-mobile article { padding: var(--space-4); border-bottom: 1px solid var(--color-border); } .entity-list-mobile article:last-child { border-bottom: 0; } .entity-list-mobile strong, .entity-list-mobile span { display: block; } .entity-list-mobile strong { color: var(--color-text); font-size: var(--font-size-body); } .entity-list-mobile span, .entity-list-mobile p { color: var(--color-text-secondary); font-size: var(--font-size-secondary); } .entity-list-mobile span { margin-top: var(--space-1); } .entity-list-mobile p { margin: var(--space-3) 0; line-height: 1.6; } }
</style>
