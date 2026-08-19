<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DocumentChecked, Lock, Search as SearchIcon } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import DataSurface from '../components/DataSurface.vue'
import EmptyState from '../components/EmptyState.vue'
import AsyncState from '../components/AsyncState.vue'
import SearchResultItem from '../components/search/SearchResultItem.vue'
import { searchKnowledge, type KnowledgeSearchResult } from '../api/search'
import { getApiErrorMessage } from '../api/http'

const route = useRoute()
const router = useRouter()
const initialQuery = typeof route.query.q === 'string' ? route.query.q.slice(0, 1000) : ''
const query = ref(initialQuery)
const submittedQuery = ref('')
const results = ref<KnowledgeSearchResult[]>([])
const loading = ref(false)
const errorMessage = ref('')
const hasSearched = ref(false)

const canSearch = computed(() => Boolean(query.value.trim()) && !loading.value)
const resultDescription = computed(() => {
  if (loading.value) return '正在检索当前权限范围内的企业知识'
  if (errorMessage.value) return '已保留本次搜索词，可重新尝试'
  return `本次返回 ${results.value.length} 条结果`
})

async function performSearch(options: { syncUrl?: boolean } = {}) {
  const normalizedQuery = query.value.trim()
  if (!normalizedQuery || loading.value) return

  query.value = normalizedQuery
  submittedQuery.value = normalizedQuery
  hasSearched.value = true
  loading.value = true
  errorMessage.value = ''
  results.value = []

  if (options.syncUrl !== false && route.query.q !== normalizedQuery) {
    void router.replace({ query: { ...route.query, q: normalizedQuery } })
  }

  try {
    const response = await searchKnowledge({ query: normalizedQuery })
    results.value = response.results
  } catch (error) {
    const fallback = '暂时无法获取检索结果，请重新尝试。'
    const resolvedMessage = getApiErrorMessage(error, fallback)
    errorMessage.value = resolvedMessage.startsWith('Request failed with status code') ? fallback : resolvedMessage
  } finally {
    loading.value = false
  }
}

function goToChat() {
  void router.push({ path: '/chat', query: { q: submittedQuery.value } })
}

onMounted(() => {
  if (query.value.trim()) void performSearch({ syncUrl: false })
})
</script>

<template>
  <main class="search-page">
    <PageHeader title="智能检索" description="在当前访问权限范围内搜索企业知识。" />

    <section class="search-workspace" aria-labelledby="search-form-title">
      <h2 id="search-form-title" class="sr-only">搜索企业知识</h2>
      <form class="search-control" role="search" @submit.prevent="performSearch()">
        <el-input
          v-model="query"
          clearable
          maxlength="1000"
          placeholder="输入关键词、问题或知识描述"
          aria-label="输入搜索内容"
        >
          <template #prefix><el-icon aria-hidden="true"><SearchIcon /></el-icon></template>
        </el-input>
        <el-button class="search-submit" type="primary" native-type="submit" :loading="loading" :disabled="!canSearch">
          搜索
        </el-button>
      </form>
      <p class="permission-note"><el-icon aria-hidden="true"><Lock /></el-icon>仅检索当前账号有权限访问的企业知识</p>
    </section>

    <section v-if="!hasSearched" class="search-intro" aria-label="检索能力说明">
      <p>输入关键词或问题，直接查找相关企业知识片段。</p>
      <ul>
        <li><el-icon aria-hidden="true"><SearchIcon /></el-icon><span>按语义查找知识</span></li>
        <li><el-icon aria-hidden="true"><Lock /></el-icon><span>仅返回有权限内容</span></li>
        <li><el-icon aria-hidden="true"><DocumentChecked /></el-icon><span>直接查看原始知识片段</span></li>
      </ul>
    </section>

    <DataSurface v-else class="search-results" title="搜索结果" :description="resultDescription">
      <AsyncState v-if="loading" state="loading" title="正在搜索企业知识" />
      <AsyncState
        v-else-if="errorMessage"
        state="error"
        title="搜索失败"
        :description="errorMessage"
        retry-label="重新搜索"
        @retry="performSearch()"
      />
      <div v-else-if="results.length" class="result-list" role="list" :aria-label="`关于${submittedQuery}的检索结果`">
        <SearchResultItem
          v-for="(result, index) in results"
          :key="`${result.filename || 'result'}-${result.chunk_index ?? index}-${index}`"
          role="listitem"
          :result="result"
          :index="index"
        />
      </div>
      <div v-else class="no-results">
        <EmptyState title="未找到相关知识" description="可以尝试更换关键词或使用更完整的描述。" />
        <el-button plain @click="goToChat">去知识问答</el-button>
      </div>
    </DataSurface>
  </main>
</template>

<style scoped>
:global(.page-container:has(.search-page)) { background: var(--color-background); }

.search-page {
  display: grid;
  gap: var(--space-6);
  width: min(1040px, 100%);
  margin: 0 auto;
}

.search-workspace, .search-intro, .search-results { width: min(1000px, 100%); margin-inline: auto; }

.search-control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  overflow: hidden;
  min-height: 56px;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.search-control:focus-within {
  border-color: #93b4f8;
  box-shadow: 0 0 0 3px rgb(37 99 235 / 10%);
}

.search-control :deep(.el-input__wrapper) {
  min-height: 54px;
  padding-inline: var(--space-4);
  background: transparent;
  box-shadow: none !important;
}

.search-control :deep(.el-input__inner) { color: var(--color-text); font-size: 15px; }
.search-control :deep(.el-input__inner::placeholder) { color: #707070; }
.search-control :deep(.el-input__prefix) { color: var(--color-text-secondary); font-size: 18px; }
.search-submit { min-width: 92px; height: 42px; margin-right: 6px; border-radius: var(--radius-md); }

.permission-note {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: var(--space-3) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-secondary);
  line-height: 1.6;
}

.permission-note .el-icon { flex: 0 0 auto; }

.search-intro {
  display: grid;
  place-items: center;
  min-height: 260px;
  padding: var(--space-8) var(--space-6);
  border-top: 1px solid var(--color-border);
  text-align: center;
}

.search-intro > p { margin: 0; color: var(--color-text-secondary); font-size: var(--font-size-body); line-height: 1.7; }
.search-intro ul { display: flex; flex-wrap: wrap; justify-content: center; gap: var(--space-3) var(--space-6); margin: var(--space-6) 0 0; padding: 0; list-style: none; }
.search-intro li { display: inline-flex; align-items: center; gap: var(--space-2); color: var(--color-text); font-size: var(--font-size-secondary); }
.search-intro li .el-icon { color: var(--color-primary); font-size: 18px; }

.result-list { min-width: 0; }
.no-results { padding-bottom: var(--space-6); text-align: center; }
.no-results :deep(.empty-state) { padding-bottom: var(--space-3); }
.no-results .el-button { min-height: 40px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; margin: -1px; padding: 0; border: 0; clip: rect(0, 0, 0, 0); white-space: nowrap; }

@media (prefers-reduced-motion: reduce) {
  .search-control { transition: none; }
}

@media (max-width: 760px) {
  .search-page { gap: var(--space-4); }
  .search-control { grid-template-columns: minmax(0, 1fr) 84px; }
  .search-control :deep(.el-input__wrapper) { padding-left: var(--space-3); }
  .search-submit { min-width: 76px; }
  .search-intro { min-height: 220px; padding: var(--space-6) var(--space-4); }
  .search-intro ul { align-items: flex-start; flex-direction: column; }
}

@media (max-width: 560px) {
  .search-page { padding-inline: var(--space-1); }
}
</style>
