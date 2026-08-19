<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createUser, updateUser, type ManagedUser, type NamedOption, type TeamOption } from '../../api/users'
import { getApiErrorMessage } from '../../api/http'
import { getUserRoleLabel } from '../../utils/userRole'

const props = defineProps<{ roles: NamedOption[]; departments: NamedOption[]; teams: TeamOption[] }>()
const emit = defineEmits<{ saved: [] }>()
const visible = ref(false)
const mode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()
const saving = ref(false)
const editingUser = ref<ManagedUser>()
const form = reactive({ username: '', password: '', role_id: undefined as number | undefined, department_id: undefined as number | undefined, team_id: undefined as number | undefined })
const selectedRole = computed(() => props.roles.find((role) => role.id === form.role_id))
const needsTeam = computed(() => ['employee', 'leader'].includes(selectedRole.value?.name.toLowerCase() || ''))
const availableTeams = computed(() => form.department_id ? props.teams.filter((team) => team.department_id === form.department_id) : [])

function validateTeam(_rule: unknown, value: unknown, callback: (error?: Error) => void) { callback(needsTeam.value && !value ? new Error('员工和组长必须分配团队') : undefined) }
function validatePassword(_rule: unknown, value: unknown, callback: (error?: Error) => void) {
  const password = String(value || '')
  if (mode.value === 'create' && password.length < 8) callback(new Error('密码至少需要 8 个字符'))
  else if (new TextEncoder().encode(password).length > 72) callback(new Error('密码不能超过 72 字节'))
  else callback()
}
const rules: FormRules = {
  username: [{ required: true, message: '请输入姓名', trigger: 'blur' }, { min: 1, max: 100, message: '姓名不能超过 100 个字符', trigger: 'blur' }],
  password: [{ validator: validatePassword, trigger: 'blur' }],
  role_id: [{ required: true, message: '请选择角色', trigger: 'change' }],
  team_id: [{ validator: validateTeam, trigger: 'change' }],
}
function resetForm() { Object.assign(form, { username: '', password: '', role_id: undefined, department_id: undefined, team_id: undefined }); nextTick(() => formRef.value?.clearValidate()) }
function openCreate() { mode.value = 'create'; editingUser.value = undefined; resetForm(); visible.value = true }
function openEdit(user: ManagedUser) {
  mode.value = 'edit'; editingUser.value = user
  Object.assign(form, { username: user.username, password: '', role_id: user.role?.id, department_id: user.department?.id, team_id: user.team?.id })
  visible.value = true; nextTick(() => formRef.value?.clearValidate())
}
async function submit() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  saving.value = true
  try {
    const userData = { username: form.username.trim(), role_id: form.role_id!, department_id: form.department_id ?? null, team_id: needsTeam.value ? form.team_id ?? null : null }
    if (mode.value === 'create') { await createUser({ password: form.password, ...userData }); ElMessage.success('用户创建成功') }
    else if (editingUser.value) { await updateUser(editingUser.value.id, userData); ElMessage.success('用户信息已更新') }
    visible.value = false; emit('saved')
  } catch (error) { ElMessage.error(getApiErrorMessage(error, mode.value === 'create' ? '用户创建失败' : '用户更新失败')) }
  finally { saving.value = false }
}
watch(() => form.department_id, () => { if (form.team_id && !availableTeams.value.some((team) => team.id === form.team_id)) form.team_id = undefined; formRef.value?.clearValidate('team_id') })
watch(() => form.role_id, () => { if (!needsTeam.value) form.team_id = undefined; formRef.value?.clearValidate('team_id') })
defineExpose({ openCreate, openEdit })
</script>

<template>
  <el-dialog v-model="visible" :title="mode === 'create' ? '创建用户' : '编辑用户'" width="600px" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <section class="form-section"><h3>账号信息</h3><div class="form-grid">
        <el-form-item label="姓名" prop="username"><el-input v-model="form.username" maxlength="100" autocomplete="name" placeholder="输入员工真实姓名" /></el-form-item>
        <el-form-item v-if="mode === 'create'" label="初始密码" prop="password"><el-input v-model="form.password" type="password" show-password autocomplete="new-password" placeholder="至少 8 个字符" /></el-form-item>
      </div></section>
      <section class="form-section"><h3>组织归属</h3><div class="form-grid">
        <el-form-item label="部门"><el-select v-model="form.department_id" clearable filterable placeholder="可不分配"><el-option v-for="department in departments" :key="department.id" :label="department.name" :value="department.id" /></el-select></el-form-item>
        <el-form-item v-if="needsTeam" label="团队" prop="team_id"><el-select v-model="form.team_id" filterable :disabled="!form.department_id" placeholder="先选择部门，再选择团队"><el-option v-for="team in availableTeams" :key="team.id" :label="team.name" :value="team.id" /></el-select></el-form-item>
      </div></section>
      <section class="form-section"><h3>权限角色</h3><el-form-item label="角色" prop="role_id"><el-select v-model="form.role_id"><el-option v-for="role in roles" :key="role.id" :label="getUserRoleLabel(role.name)" :value="role.id" /></el-select></el-form-item><p class="form-note">员工和组长必须归属团队；组织约束会在保存时再次校验。</p></section>
    </el-form>
    <template #footer><el-button @click="visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submit">{{ mode === 'create' ? '创建用户' : '保存修改' }}</el-button></template>
  </el-dialog>
</template>

<style scoped>
.form-section + .form-section { margin-top: var(--space-6); padding-top: 20px; border-top: 1px solid var(--color-border); }
.form-section h3 { margin: 0 0 var(--space-4); color: var(--color-text); font-size: var(--font-size-body); font-weight: 600; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
.form-section :deep(.el-select) { width: 100%; }
.form-note { margin: calc(var(--space-2) * -1) 0 0; color: var(--color-text-secondary); font-size: var(--font-size-secondary); line-height: 1.6; }
@media (max-width: 640px) { .form-grid { grid-template-columns: 1fr; gap: 0; } }
</style>
