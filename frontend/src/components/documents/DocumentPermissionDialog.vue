<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { updateDocument, type DocumentItem, type DocumentVisibility, type TeamOption } from '../../api/documents'
import { getApiErrorMessage } from '../../api/http'

const props = defineProps<{ modelValue: boolean; document?: DocumentItem; teams: TeamOption[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; updated: [] }>()
const formRef = ref<FormInstance>()
const saving = ref(false)
const form = reactive<{ visibility: DocumentVisibility; team_id?: number }>({ visibility: 'private' })
const visibilityLabels: Record<DocumentVisibility, string> = { private: '仅自己', team: '团队', department: '部门', company: '全公司' }
function validateTeam(_rule: unknown, value: unknown, callback: (error?: Error) => void) { callback(form.visibility === 'team' && !value ? new Error('请选择目标团队') : undefined) }
const rules: FormRules = { visibility: [{ required: true, message: '请选择可见范围', trigger: 'change' }], team_id: [{ validator: validateTeam, trigger: 'change' }] }

async function submit() {
  if (!props.document || !(await formRef.value?.validate().catch(() => false))) return
  saving.value = true
  try {
    await updateDocument(props.document.document_id, { visibility: form.visibility, ...(form.visibility === 'team' && form.team_id ? { team_id: form.team_id } : {}) })
    ElMessage.success('文档权限已更新')
    emit('update:modelValue', false)
    emit('updated')
  } catch (error) { ElMessage.error(getApiErrorMessage(error, '文档权限更新失败')) }
  finally { saving.value = false }
}

watch(() => props.modelValue, (visible) => {
  if (!visible || !props.document) return
  form.visibility = props.document.visibility
  form.team_id = props.document.visibility === 'team' ? props.document.team_id ?? undefined : undefined
})
watch(() => form.visibility, (value) => { if (value !== 'team') form.team_id = undefined; formRef.value?.clearValidate('team_id') })
</script>

<template>
  <el-dialog :model-value="modelValue" title="修改文档权限" width="min(480px, 94vw)" destroy-on-close @update:model-value="$emit('update:modelValue', $event)">
    <div v-if="document" class="current-permission"><span>当前文档</span><strong>{{ document.filename }}</strong><span>当前范围：{{ visibilityLabels[document.visibility] }}</span></div>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="新的可见范围" prop="visibility"><el-select v-model="form.visibility" style="width: 100%"><el-option v-for="(label, value) in visibilityLabels" :key="value" :label="label" :value="value" /></el-select></el-form-item>
      <el-form-item v-if="form.visibility === 'team'" label="目标团队" prop="team_id"><el-select v-model="form.team_id" placeholder="请选择团队" style="width: 100%" filterable><el-option v-for="team in teams" :key="team.id" :label="`${team.department.name} / ${team.name}`" :value="team.id" /></el-select></el-form-item>
    </el-form>
    <template #footer><el-button @click="$emit('update:modelValue', false)">取消</el-button><el-button type="primary" :loading="saving" @click="submit">保存修改</el-button></template>
  </el-dialog>
</template>

<style scoped>
.current-permission { display: grid; gap: var(--space-1); margin-bottom: var(--space-6); padding: var(--space-3); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
.current-permission span { color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
.current-permission strong { overflow-wrap: anywhere; color: var(--color-text); font-size: var(--font-size-body); font-weight: 500; }
</style>
