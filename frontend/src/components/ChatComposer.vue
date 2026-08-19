<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { InputInstance } from 'element-plus'
import { ChatDotRound } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  modelValue: string
  sending: boolean
  variant?: 'welcome' | 'compact'
  placeholder?: string
  label?: string
  hint?: string
  autofocus?: boolean
}>(), {
  variant: 'compact',
  placeholder: '继续提问',
  label: '输入问题',
  hint: 'Enter 发送 · Shift + Enter 换行',
  autofocus: false,
})

const emit = defineEmits<{ 'update:modelValue': [value: string]; send: [] }>()
const questionInput = ref<InputInstance>()
const autosize = computed(() => props.variant === 'welcome'
  ? { minRows: 5, maxRows: 9 }
  : { minRows: 2, maxRows: 6 })

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    if (props.modelValue.trim() && !props.sending) emit('send')
  }
}

function focus() {
  questionInput.value?.focus()
}

onMounted(() => {
  if (props.autofocus) focus()
})

defineExpose({ focus })
</script>

<template>
  <div class="chat-composer" :class="`chat-composer--${variant}`">
    <div class="composer-surface">
      <el-input
        ref="questionInput"
        :model-value="modelValue"
        type="textarea"
        :autosize="autosize"
        resize="none"
        maxlength="1000"
        :placeholder="placeholder"
        :aria-label="label"
        @update:model-value="$emit('update:modelValue', $event)"
        @keydown="handleKeydown"
      />
      <div class="composer-actions">
        <el-button
          class="composer-submit"
          type="primary"
          :loading="sending"
          :disabled="!modelValue.trim() || sending"
          @click="$emit('send')"
        >
          <el-icon aria-hidden="true"><ChatDotRound /></el-icon>
          提问
        </el-button>
      </div>
    </div>
    <p v-if="hint" class="composer-hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.chat-composer { width: 100%; }
.composer-surface {
  overflow: hidden;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgb(17 24 39 / 4%);
  transition: border-color 160ms ease, box-shadow 160ms ease;
}
.composer-surface:focus-within {
  border-color: #93b4f8;
  box-shadow: 0 4px 16px rgb(37 99 235 / 6%), 0 0 0 3px rgb(37 99 235 / 10%);
}
.composer-surface :deep(.el-textarea__inner) {
  padding: var(--space-4) var(--space-4) var(--space-2);
  color: var(--color-text);
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none !important;
  font-size: 15px;
  line-height: 1.7;
}
.composer-surface :deep(.el-textarea__inner::placeholder) { color: #707070; }
.chat-composer--welcome .composer-surface :deep(.el-textarea__inner) {
  min-height: 150px !important;
  padding: var(--space-6) var(--space-6) var(--space-3);
}
.chat-composer--compact .composer-surface { border-radius: 12px; }
.chat-composer--compact .composer-surface :deep(.el-textarea__inner) { min-height: 56px !important; }
.composer-actions { display: flex; justify-content: flex-end; padding: 0 var(--space-3) var(--space-3); }
.composer-submit { min-width: 92px; height: 40px; border-radius: var(--radius-lg); }
.composer-hint {
  margin: var(--space-2) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-secondary);
  line-height: 1.6;
  text-align: center;
}
@media (max-width: 760px) {
  .chat-composer--welcome .composer-surface :deep(.el-textarea__inner) {
    min-height: 132px !important;
    padding: var(--space-4) var(--space-4) var(--space-2);
  }
  .composer-hint { text-align: left; }
}
</style>
