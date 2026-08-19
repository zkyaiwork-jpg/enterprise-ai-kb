<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules, type UploadFile } from 'element-plus'
import { uploadDocument, type DocumentVisibility, type FolderOption, type TeamOption } from '../../api/documents'
import { getApiErrorMessage } from '../../api/http'

const props = defineProps<{ modelValue: boolean; teams: TeamOption[]; folders: FolderOption[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; uploaded: [] }>()
const formRef = ref<FormInstance>()
const file = ref<File>()
const fileList = ref<UploadFile[]>([])
const uploading = ref(false)
const form = reactive<{ visibility: DocumentVisibility; team_id?: number; folder_id?: number }>({ visibility: 'private' })
const visibilityLabels: Record<DocumentVisibility, string> = { private: '仅自己', team: '团队', department: '部门', company: '全公司' }

function validateTeam(_rule: unknown, value: unknown, callback: (error?: Error) => void) { callback(form.visibility === 'team' && !value ? new Error('请选择目标团队') : undefined) }
const rules: FormRules = { visibility: [{ required: true, message: '请选择可见范围', trigger: 'change' }], team_id: [{ validator: validateTeam, trigger: 'change' }] }
function selectFile(selected: UploadFile) { file.value = selected.raw; fileList.value = [selected] }
function removeFile() { file.value = undefined; fileList.value = [] }
async function submit() {
  if (!file.value) { ElMessage.warning('请选择要上传的文件'); return }
  if (!(await formRef.value?.validate().catch(() => false))) return
  const payload = new FormData()
  payload.append('file', file.value)
  payload.append('visibility', form.visibility)
  if (form.folder_id) payload.append('folder_id', String(form.folder_id))
  if (form.visibility === 'team' && form.team_id) payload.append('team_id', String(form.team_id))
  uploading.value = true
  try {
    await uploadDocument(payload)
    ElMessage.success('文档上传成功')
    emit('update:modelValue', false)
    emit('uploaded')
  } catch (error) { ElMessage.error(getApiErrorMessage(error, '文档上传失败')) }
  finally { uploading.value = false }
}

watch(() => props.modelValue, (visible) => {
  if (!visible) return
  file.value = undefined; fileList.value = []
  Object.assign(form, { visibility: 'private', team_id: undefined, folder_id: undefined })
})
watch(() => form.visibility, (value) => { if (value !== 'team') form.team_id = undefined; formRef.value?.clearValidate('team_id') })
</script>

<template>
  <el-dialog :model-value="modelValue" title="上传文档" width="min(540px, 94vw)" destroy-on-close @update:model-value="$emit('update:modelValue', $event)">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <section class="dialog-section"><h3>文件选择</h3><el-form-item label="文档文件" required><el-upload v-model:file-list="fileList" drag action="#" :auto-upload="false" :limit="1" accept=".docx,.txt,.pdf" :on-change="selectFile" :on-remove="removeFile"><div class="upload-copy"><strong>点击或拖拽文件到此处</strong><span>支持 DOCX、TXT、PDF</span></div></el-upload></el-form-item></section>
      <section class="dialog-section"><h3>访问权限</h3><el-form-item label="可见范围" prop="visibility"><el-select v-model="form.visibility" style="width: 100%"><el-option v-for="(label, value) in visibilityLabels" :key="value" :label="label" :value="value" /></el-select></el-form-item><el-form-item v-if="form.visibility === 'team'" label="目标团队" prop="team_id"><el-select v-model="form.team_id" placeholder="请选择团队" style="width: 100%" filterable><el-option v-for="team in teams" :key="team.id" :label="`${team.department.name} / ${team.name}`" :value="team.id" /></el-select></el-form-item><el-form-item label="文件夹（可选）"><el-select v-model="form.folder_id" clearable placeholder="不归入文件夹" style="width: 100%"><el-option v-for="folder in folders" :key="folder.id" :label="folder.name" :value="folder.id" /></el-select></el-form-item></section>
    </el-form>
    <template #footer><el-button @click="$emit('update:modelValue', false)">取消</el-button><el-button type="primary" :loading="uploading" @click="submit">确认上传</el-button></template>
  </el-dialog>
</template>

<style scoped>
.dialog-section + .dialog-section { margin-top: var(--space-6); padding-top: var(--space-4); border-top: 1px solid var(--color-border); }
.dialog-section h3 { margin: 0 0 var(--space-4); color: var(--color-text); font-size: var(--font-size-section-title); font-weight: 600; }
.upload-copy { padding: var(--space-2) 0; }.upload-copy strong, .upload-copy span { display: block; }.upload-copy strong { color: var(--color-text); font-size: var(--font-size-body); }.upload-copy span { margin-top: var(--space-2); color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
:deep(.el-upload), :deep(.el-upload-dragger) { width: 100%; }
</style>
