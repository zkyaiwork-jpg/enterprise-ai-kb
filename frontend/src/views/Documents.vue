<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import DataSurface from '../components/DataSurface.vue'
import EmptyState from '../components/EmptyState.vue'
import AsyncState from '../components/AsyncState.vue'
import PageHeader from '../components/PageHeader.vue'
import DocumentActions from '../components/documents/DocumentActions.vue'
import DocumentDetail from '../components/documents/DocumentDetail.vue'
import DocumentPermissionDialog from '../components/documents/DocumentPermissionDialog.vue'
import DocumentUploadDialog from '../components/documents/DocumentUploadDialog.vue'
import {
  deleteDocument, listAvailableUploadTeams, listDocuments, listFolders,
  type DocumentItem, type DocumentVisibility, type FolderOption, type TeamOption,
} from '../api/documents'
import { getApiErrorMessage } from '../api/http'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const documents = ref<DocumentItem[]>([])
const loading = ref(false)
const loadError = ref('')
const page = ref(1)
const pageSize = ref(10)
const teams = ref<TeamOption[]>([])
const folders = ref<FolderOption[]>([])
const keyword = ref('')
const visibilityFilter = ref<DocumentVisibility>()
const fileTypeFilter = ref<string>()
const uploadVisible = ref(false)
const permissionVisible = ref(false)
const detailVisible = ref(false)
const selectedDocument = ref<DocumentItem>()

const canUpload = computed(() => userStore.hasPermission('file_upload'))
const canEdit = computed(() => userStore.hasPermission('file_edit'))
const canDelete = computed(() => userStore.hasPermission('file_delete'))
const visibilityLabels: Record<DocumentVisibility, string> = { private: '仅自己', team: '团队', department: '部门', company: '全公司' }
const fileTypes = computed(() => Array.from(new Set(documents.value.map((item) => item.file_type || item.type).filter((value): value is string => Boolean(value)))).sort())
const filteredDocuments = computed(() => {
  const query = keyword.value.trim().toLocaleLowerCase()
  return documents.value.filter((document) => {
    const type = document.file_type || document.type || ''
    return (!query || document.filename.toLocaleLowerCase().includes(query) || (document.folder_name || '').toLocaleLowerCase().includes(query))
      && (!visibilityFilter.value || document.visibility === visibilityFilter.value)
      && (!fileTypeFilter.value || type === fileTypeFilter.value)
  })
})
const pagedDocuments = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredDocuments.value.slice(start, start + pageSize.value)
})
const hasFilters = computed(() => Boolean(keyword.value || visibilityFilter.value || fileTypeFilter.value))

async function loadDocuments() {
  loading.value = true
  loadError.value = ''
  try {
    documents.value = await listDocuments()
    page.value = Math.min(page.value, Math.max(1, Math.ceil(filteredDocuments.value.length / pageSize.value)))
  } catch (error) { loadError.value = getApiErrorMessage(error, '文档列表加载失败，请重新加载。') }
  finally { loading.value = false }
}

async function loadFormOptions() {
  const requests: Promise<void>[] = [listFolders().then((items) => { folders.value = items }).catch(() => { folders.value = [] })]
  if (canUpload.value || canEdit.value) requests.push(listAvailableUploadTeams().then((items) => { teams.value = items }).catch(() => { teams.value = [] }))
  await Promise.all(requests)
}

function showDetails(document: DocumentItem) { selectedDocument.value = document; detailVisible.value = true }
function editPermission(document: DocumentItem) { selectedDocument.value = document; permissionVisible.value = true }
function clearFilters() { keyword.value = ''; visibilityFilter.value = undefined; fileTypeFilter.value = undefined }
async function confirmDelete(document: DocumentItem) {
  try {
    await ElMessageBox.confirm(`删除“${document.filename}”后，将同步移除知识库中的相关内容。此操作无法撤销。`, '删除文档', { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' })
    await deleteDocument(document.filename)
    ElMessage.success('文档已删除')
    await loadDocuments()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getApiErrorMessage(error, '文档删除失败'))
  }
}

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
function fileType(document: DocumentItem) { return (document.file_type || document.type || 'FILE').replace('.', '').slice(0, 5).toUpperCase() }

watch([keyword, visibilityFilter, fileTypeFilter, pageSize], () => { page.value = 1 })
onMounted(async () => { await Promise.all([loadDocuments(), loadFormOptions()]) })
</script>

<template>
  <main class="documents-page">
    <PageHeader title="文档管理" description="管理企业知识文档和访问范围。">
      <template #actions><el-button v-if="canUpload" type="primary" @click="uploadVisible = true">上传文档</el-button></template>
    </PageHeader>

    <DataSurface title="知识文档" :description="`共 ${documents.length} 份文档`">
      <template #actions><el-button text :loading="loading" @click="loadDocuments">刷新</el-button></template>

      <div class="document-filters">
        <el-input v-model="keyword" clearable placeholder="搜索文件名或文件夹" aria-label="搜索文档" />
        <el-select v-model="visibilityFilter" clearable placeholder="可见范围" aria-label="按可见范围筛选">
          <el-option v-for="(label, value) in visibilityLabels" :key="value" :label="label" :value="value" />
        </el-select>
        <el-select v-model="fileTypeFilter" clearable placeholder="文件类型" aria-label="按文件类型筛选">
          <el-option v-for="type in fileTypes" :key="type" :label="type.toUpperCase()" :value="type" />
        </el-select>
        <el-button v-if="hasFilters" text @click="clearFilters">清除筛选</el-button>
        <span class="filter-result">显示 {{ filteredDocuments.length }} 份</span>
      </div>

      <AsyncState v-if="loading" state="loading" title="正在加载文档" />
      <AsyncState v-else-if="loadError" state="error" title="文档列表无法加载" :description="loadError" @retry="loadDocuments" />
      <el-table v-else-if="filteredDocuments.length" :data="pagedDocuments" row-key="document_id" class="document-table">
        <el-table-column label="文档" min-width="280">
          <template #default="{ row }">
            <button type="button" class="document-primary" @click="showDetails(row)">
              <span class="file-type-mark">{{ fileType(row) }}</span>
              <span><strong>{{ row.filename }}</strong><small><span v-if="row.file_type || row.type">{{ row.file_type || row.type }}</span><span v-if="row.file_size != null || row.size != null">{{ formatSize(row.file_size ?? row.size) }}</span><span>内部 ID {{ row.document_id }}</span></small></span>
            </button>
          </template>
        </el-table-column>
        <el-table-column label="访问范围" min-width="150">
          <template #default="{ row }"><div class="access-cell"><span class="visibility-label">{{ visibilityLabels[row.visibility as DocumentVisibility] }}</span><small v-if="row.folder_name">文件夹：{{ row.folder_name }}</small></div></template>
        </el-table-column>
        <el-table-column label="上传信息" min-width="190">
          <template #default="{ row }"><div class="secondary-cell"><span v-if="row.uploaded_at">{{ formatDate(row.uploaded_at) }}</span><small v-if="row.uploader_id != null">上传者内部 ID {{ row.uploader_id }}</small></div></template>
        </el-table-column>
        <el-table-column label="组织范围" min-width="160">
          <template #default="{ row }"><div class="secondary-cell"><span v-if="row.department_id != null">部门内部 ID {{ row.department_id }}</span><small v-if="row.team_id != null">团队内部 ID {{ row.team_id }}</small><span v-if="row.department_id == null && row.team_id == null">—</span></div></template>
        </el-table-column>
        <el-table-column label="操作" width="64" align="center">
          <template #default="{ row }"><DocumentActions :can-edit="canEdit" :can-delete="canDelete" @view="showDetails(row)" @edit="editPermission(row)" @delete="confirmDelete(row)" /></template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && !loadError && filteredDocuments.length" class="document-mobile-list">
        <article v-for="document in pagedDocuments" :key="document.document_id" class="document-mobile-item">
          <button type="button" class="mobile-document-main" @click="showDetails(document)"><span class="file-type-mark">{{ fileType(document) }}</span><span><strong>{{ document.filename }}</strong><small>{{ document.file_type || document.type || '文件' }}<template v-if="document.uploaded_at"> · {{ formatDate(document.uploaded_at) }}</template></small></span></button>
          <div class="mobile-document-footer"><span class="visibility-label">{{ visibilityLabels[document.visibility] }}</span><DocumentActions :can-edit="canEdit" :can-delete="canDelete" @view="showDetails(document)" @edit="editPermission(document)" @delete="confirmDelete(document)" /></div>
        </article>
      </div>

      <EmptyState v-if="!loading && !loadError && !filteredDocuments.length" :title="hasFilters ? '没有符合筛选条件的文档' : '暂无可访问的文档'" :description="hasFilters ? '调整或清除筛选条件后重试。' : '拥有上传权限的成员可以添加企业知识文档。'" />

      <div v-if="!loadError && filteredDocuments.length" class="pagination-wrap">
        <el-pagination class="desktop-pagination" v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10, 20, 50]" :total="filteredDocuments.length" layout="total, sizes, prev, pager, next" />
        <el-pagination class="mobile-pagination" v-model:current-page="page" :page-size="pageSize" :total="filteredDocuments.length" layout="prev, pager, next" />
      </div>
    </DataSurface>

    <DocumentUploadDialog v-model="uploadVisible" :teams="teams" :folders="folders" @uploaded="loadDocuments" />
    <DocumentPermissionDialog v-model="permissionVisible" :document="selectedDocument" :teams="teams" @updated="loadDocuments" />
    <DocumentDetail v-model="detailVisible" :document="selectedDocument" />
  </main>
</template>

<style scoped>
.documents-page { display: grid; gap: var(--space-6); width: min(1320px, 100%); margin: 0 auto; }
.document-filters { display: flex; align-items: center; gap: var(--space-2); min-height: 60px; padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--color-border); }
.document-filters .el-input { width: min(280px, 100%); }.document-filters .el-select { width: 150px; }.filter-result { margin-left: auto; color: var(--color-text-secondary); font-size: var(--font-size-secondary); white-space: nowrap; }
.document-primary, .mobile-document-main { display: flex; align-items: center; gap: var(--space-3); min-width: 0; width: 100%; padding: 0; text-align: left; border: 0; background: transparent; cursor: pointer; }
.file-type-mark { display: grid; place-items: center; flex: 0 0 auto; min-width: 40px; height: 36px; padding: 0 var(--space-2); color: var(--color-primary); background: var(--color-primary-subtle); border: 1px solid #bfdbfe; border-radius: var(--radius-md); font-size: var(--font-size-secondary); font-weight: 600; }
.document-primary > span:last-child, .mobile-document-main > span:last-child { min-width: 0; }
.document-primary strong, .document-primary small, .mobile-document-main strong, .mobile-document-main small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.document-primary strong, .mobile-document-main strong { color: var(--color-text); font-size: var(--font-size-body); font-weight: 500; }.document-primary:hover strong, .mobile-document-main:hover strong { color: var(--color-primary); }
.document-primary small, .mobile-document-main small { margin-top: var(--space-1); color: var(--color-text-secondary); font-size: var(--font-size-secondary); }.document-primary small span + span::before { margin: 0 var(--space-2); content: '·'; }
.access-cell, .secondary-cell { display: grid; gap: var(--space-1); }.access-cell small, .secondary-cell small, .secondary-cell span { color: var(--color-text-secondary); font-size: var(--font-size-secondary); }.visibility-label { display: inline-flex; width: fit-content; padding: 2px var(--space-2); color: var(--color-primary); background: var(--color-primary-subtle); border: 1px solid #bfdbfe; border-radius: var(--radius-sm); font-size: var(--font-size-secondary); }
.document-mobile-list { display: none; }.pagination-wrap { display: flex; justify-content: flex-end; padding: var(--space-3) var(--space-4); border-top: 1px solid var(--color-border); }.mobile-pagination { display: none; }
:deep(.document-table th.el-table__cell) { color: var(--color-text-secondary); background: var(--color-surface); font-size: var(--font-size-secondary); font-weight: 500; }:deep(.document-table td.el-table__cell) { padding: var(--space-3) 0; color: var(--color-text); font-size: var(--font-size-body); }

@media (max-width: 760px) {
  .documents-page { gap: var(--space-4); }.document-filters { align-items: stretch; flex-direction: column; }.document-filters .el-input, .document-filters .el-select { width: 100%; }.filter-result { margin-left: 0; }.document-table { display: none; }.document-mobile-list { display: grid; }.document-mobile-item { padding: var(--space-3); border-bottom: 1px solid var(--color-border); }.document-mobile-item:last-child { border-bottom: 0; }.mobile-document-footer { display: flex; align-items: center; justify-content: space-between; margin-top: var(--space-3); padding-top: var(--space-2); border-top: 1px solid var(--color-border); }.desktop-pagination { display: none; }.mobile-pagination { display: flex; }.pagination-wrap { justify-content: center; padding-inline: var(--space-2); }
}
</style>
