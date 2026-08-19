<script setup lang="ts">
import ChatComposer from './ChatComposer.vue'

defineProps<{ modelValue: string; sending: boolean }>()
defineEmits<{ 'update:modelValue': [value: string]; send: [] }>()
</script>

<template>
  <ChatComposer
    :model-value="modelValue"
    :sending="sending"
    variant="compact"
    placeholder="继续提问"
    label="继续输入问题"
    hint="Enter 发送 · Shift + Enter 换行 · 回答内容请结合来源原文核验"
    @update:model-value="$emit('update:modelValue', $event)"
    @send="$emit('send')"
  />
</template>
