<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { DocumentChecked, EditPen, Search } from '@element-plus/icons-vue'
import ChatComposer from './ChatComposer.vue'

defineProps<{ modelValue: string; sending: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; send: [] }>()

const composer = ref<InstanceType<typeof ChatComposer>>()
const quickQuestions = ['知识问答是什么', '员工请假流程', '员工报销申请提价'] as const
const guides = [
  { title: '提出问题', description: '输入与企业制度、流程、规范相关的问题', icon: EditPen },
  { title: '检索知识', description: '在你的访问权限范围内检索相关知识', icon: Search },
  { title: '获得回答', description: '基于检索到的知识生成回答，并提供来源证据', icon: DocumentChecked },
] as const

async function selectQuickQuestion(value: string) {
  emit('update:modelValue', value)
  await nextTick()
  composer.value?.focus()
}
</script>

<template>
  <section class="chat-welcome" aria-labelledby="chat-welcome-title">
    <header class="welcome-heading">
      <h1 id="chat-welcome-title">知识问答</h1>
      <p>基于企业知识库，为你提供准确、可追溯的回答</p>
    </header>

    <ChatComposer
      ref="composer"
      class="welcome-composer"
      :model-value="modelValue"
      :sending="sending"
      variant="welcome"
      placeholder="输入你的问题，例如：员工请假需要走哪些流程？"
      label="输入你的问题"
      hint="Enter 发送 · Shift + Enter 换行 · 回答内容基于企业知识库生成"
      autofocus
      @update:model-value="$emit('update:modelValue', $event)"
      @send="$emit('send')"
    />

    <div class="quick-questions" aria-label="快捷问题">
      <button
        v-for="quickQuestion in quickQuestions"
        :key="quickQuestion"
        type="button"
        @click="selectQuickQuestion(quickQuestion)"
      >
        {{ quickQuestion }}
      </button>
    </div>

    <div class="welcome-divider" />

    <section class="usage-guide" aria-labelledby="usage-guide-title">
      <h2 id="usage-guide-title">使用说明</h2>
      <div class="guide-grid">
        <article v-for="guide in guides" :key="guide.title">
          <el-icon aria-hidden="true"><component :is="guide.icon" /></el-icon>
          <div>
            <h3>{{ guide.title }}</h3>
            <p>{{ guide.description }}</p>
          </div>
        </article>
      </div>
    </section>

  </section>
</template>

<style scoped>
.chat-welcome {
  width: min(960px, 100%);
  margin: 0 auto;
  padding: clamp(32px, 7vh, 72px) 0 var(--space-6);
}
.welcome-heading { text-align: center; }
.welcome-heading h1 {
  margin: 0;
  color: var(--color-text);
  font-size: clamp(25px, 3vw, 28px);
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: -.025em;
}
.welcome-heading p {
  margin: var(--space-3) 0 0;
  color: var(--color-text-secondary);
  font-size: 15px;
  line-height: 1.7;
}
.welcome-composer {
  margin-top: var(--space-8);
}
.quick-questions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin-top: var(--space-4);
}
.quick-questions button {
  min-height: 44px;
  padding: var(--space-2) var(--space-4);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-background);
  cursor: pointer;
  transition: color 160ms ease, border-color 160ms ease, background-color 160ms ease;
}
.quick-questions button:hover { color: var(--color-primary); border-color: #bfdbfe; background: var(--color-primary-subtle); }
.welcome-divider { height: 1px; margin: var(--space-8) 0; background: var(--color-border); }
.usage-guide h2 { margin: 0 0 var(--space-4); font-size: var(--font-size-section-title); font-weight: 600; }
.guide-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-3); }
.guide-grid article {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid transparent;
  border-radius: var(--radius-lg);
}
.guide-grid article > .el-icon { flex: 0 0 auto; width: 20px; height: 20px; margin-top: 1px; color: var(--color-primary); }
.guide-grid h3 { margin: 0; color: var(--color-text); font-size: var(--font-size-body); font-weight: 600; }
.guide-grid p { margin: var(--space-2) 0 0; color: var(--color-text-secondary); font-size: var(--font-size-secondary); line-height: 1.65; }

@media (max-width: 700px) {
  .chat-welcome { padding-top: var(--space-6); }
  .welcome-heading { text-align: left; }
  .welcome-heading p { font-size: var(--font-size-body); }
  .welcome-composer { margin-top: var(--space-6); }
  .quick-questions, .guide-grid { grid-template-columns: 1fr; }
  .quick-questions { gap: var(--space-2); }
  .quick-questions button { text-align: left; }
  .welcome-divider { margin: var(--space-6) 0; }
}
</style>
