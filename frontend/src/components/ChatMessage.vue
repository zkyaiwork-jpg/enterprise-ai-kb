<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import SourceReference from './SourceReference.vue'
import type { ChatSource } from '../api/chat'

interface AnswerBlock {
  type: 'paragraph' | 'heading' | 'unordered-list' | 'ordered-list'
  content?: string
  items?: string[]
}

const props = defineProps<{
  messageId: string
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
  pending?: boolean
  error?: string
  createdAt?: string
}>()

defineEmits<{ retry: [] }>()

const openSourceIndex = ref<number | null>(null)
const showAllSources = ref(false)
const visibleSources = computed(() => showAllSources.value ? props.sources || [] : (props.sources || []).slice(0, 3))
const answerBlocks = computed(() => parseAnswer(props.content))

watch(() => props.sources, () => {
  openSourceIndex.value = null
  showAllSources.value = false
})

function formatTime(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString('zh-CN', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  })
}

function parseAnswer(value: string): AnswerBlock[] {
  const blocks: AnswerBlock[] = []
  let paragraphLines: string[] = []
  let listType: 'unordered-list' | 'ordered-list' | null = null
  let listItems: string[] = []

  const flushParagraph = () => {
    if (!paragraphLines.length) return
    blocks.push({ type: 'paragraph', content: paragraphLines.join('\n') })
    paragraphLines = []
  }
  const flushList = () => {
    if (!listType || !listItems.length) return
    blocks.push({ type: listType, items: listItems })
    listType = null
    listItems = []
  }

  for (const rawLine of value.replace(/\r\n/g, '\n').split('\n')) {
    const line = rawLine.trim()
    if (!line) {
      flushParagraph()
      flushList()
      continue
    }
    const heading = line.match(/^#{1,3}\s+(.+)$/)
    const unordered = line.match(/^[-*•]\s+(.+)$/)
    const ordered = line.match(/^\d+[.)、]\s*(.+)$/)
    if (heading) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'heading', content: heading[1] })
    } else if (unordered || ordered) {
      flushParagraph()
      const nextType = unordered ? 'unordered-list' : 'ordered-list'
      if (listType && listType !== nextType) flushList()
      listType = nextType
      listItems.push((unordered || ordered)?.[1] || line)
    } else {
      flushList()
      paragraphLines.push(line)
    }
  }
  flushParagraph()
  flushList()
  return blocks
}

function toggleSource(index: number) {
  openSourceIndex.value = openSourceIndex.value === index ? null : index
}

function toggleAllSources() {
  showAllSources.value = !showAllSources.value
  if (!showAllSources.value && openSourceIndex.value != null && openSourceIndex.value >= 3) openSourceIndex.value = null
}
</script>

<template>
  <article class="chat-message" :class="`chat-message--${role}`" :data-message-id="messageId" :aria-label="role === 'assistant' ? '知识助手回答' : '你的问题'">
    <template v-if="role === 'user'">
      <div class="question-wrap">
        <header class="message-meta">
          <strong>你</strong>
          <time v-if="createdAt" :datetime="createdAt">{{ formatTime(createdAt) }}</time>
        </header>
        <div class="question-block">
          <p>{{ content }}</p>
        </div>
      </div>
    </template>

    <template v-else>
      <header class="message-meta assistant-meta">
        <strong>知识助手</strong>
        <time v-if="createdAt" :datetime="createdAt">{{ formatTime(createdAt) }}</time>
      </header>

      <div v-if="pending" class="query-status">
        <span class="query-indicator" aria-hidden="true" />正在检索知识并生成回答……
      </div>

      <div v-else-if="error" class="answer-error" role="alert">
        <p>{{ error }}</p>
        <button type="button" class="retry-button" @click="$emit('retry')">重新发送</button>
      </div>

      <div v-else class="answer-content">
        <template v-for="(block, index) in answerBlocks" :key="`${block.type}-${index}`">
          <h3 v-if="block.type === 'heading'">{{ block.content }}</h3>
          <ul v-else-if="block.type === 'unordered-list'">
            <li v-for="item in block.items" :key="item">{{ item }}</li>
          </ul>
          <ol v-else-if="block.type === 'ordered-list'">
            <li v-for="item in block.items" :key="item">{{ item }}</li>
          </ol>
          <p v-else>{{ block.content }}</p>
        </template>
      </div>

      <section v-if="sources?.length && !pending && !error" class="message-sources" aria-label="来源依据">
        <header class="sources-heading"><h3>来源依据</h3><span>{{ sources.length }} 条</span></header>
        <div class="source-list">
          <SourceReference
            v-for="(source, index) in visibleSources"
            :key="`${source.filename || 'source'}-${source.chunk_index ?? index}-${index}`"
            :source="source"
            :index="index"
            :expanded="openSourceIndex === index"
            @toggle="toggleSource(index)"
          />
        </div>
        <button v-if="sources.length > 3" type="button" class="show-all-sources" @click="toggleAllSources">
          {{ showAllSources ? '收起其余来源' : `查看全部 ${sources.length} 条来源` }}
        </button>
      </section>
    </template>
  </article>
</template>

<style scoped>
.chat-message { width: min(800px, 100%); margin-inline: auto; }
.chat-message--assistant { margin-top: var(--space-6); }
.chat-message--assistant + .chat-message--user { margin-top: 56px; }
.question-wrap { width: fit-content; max-width: min(500px, 100%); margin-left: auto; }
.question-wrap .message-meta { justify-content: flex-end; }
.question-block { padding: var(--space-3) var(--space-4); background: #f3f6fa; border-radius: 12px; }
.message-meta { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.message-meta strong { color: var(--color-text); font-size: var(--font-size-secondary); font-weight: 600; }
.message-meta time { color: var(--color-text-secondary); font-size: var(--font-size-secondary); font-variant-numeric: tabular-nums; }
.question-block p { margin: 0; color: var(--color-text); font-size: 16px; line-height: 1.7; overflow-wrap: anywhere; white-space: pre-wrap; }
.assistant-meta { width: min(760px, 100%); margin-bottom: var(--space-3); }
.answer-content, .query-status, .answer-error { width: min(760px, 100%); }
.answer-content { color: var(--color-text); font-size: 16px; line-height: 1.75; }
.answer-content p { margin: 0 0 var(--space-4); overflow-wrap: anywhere; white-space: pre-wrap; }
.answer-content p:last-child { margin-bottom: 0; }
.answer-content h3 { margin: var(--space-6) 0 var(--space-3); font-size: var(--font-size-section-title); line-height: 1.5; }
.answer-content ul, .answer-content ol { margin: 0 0 var(--space-4); padding-left: var(--space-6); }
.answer-content li { padding-left: var(--space-1); }
.answer-content li + li { margin-top: var(--space-2); }
.query-status { display: flex; align-items: center; gap: var(--space-2); min-height: 48px; color: var(--color-text-secondary); font-size: var(--font-size-body); }
.query-indicator { width: 8px; height: 8px; border-radius: 50%; background: var(--color-primary); animation: query-pulse 1.2s ease-in-out infinite; }
@keyframes query-pulse { 0%, 100% { opacity: .35; } 50% { opacity: 1; } }
.answer-error { padding-block: var(--space-2); }
.answer-error p { margin: 0; color: var(--color-text); font-size: var(--font-size-body); line-height: 1.7; }
.retry-button { margin-top: var(--space-3); padding: var(--space-2) var(--space-3); color: var(--color-error); border: 1px solid #fecaca; border-radius: var(--radius-md); background: var(--color-background); cursor: pointer; }
.retry-button:hover { background: #fff7f7; }
.message-sources { width: min(800px, 100%); margin-top: var(--space-6); }
.sources-heading { display: flex; align-items: baseline; gap: var(--space-2); margin-bottom: var(--space-3); }
.sources-heading h3 { margin: 0; color: var(--color-text); font-size: var(--font-size-body); font-weight: 600; }
.sources-heading span { color: var(--color-text-secondary); font-size: var(--font-size-secondary); }
.source-list { overflow: hidden; background: var(--color-background); border: 1px solid var(--color-border); border-radius: var(--radius-lg); }
.show-all-sources { margin-top: var(--space-3); padding: var(--space-2) 0; color: var(--color-primary); border: 0; background: transparent; font-size: var(--font-size-secondary); cursor: pointer; }
.show-all-sources:hover { color: var(--color-primary-hover); text-decoration: underline; text-underline-offset: 3px; }
@media (prefers-reduced-motion: reduce) { .query-indicator { animation: none; } }
@media (max-width: 760px) {
  .chat-message--assistant + .chat-message--user { margin-top: var(--space-12); }
  .question-wrap { max-width: 85%; }
  .question-block { padding: var(--space-3); }
  .question-block p, .answer-content { font-size: 15px; }
  .assistant-meta, .answer-content, .query-status, .answer-error, .message-sources { width: 100%; }
}
</style>
