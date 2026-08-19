<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AsyncState from '../components/AsyncState.vue'
import DataSurface from '../components/DataSurface.vue'
import EmptyState from '../components/EmptyState.vue'
import { getDashboardStats, type DashboardStats } from '../api/dashboard'
import { listDocuments, type DocumentItem, type DocumentVisibility } from '../api/documents'
import { getApiErrorMessage } from '../api/http'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const stats = ref<DashboardStats>()
const statsLoading = ref(true)
const statsError = ref('')
const documents = ref<DocumentItem[]>([])
const documentsLoading = ref(true)
const documentsError = ref('')
const question = ref('')

const profile = computed(() => userStore.state.profile)
const displayName = computed(() => userStore.displayName.value)
const canUpload = computed(() => userStore.hasPermission('file_upload'))
// 当前 /documents 返回当前用户可见的完整集合；最近上传仅在该响应范围内排序。
const recentDocuments = computed(() => [...documents.value]
  .sort((left, right) => timestamp(right.uploaded_at) - timestamp(left.uploaded_at))
  .slice(0, 5))

const roleLabels: Record<string, string> = { admin: '管理员', manager: '经理', leader: '组长', employee: '员工' }
const visibilityLabels: Record<DocumentVisibility, string> = { private: '仅自己', team: '团队可见', department: '部门可见', company: '公司可见' }

function roleLabel(value?: string) { return value ? roleLabels[value.toLowerCase()] || value : '未分配' }
function timestamp(value?: string) { const time = value ? new Date(value).getTime() : 0; return Number.isNaN(time) ? 0 : time }
function formatDate(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}
function formatSize(value?: number) {
  if (value == null) return ''
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}
function fileType(document: DocumentItem) { return (document.file_type || document.type || '文件').replace('.', '').toUpperCase() }
function askQuestion() {
  const content = question.value.trim()
  if (!content) return
  void router.push({ name: 'chat', query: { q: content } })
}
function openDocuments() { void router.push({ name: 'documents' }) }

async function loadStats() {
  statsLoading.value = true
  statsError.value = ''
  try { stats.value = await getDashboardStats() }
  catch (error) { statsError.value = getApiErrorMessage(error, '知识库概况加载失败，请重新加载。') }
  finally { statsLoading.value = false }
}
async function loadRecentDocuments() {
  documentsLoading.value = true
  documentsError.value = ''
  try { documents.value = await listDocuments() }
  catch (error) { documentsError.value = getApiErrorMessage(error, '最近文档加载失败，请重新加载。') }
  finally { documentsLoading.value = false }
}

onMounted(() => { void Promise.all([loadStats(), loadRecentDocuments()]) })
</script>

<template>
  <main class="dashboard-page">
    <section class="dashboard-hero" aria-labelledby="dashboard-hero-title">
      <div class="hero-content">
        <p class="hero-welcome">{{ displayName }}，欢迎回来</p>
        <h2 id="dashboard-hero-title">从企业知识中获得可验证的答案</h2>
        <form class="hero-question" role="search" @submit.prevent="askQuestion">
          <el-input v-model="question" maxlength="1000" size="large" aria-label="输入企业知识问题" placeholder="输入你的问题，例如：员工请假需要走哪些流程？" />
          <el-button type="primary" size="large" native-type="submit" :disabled="!question.trim()">提问</el-button>
        </form>
        <p class="hero-description">基于企业知识库，为你提供准确、可追溯的回答。</p>
      </div>

      <div class="hero-visual" aria-hidden="true">
        <svg viewBox="0 0 320 220">
          <path class="visual-line" d="M24 48h102M194 48h102M44 178h232" />
          <rect class="visual-sheet visual-sheet-back" x="86" y="34" width="142" height="152" rx="8" />
          <rect class="visual-sheet" x="70" y="50" width="142" height="152" rx="8" />
          <path class="visual-fold" d="M166 50v38h46" />
          <path class="visual-copy" d="M94 112h78M94 132h92M94 152h60" />
          <path class="visual-shield" d="M222 112 266 96l44 16v34c0 30-19 52-44 62-25-10-44-32-44-62z" />
          <path class="visual-check" d="m246 151 14 14 28-32" />
        </svg>
      </div>
    </section>

    <div class="dashboard-secondary-grid">
      <DataSurface title="知识库概况" description="来自当前知识库的真实统计">
        <AsyncState v-if="statsLoading" state="loading" title="正在加载知识库概况" />
        <AsyncState v-else-if="statsError" state="error" title="知识库概况加载失败" :description="statsError" @retry="loadStats" />
        <template v-else>
          <dl class="knowledge-metrics">
            <div>
              <span class="metric-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h9l4 4v14H6zM15 3v5h4M9 13h6M9 17h6" /></svg></span>
              <div><dd>{{ stats?.document_count ?? 0 }}</dd><dt>知识文档</dt></div>
            </div>
            <div>
              <span class="metric-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 7 8-4 8 4-8 4zM4 12l8 4 8-4M4 17l8 4 8-4" /></svg></span>
              <div><dd>{{ stats?.chunk_count ?? 0 }}</dd><dt>知识库片段</dt></div>
            </div>
          </dl>
          <p class="knowledge-summary">当前知识库已收录 {{ stats?.document_count ?? 0 }} 份企业文档，构建 {{ stats?.chunk_count ?? 0 }} 个可检索片段。</p>
          <div class="knowledge-actions"><el-button @click="openDocuments">查看文档</el-button><el-button v-if="canUpload" type="primary" plain @click="openDocuments">上传文档</el-button></div>
        </template>
      </DataSurface>

      <DataSurface title="当前访问范围" description="来自当前登录身份">
        <dl class="access-scope">
          <div><dt>角色</dt><dd>{{ roleLabel(profile?.role?.name) }}</dd></div>
          <div><dt>部门</dt><dd>{{ profile?.department?.name || '未分配' }}</dd></div>
          <div><dt>团队</dt><dd>{{ profile?.team?.name || '未分配' }}</dd></div>
          <div><dt>账号状态</dt><dd><span :class="['account-status', profile?.status]"><i aria-hidden="true" />{{ profile?.status === 'active' ? '账号已启用' : '账号未启用' }}</span></dd></div>
        </dl>
      </DataSurface>
    </div>

    <DataSurface title="最近上传" description="当前账号有权查看的最近文档">
      <template #actions><el-button text :loading="documentsLoading" @click="loadRecentDocuments">刷新</el-button></template>
      <AsyncState v-if="documentsLoading" state="loading" title="正在加载最近文档" />
      <AsyncState v-else-if="documentsError" state="error" title="最近文档加载失败" :description="documentsError" @retry="loadRecentDocuments" />
      <template v-else-if="recentDocuments.length">
        <div class="recent-table" role="table" aria-label="最近上传文档">
          <div class="recent-table-header" role="row"><span>文档名称</span><span>文件类型</span><span>可见范围</span><span>上传时间</span><span>文件大小</span><span>操作</span></div>
          <div v-for="document in recentDocuments" :key="document.document_id" class="recent-row" role="row">
            <div class="recent-document"><span class="file-mark">{{ fileType(document).slice(0, 5) }}</span><span><strong>{{ document.filename }}</strong><small v-if="document.folder_name">{{ document.folder_name }}</small></span></div>
            <span>{{ fileType(document) }}</span>
            <span class="visibility-label">{{ visibilityLabels[document.visibility] }}</span>
            <time v-if="document.uploaded_at" :datetime="document.uploaded_at">{{ formatDate(document.uploaded_at) }}</time><span v-else>—</span>
            <span>{{ formatSize(document.file_size ?? document.size) || '—' }}</span>
            <el-button link type="primary" @click="openDocuments">查看</el-button>
          </div>
        </div>

        <div class="recent-mobile-list">
          <article v-for="document in recentDocuments" :key="document.document_id">
            <div class="recent-mobile-heading"><div class="recent-document"><span class="file-mark">{{ fileType(document).slice(0, 5) }}</span><span><strong>{{ document.filename }}</strong><small v-if="document.folder_name">{{ document.folder_name }}</small></span></div><el-button link type="primary" @click="openDocuments">查看</el-button></div>
            <div class="recent-mobile-meta"><span class="visibility-label">{{ visibilityLabels[document.visibility] }}</span><span>{{ fileType(document) }}</span><time v-if="document.uploaded_at" :datetime="document.uploaded_at">{{ formatDate(document.uploaded_at) }}</time></div>
          </article>
        </div>
      </template>
      <EmptyState v-else title="暂无最近上传文档" description="当前账号可访问的知识库中暂时没有文档。" />
    </DataSurface>
  </main>
</template>

<style scoped>
.dashboard-page { display: grid; gap: var(--space-6); width: 100%; max-width: 1480px; margin: 0 auto; }
.dashboard-hero { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) 340px; min-height: 300px; overflow: hidden; border: 1px solid #dbeafe; border-radius: 10px; background: linear-gradient(135deg, #f8fbff 0%, #eff6ff 100%); }
.hero-content { position: relative; z-index: 1; align-self: center; max-width: 820px; padding: var(--space-10); }
.hero-welcome { margin: 0 0 var(--space-3); color: var(--color-text-secondary); font-size: var(--font-size-body); }
.hero-content h2 { margin: 0; color: var(--color-text); font-size: 30px; font-weight: 600; line-height: 1.3; letter-spacing: -.03em; }
.hero-question { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--space-3); margin-top: var(--space-8); }
.hero-question :deep(.el-input__wrapper) { min-height: 52px; padding-inline: var(--space-4); border-radius: var(--radius-lg); background: rgba(255, 255, 255, .96); box-shadow: 0 0 0 1px #bfdbfe inset; }
.hero-question :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 2px var(--color-primary) inset; }
.hero-question .el-button { min-width: 96px; min-height: 52px; border-radius: var(--radius-lg); }
.hero-description { margin: var(--space-3) 0 0; color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
.hero-visual { display: grid; place-items: center; padding: var(--space-6); }
.hero-visual svg { width: min(320px, 100%); height: auto; }
.visual-line { fill: none; stroke: #dbeafe; stroke-width: 1; }.visual-sheet { fill: #fff; stroke: #93c5fd; stroke-width: 1.5; }.visual-sheet-back { fill: #dbeafe; stroke: #bfdbfe; }.visual-fold, .visual-copy { fill: none; stroke: #60a5fa; stroke-linecap: round; stroke-linejoin: round; stroke-width: 6; }.visual-fold { stroke-width: 1.5; }.visual-shield { fill: #2563eb; stroke: #1d4ed8; stroke-width: 1.5; }.visual-check { fill: none; stroke: #fff; stroke-linecap: round; stroke-linejoin: round; stroke-width: 5; }
.dashboard-secondary-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(320px, .65fr); gap: var(--space-6); }
.knowledge-metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 0; }
.knowledge-metrics > div { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-6); border-right: 1px solid var(--color-border); }.knowledge-metrics > div:last-child { border-right: 0; }
.metric-icon { display: grid; place-items: center; width: 48px; height: 48px; flex: 0 0 auto; color: var(--color-primary); border: 1px solid #bfdbfe; border-radius: var(--radius-lg); background: var(--color-primary-subtle); }.metric-icon svg { width: 24px; height: 24px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.7; }
.knowledge-metrics dt { margin-top: var(--space-1); color: var(--color-text-secondary); font-size: var(--font-size-secondary); }.knowledge-metrics dd { margin: 0; color: var(--color-text); font-size: 28px; font-variant-numeric: tabular-nums; font-weight: 600; }
.knowledge-summary { margin: 0; padding: var(--space-4) var(--space-6); color: var(--color-text-secondary); border-top: 1px solid var(--color-border); font-size: var(--font-size-secondary); line-height: 1.6; }.knowledge-actions { display: flex; gap: var(--space-3); padding: 0 var(--space-6) var(--space-6); }
.access-scope { margin: 0; }.access-scope > div { display: grid; grid-template-columns: 96px minmax(0, 1fr); gap: var(--space-4); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--color-border); }.access-scope > div:last-child { border-bottom: 0; }.access-scope dt { color: var(--color-text-secondary); font-size: var(--font-size-secondary); }.access-scope dd { overflow: hidden; margin: 0; color: var(--color-text); font-size: var(--font-size-body); font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
.account-status { display: inline-flex; align-items: center; gap: var(--space-2); color: var(--color-error); font-size: var(--font-size-secondary); }.account-status.active { color: var(--color-success); }.account-status i { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.recent-table-header, .recent-row { display: grid; grid-template-columns: minmax(260px, 2fr) 110px 120px 180px 100px 64px; align-items: center; gap: var(--space-4); padding: var(--space-3) var(--space-4); }.recent-table-header { min-height: 44px; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); background: var(--color-surface); font-size: var(--font-size-secondary); }.recent-row { min-height: 64px; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); font-size: var(--font-size-secondary); }.recent-row:last-child { border-bottom: 0; }.recent-document { display: flex; align-items: center; gap: var(--space-3); min-width: 0; }.recent-document > span:last-child { min-width: 0; }.recent-document strong, .recent-document small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.recent-document strong { color: var(--color-text); font-size: var(--font-size-body); font-weight: 500; }.recent-document small { margin-top: var(--space-1); color: var(--color-text-secondary); font-size: var(--font-size-secondary); }.file-mark { display: grid; place-items: center; min-width: 40px; height: 36px; padding: 0 var(--space-2); color: var(--color-primary); border: 1px solid #bfdbfe; border-radius: var(--radius-md); background: var(--color-primary-subtle); font-size: var(--font-size-secondary); font-weight: 600; }.visibility-label { display: inline-flex; width: fit-content; padding: 2px var(--space-2); color: var(--color-primary); border: 1px solid #bfdbfe; border-radius: var(--radius-sm); background: var(--color-primary-subtle); white-space: nowrap; }time { font-variant-numeric: tabular-nums; }.recent-mobile-list { display: none; }
@media (max-width: 1120px) { .dashboard-hero { grid-template-columns: minmax(0, 1fr) 260px; }.hero-visual { padding-left: 0; }.recent-table-header, .recent-row { grid-template-columns: minmax(220px, 2fr) 90px 110px 160px 64px; }.recent-table-header > :nth-child(5), .recent-row > :nth-child(5) { display: none; } }
@media (max-width: 860px) { .dashboard-hero { grid-template-columns: 1fr; }.hero-content { padding: var(--space-8); }.hero-visual { display: none; }.dashboard-secondary-grid { grid-template-columns: 1fr; }.recent-table { display: none; }.recent-mobile-list { display: grid; }.recent-mobile-list article { padding: var(--space-4); border-bottom: 1px solid var(--color-border); }.recent-mobile-list article:last-child { border-bottom: 0; }.recent-mobile-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); }.recent-mobile-meta { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-3); padding-top: var(--space-3); color: var(--color-text-secondary); border-top: 1px solid var(--color-border); font-size: var(--font-size-secondary); } }
@media (max-width: 560px) { .dashboard-page { gap: var(--space-4); }.dashboard-hero { min-height: 0; border-radius: var(--radius-lg); }.hero-content { padding: var(--space-6) var(--space-4); }.hero-content h2 { font-size: 24px; }.hero-question { grid-template-columns: 1fr; margin-top: var(--space-6); }.hero-question .el-button { width: 100%; }.knowledge-metrics { grid-template-columns: 1fr; }.knowledge-metrics > div { padding: var(--space-4); border-right: 0; border-bottom: 1px solid var(--color-border); }.knowledge-metrics > div:last-child { border-bottom: 0; }.knowledge-actions { flex-direction: column; padding-inline: var(--space-4); }.knowledge-actions .el-button { width: 100%; margin: 0; } }
</style>
