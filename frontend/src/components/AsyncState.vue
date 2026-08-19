<script setup lang="ts">
withDefaults(defineProps<{
  state: 'loading' | 'error' | 'empty'
  title: string
  description?: string
  retryLabel?: string
}>(), { retryLabel: '重新加载' })

defineEmits<{ retry: [] }>()
</script>

<template>
  <div :class="['async-state', `async-state--${state}`]" :role="state === 'error' ? 'alert' : 'status'" aria-live="polite">
    <el-skeleton v-if="state === 'loading'" :rows="3" animated />
    <template v-else>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <template v-if="state === 'error'"><circle cx="12" cy="12" r="9" /><path d="M12 7v6M12 17v.01" /></template>
        <template v-else><path d="M5 4h14v16H5z" /><path d="M8 9h8M8 13h5" /></template>
      </svg>
      <strong>{{ title }}</strong>
      <p v-if="description">{{ description }}</p>
      <el-button v-if="state === 'error'" type="primary" plain @click="$emit('retry')">{{ retryLabel }}</el-button>
    </template>
  </div>
</template>

<style scoped>
.async-state { display: flex; align-items: center; flex-direction: column; justify-content: center; min-height: 176px; padding: var(--space-6); text-align: center; }
.async-state--loading { display: block; text-align: left; }
.async-state--loading :deep(.el-skeleton) { width: min(720px, 100%); margin: 0 auto; }
.async-state svg { width: 24px; height: 24px; margin-bottom: var(--space-3); color: var(--color-text-secondary); fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.5; }
.async-state--error svg { color: var(--color-error); }
.async-state strong { color: var(--color-text); font-size: var(--font-size-body); font-weight: 600; }
.async-state p { max-width: 48ch; margin: var(--space-2) 0 0; color: var(--color-text-secondary); font-size: var(--font-size-secondary); line-height: 1.6; }
.async-state .el-button { margin-top: var(--space-4); }
</style>
