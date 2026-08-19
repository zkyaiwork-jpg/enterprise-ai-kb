<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import type { KnowledgeSearchResult } from '../../api/search'

const props = defineProps<{
  result: KnowledgeSearchResult
  index: number
}>()

const expanded = ref(false)
const componentId = useId()
const contentId = `${componentId}-content`
const title = computed(() => props.result.filename || '未命名文档')
const fileType = computed(() => props.result.file_type?.replace('.', '').toUpperCase())
const hasTechnicalInfo = computed(() => (
  props.result.chunk_index != null || Number.isFinite(props.result.distance)
))

function toggleExpanded() {
  expanded.value = !expanded.value
}
</script>

<template>
  <article class="search-result-item">
    <span class="result-index" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>

    <div class="result-content">
      <header class="result-heading">
        <h3>{{ title }}</h3>
        <div v-if="result.folder_name || fileType || result.chunk_index != null" class="result-meta">
          <span v-if="result.folder_name">{{ result.folder_name }}</span>
          <span v-if="fileType">{{ fileType }}</span>
          <span v-if="result.chunk_index != null">知识片段 #{{ result.chunk_index }}</span>
        </div>
      </header>

      <p
        v-if="result.content"
        :id="contentId"
        class="result-excerpt"
        :class="{ 'is-expanded': expanded }"
      >
        {{ result.content }}
      </p>
      <p v-else class="result-excerpt result-excerpt--empty">该结果未返回可展示的知识片段。</p>

      <div v-if="result.content" class="result-actions">
        <button
          type="button"
          class="text-action"
          :aria-expanded="expanded"
          :aria-controls="contentId"
          @click="toggleExpanded"
        >
          {{ expanded ? '收起原文' : '展开原文' }}
        </button>

        <details v-if="expanded && hasTechnicalInfo" class="technical-details">
          <summary>技术信息</summary>
          <dl>
            <div v-if="result.chunk_index != null">
              <dt>片段编号</dt>
              <dd>{{ result.chunk_index }}</dd>
            </div>
            <div v-if="Number.isFinite(result.distance)">
              <dt>检索距离</dt>
              <dd>{{ result.distance.toFixed(4) }}</dd>
            </div>
          </dl>
        </details>
      </div>
    </div>
  </article>
</template>

<style scoped>
.search-result-item {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: var(--space-3);
  padding: 20px;
  transition: background-color 160ms ease;
}

.search-result-item + .search-result-item { border-top: 1px solid var(--color-border); }
.search-result-item:hover { background: #fafafa; }

.result-index {
  padding-top: 2px;
  color: var(--color-primary);
  font-size: var(--font-size-secondary);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.result-content { min-width: 0; }
.result-heading h3 {
  margin: 0;
  color: var(--color-text);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-2);
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: var(--font-size-secondary);
  line-height: 1.5;
}

.result-meta span + span::before { margin-right: var(--space-2); content: '·'; }

.result-excerpt {
  display: -webkit-box;
  overflow: hidden;
  margin: var(--space-3) 0 0;
  color: var(--color-text);
  font-size: 15px;
  line-height: 1.75;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.result-excerpt.is-expanded { display: block; overflow: visible; }
.result-excerpt--empty { color: var(--color-text-secondary); }

.result-actions {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.text-action {
  min-height: 40px;
  padding: 0;
  color: var(--color-primary);
  border: 0;
  background: transparent;
  font-size: var(--font-size-secondary);
  cursor: pointer;
}

.text-action:hover { color: var(--color-primary-hover); text-decoration: underline; text-underline-offset: 3px; }
.technical-details { width: 100%; color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
.technical-details summary { width: fit-content; min-height: 40px; padding: 10px 0; cursor: pointer; }
.technical-details dl { display: grid; grid-template-columns: repeat(2, minmax(0, 180px)); gap: var(--space-2) var(--space-6); margin: 0; padding: var(--space-3); background: var(--color-surface); border-radius: var(--radius-md); }
.technical-details dl > div { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: var(--space-2); }
.technical-details dt { color: var(--color-text-secondary); }
.technical-details dd { margin: 0; color: var(--color-text); font-variant-numeric: tabular-nums; }

@media (prefers-reduced-motion: reduce) {
  .search-result-item { transition: none; }
}

@media (max-width: 760px) {
  .search-result-item { grid-template-columns: 28px minmax(0, 1fr); gap: var(--space-2); padding: var(--space-4); }
  .result-meta span + span::before { margin-right: var(--space-2); }
  .technical-details dl { grid-template-columns: 1fr; }
}
</style>
