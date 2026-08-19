<script setup lang="ts">
import { computed, useId } from 'vue'
import type { ChatSource } from '../api/chat'

const props = withDefaults(defineProps<{ source: ChatSource; index: number; expanded?: boolean }>(), { expanded: false })
defineEmits<{ toggle: [] }>()

const componentId = useId()
const summaryId = `${componentId}-summary`
const detailId = `${componentId}-detail`
const title = computed(() => props.source.filename || props.source.folder_name || `来源 ${props.index + 1}`)
const preview = computed(() => props.source.content?.replace(/\s+/g, ' ').trim() || '')
const formattedDistance = computed(() => typeof props.source.distance === 'number' ? props.source.distance.toFixed(4) : undefined)
const hasTechnicalInfo = computed(() => Boolean(
  props.source.file_type || props.source.folder_name || props.source.chunk_index != null || formattedDistance.value,
))
</script>

<template>
  <article class="source-reference" :class="{ 'is-expanded': expanded }">
    <button
      :id="summaryId"
      type="button"
      class="source-summary"
      :aria-expanded="expanded"
      :aria-controls="detailId"
      @click="$emit('toggle')"
    >
      <span class="source-index">{{ String(index + 1).padStart(2, '0') }}</span>
      <span class="source-overview">
        <strong>{{ title }}</strong>
        <small v-if="source.folder_name || source.file_type">
          <span v-if="source.folder_name">{{ source.folder_name }}</span>
          <span v-if="source.file_type">{{ source.file_type.toUpperCase() }}</span>
        </small>
        <span v-if="preview" class="source-preview">{{ preview }}</span>
      </span>
      <svg class="source-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m8 10 4 4 4-4" /></svg>
    </button>

    <div v-if="expanded" :id="detailId" class="source-detail" role="region" :aria-labelledby="summaryId">
      <h4>来源片段</h4>
      <blockquote v-if="source.content">{{ source.content }}</blockquote>
      <p v-else class="source-content-empty">该来源未返回文本片段。</p>

      <details v-if="hasTechnicalInfo" class="source-technical">
        <summary>技术信息</summary>
        <dl>
          <div v-if="source.file_type"><dt>文件类型</dt><dd>{{ source.file_type.toUpperCase() }}</dd></div>
          <div v-if="source.folder_name"><dt>文件夹</dt><dd>{{ source.folder_name }}</dd></div>
          <div v-if="source.chunk_index != null"><dt>片段编号</dt><dd>{{ source.chunk_index }}</dd></div>
          <div v-if="formattedDistance"><dt>检索距离</dt><dd>{{ formattedDistance }}</dd></div>
        </dl>
      </details>
    </div>
  </article>
</template>

<style scoped>
.source-reference + .source-reference { border-top: 1px solid var(--color-border); }
.source-summary { display: grid; grid-template-columns: 32px minmax(0, 1fr) 20px; align-items: start; gap: var(--space-3); width: 100%; min-height: 64px; padding: var(--space-3) var(--space-4); color: var(--color-text); border: 0; background: transparent; text-align: left; cursor: pointer; }
.source-summary:hover { background: var(--color-surface); }
.source-index { padding-top: 1px; color: var(--color-primary); font-size: var(--font-size-secondary); font-variant-numeric: tabular-nums; font-weight: 600; }
.source-overview { min-width: 0; }
.source-overview strong, .source-overview small, .source-preview { display: block; }
.source-overview strong { overflow: hidden; color: var(--color-text); font-size: var(--font-size-body); font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
.source-overview small { margin-top: 3px; color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
.source-overview small span + span::before { margin: 0 var(--space-2); content: '·'; }
.source-preview { display: -webkit-box; overflow: hidden; margin-top: var(--space-2); color: var(--color-text-secondary); font-size: var(--font-size-secondary); line-height: 1.55; overflow-wrap: anywhere; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.source-chevron { width: 18px; height: 18px; margin-top: 1px; color: var(--color-text-secondary); fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.75; transition: transform 160ms ease; }
.is-expanded .source-chevron { transform: rotate(180deg); }
.source-detail { padding: 0 var(--space-4) var(--space-4) 60px; }
.source-detail h4 { margin: 0 0 var(--space-2); color: var(--color-text); font-size: var(--font-size-secondary); font-weight: 600; }
.source-detail blockquote { margin: 0; padding: var(--space-3) var(--space-4); color: var(--color-text); background: var(--color-surface); border-left: 1px solid var(--color-primary); font-size: var(--font-size-body); line-height: 1.75; overflow-wrap: anywhere; white-space: pre-wrap; }
.source-content-empty { margin: 0; color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
.source-technical { margin-top: var(--space-3); }
.source-technical summary { width: fit-content; color: var(--color-text-secondary); font-size: var(--font-size-secondary); cursor: pointer; }
.source-technical dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-2) var(--space-6); margin: var(--space-3) 0 0; padding-top: var(--space-3); border-top: 1px solid var(--color-border); }
.source-technical dl > div { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: var(--space-2); }
.source-technical dt, .source-technical dd { font-size: var(--font-size-secondary); line-height: 1.5; }
.source-technical dt { color: var(--color-text-secondary); }
.source-technical dd { min-width: 0; margin: 0; color: var(--color-text); overflow-wrap: anywhere; }
@media (prefers-reduced-motion: reduce) { .source-chevron { transition: none; } }
@media (max-width: 760px) {
  .source-summary { grid-template-columns: 28px minmax(0, 1fr) 18px; gap: var(--space-2); padding: var(--space-3); }
  .source-detail { padding: 0 var(--space-3) var(--space-3); }
  .source-technical dl { grid-template-columns: 1fr; }
}
</style>
