<script setup lang="ts">
import type { DocumentItem, DocumentVisibility } from '../../api/documents'

defineProps<{ modelValue: boolean; document?: DocumentItem }>()
defineEmits<{ 'update:modelValue': [value: boolean] }>()

const visibilityLabels: Record<DocumentVisibility, string> = { private: '仅自己', team: '团队', department: '部门', company: '全公司' }
function formatSize(value?: number) {
  if (value == null) return ''
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}
function formatDate(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <el-drawer :model-value="modelValue" title="文档详情" size="min(520px, 94vw)" @update:model-value="$emit('update:modelValue', $event)">
    <div v-if="document" class="document-detail">
      <header><span>{{ (document.file_type || document.type || 'FILE').replace('.', '').slice(0, 5).toUpperCase() }}</span><div><h2>{{ document.filename }}</h2><p>文档内部 ID：{{ document.document_id }}</p></div></header>
      <dl>
        <div><dt>可见范围</dt><dd>{{ visibilityLabels[document.visibility] }}</dd></div>
        <div v-if="document.file_type || document.type"><dt>文件类型</dt><dd>{{ document.file_type || document.type }}</dd></div>
        <div v-if="document.file_size != null || document.size != null"><dt>文件大小</dt><dd>{{ formatSize(document.file_size ?? document.size) }}</dd></div>
        <div v-if="document.uploaded_at"><dt>上传时间</dt><dd>{{ formatDate(document.uploaded_at) }}</dd></div>
        <div v-if="document.folder_name"><dt>文件夹</dt><dd>{{ document.folder_name }}</dd></div>
        <div v-if="document.uploader_id != null"><dt>上传者内部 ID</dt><dd>{{ document.uploader_id }}</dd></div>
        <div v-if="document.department_id != null"><dt>部门内部 ID</dt><dd>{{ document.department_id }}</dd></div>
        <div v-if="document.team_id != null"><dt>团队内部 ID</dt><dd>{{ document.team_id }}</dd></div>
        <div v-if="document.chunk_count != null"><dt>知识片段数</dt><dd>{{ document.chunk_count }}</dd></div>
        <div v-if="document.status"><dt>文档状态</dt><dd>{{ document.status }}</dd></div>
      </dl>
    </div>
  </el-drawer>
</template>

<style scoped>
.document-detail > header { display: flex; align-items: flex-start; gap: var(--space-3); padding-bottom: var(--space-6); border-bottom: 1px solid var(--color-border); }
.document-detail > header > span { display: grid; place-items: center; flex: 0 0 auto; min-width: 44px; height: 44px; padding: 0 var(--space-2); color: var(--color-primary); background: var(--color-primary-subtle); border: 1px solid #bfdbfe; border-radius: var(--radius-md); font-size: var(--font-size-secondary); font-weight: 600; }
.document-detail h2 { margin: 0; overflow-wrap: anywhere; color: var(--color-text); font-size: var(--font-size-section-title); font-weight: 600; line-height: 1.5; }
.document-detail header p { margin: var(--space-1) 0 0; color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
.document-detail dl { margin: 0; }
.document-detail dl > div { display: grid; grid-template-columns: 120px minmax(0, 1fr); gap: var(--space-4); padding: var(--space-3) 0; border-bottom: 1px solid var(--color-border); }
.document-detail dt { color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
.document-detail dd { margin: 0; overflow-wrap: anywhere; color: var(--color-text); font-size: var(--font-size-body); }
</style>
