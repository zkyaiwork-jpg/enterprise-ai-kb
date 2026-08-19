<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useRoute } from 'vue-router'
import ChatInput from '../components/ChatInput.vue'
import ChatMessage from '../components/ChatMessage.vue'
import ChatWelcome from '../components/ChatWelcome.vue'
import { sendChatMessage, type ChatSource } from '../api/chat'
import { getApiErrorMessage } from '../api/http'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
  pending?: boolean
  error?: string
  retryContent?: string
  createdAt?: string
}

const route = useRoute()
const messages = ref<Message[]>([])
const question = ref(typeof route.query.q === 'string' ? route.query.q.slice(0, 1000) : '')
const sending = ref(false)
const conversationId = ref<number>()
const messageList = ref<HTMLElement>()
const liveStatus = ref('')

async function scrollToMessage(messageId: string, block: ScrollLogicalPosition = 'nearest') {
  await nextTick()
  const behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
  messageList.value
    ?.querySelector<HTMLElement>(`[data-message-id="${messageId}"]`)
    ?.scrollIntoView({ behavior, block })
}

function isNearPageBottom() {
  return document.documentElement.scrollHeight - (window.scrollY + window.innerHeight) < 240
}

async function requestAnswer(content: string, pendingId: string, followResponse = true) {
  sending.value = true
  liveStatus.value = '正在检索知识并生成回答'
  if (followResponse) await scrollToMessage(pendingId)
  const shouldFollow = followResponse && isNearPageBottom()
  try {
    const response = await sendChatMessage({
      question: content,
      ...(conversationId.value ? { conversation_id: conversationId.value } : {}),
    })
    conversationId.value = response.conversation_id
    const index = messages.value.findIndex((message) => message.id === pendingId)
    if (index >= 0) {
      messages.value[index] = {
        id: String(response.id),
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        createdAt: response.created_at,
      }
      liveStatus.value = '回答已生成'
      if (shouldFollow) await scrollToMessage(String(response.id), 'start')
    }
  } catch (error) {
    const index = messages.value.findIndex((message) => message.id === pendingId)
    if (index >= 0) {
      messages.value[index] = {
        id: pendingId,
        role: 'assistant',
        content: '',
        error: getApiErrorMessage(error, '发送失败，请稍后重试。'),
        retryContent: content,
      }
      liveStatus.value = '回答失败，可以重新发送'
      if (shouldFollow) await scrollToMessage(pendingId)
    }
    if (!question.value.trim()) question.value = content
  } finally {
    sending.value = false
  }
}

function send() {
  const content = question.value.trim()
  if (!content || sending.value) return
  const timestamp = Date.now()
  question.value = ''
  messages.value.push({
    id: `user-${timestamp}`,
    role: 'user',
    content,
    createdAt: new Date(timestamp).toISOString(),
  })
  const pendingId = `pending-${timestamp}`
  messages.value.push({ id: pendingId, role: 'assistant', content: '', pending: true })
  void requestAnswer(content, pendingId)
}

function retry(message: Message) {
  if (!message.retryContent || sending.value) return
  const index = messages.value.findIndex((item) => item.id === message.id)
  if (index < 0) return
  messages.value[index] = {
    id: message.id,
    role: 'assistant',
    content: '',
    pending: true,
    retryContent: message.retryContent,
  }
  void requestAnswer(message.retryContent, message.id, false)
}
</script>

<template>
  <main class="knowledge-chat-page">
    <ChatWelcome v-if="messages.length === 0" v-model="question" :sending="sending" @send="send" />

    <section v-else class="conversation-shell" aria-label="知识问答对话">
      <header class="conversation-heading">
        <p>回答内容会附带可核验的知识来源</p>
      </header>
      <div class="knowledge-chat-workspace">
        <p class="sr-only" role="status" aria-live="polite">{{ liveStatus }}</p>
        <div ref="messageList" class="knowledge-message-list" role="log" aria-label="问答记录" :aria-busy="sending">
          <ChatMessage
            v-for="message in messages"
            :key="message.id"
            :message-id="message.id"
            :role="message.role"
            :content="message.content"
            :sources="message.sources"
            :pending="message.pending"
            :error="message.error"
            :created-at="message.createdAt"
            @retry="retry(message)"
          />
        </div>
        <div class="conversation-composer">
          <ChatInput v-model="question" :sending="sending" @send="send" />
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.knowledge-chat-page {
  width: 100%;
  min-width: 0;
  min-height: calc(100vh - 112px);
  background: var(--color-background);
  box-shadow: 0 0 0 100vmax var(--color-background);
  clip-path: inset(0 -100vmax);
}
.conversation-shell { width: min(1040px, 100%); margin: 0 auto; }
.conversation-heading { width: min(800px, 100%); margin: 0 auto var(--space-8); padding-top: var(--space-2); }
.conversation-heading p { margin: 0; color: #888888; font-size: var(--font-size-secondary); line-height: 1.6; }
.knowledge-chat-workspace { min-width: 0; }
.knowledge-message-list { min-width: 0; }
.conversation-composer {
  position: sticky;
  bottom: 0;
  z-index: 2;
  width: min(800px, 100%);
  margin: var(--space-10) auto 0;
  padding: var(--space-4) 0 max(var(--space-2), env(safe-area-inset-bottom));
  background: var(--color-background);
}
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; margin: -1px; padding: 0; border: 0; clip: rect(0, 0, 0, 0); white-space: nowrap; }
@media (max-width: 760px) {
  .knowledge-chat-page { min-height: calc(100vh - 88px); }
  .conversation-heading { margin-bottom: var(--space-6); padding-top: 0; }
  .conversation-composer { margin-top: var(--space-6); padding-top: var(--space-3); }
}
</style>
