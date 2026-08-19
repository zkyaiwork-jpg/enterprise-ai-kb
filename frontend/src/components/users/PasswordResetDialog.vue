<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { resetUserPassword, type ManagedUser } from '../../api/users'
import { getApiErrorMessage } from '../../api/http'

const visible = ref(false), formRef = ref<FormInstance>(), saving = ref(false), target = ref<ManagedUser>()
const form = reactive({ new_password: '', confirm_password: '' })
function validateNewPassword(_rule: unknown, value: unknown, callback: (error?: Error) => void) { const password = String(value || ''); if (password.length < 8) callback(new Error('密码至少需要 8 个字符')); else if (new TextEncoder().encode(password).length > 72) callback(new Error('密码不能超过 72 字节')); else callback() }
function validateConfirmPassword(_rule: unknown, value: unknown, callback: (error?: Error) => void) { callback(value !== form.new_password ? new Error('两次输入的密码不一致') : undefined) }
const rules: FormRules = { new_password: [{ validator: validateNewPassword, trigger: 'blur' }], confirm_password: [{ validator: validateConfirmPassword, trigger: 'blur' }] }
function open(user: ManagedUser) { target.value = user; Object.assign(form, { new_password: '', confirm_password: '' }); visible.value = true }
async function submit() {
  if (!target.value || !(await formRef.value?.validate().catch(() => false))) return
  saving.value = true
  try { await resetUserPassword(target.value.id, form.new_password); ElMessage.success('密码已重置，原有登录凭证已失效'); visible.value = false }
  catch (error) { ElMessage.error(getApiErrorMessage(error, '密码重置失败')) }
  finally { saving.value = false }
}
defineExpose({ open })
</script>

<template>
  <el-dialog v-model="visible" title="重置密码" width="480px" destroy-on-close>
    <p class="password-target">管理员正在为 <strong>{{ target?.username }}</strong> 设置新密码。</p>
    <el-alert title="重置后，该用户现有登录凭证将立即失效。" type="warning" :closable="false" show-icon />
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="password-form">
      <el-form-item label="新密码" prop="new_password"><el-input v-model="form.new_password" type="password" show-password autocomplete="new-password" /></el-form-item>
      <el-form-item label="确认新密码" prop="confirm_password"><el-input v-model="form.confirm_password" type="password" show-password autocomplete="new-password" /></el-form-item>
    </el-form>
    <template #footer><el-button @click="visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submit">确认重置</el-button></template>
  </el-dialog>
</template>

<style scoped>
.password-target { margin: 0 0 var(--space-4); color: var(--color-text-secondary); font-size: var(--font-size-body); line-height: 1.6; }
.password-target strong { color: var(--color-text); font-weight: 600; }
.password-form { margin-top: var(--space-6); }
</style>
