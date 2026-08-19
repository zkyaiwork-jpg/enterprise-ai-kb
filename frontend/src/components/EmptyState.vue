<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <div class="empty-state" role="status">
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 4h14v16H5z" />
      <path d="M8 9h8M8 13h5" />
    </svg>
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  min-height: 160px;
  padding: var(--space-6);
  text-align: center;
}

.empty-state svg {
  width: 24px;
  height: 24px;
  margin-bottom: var(--space-3);
  color: var(--color-text-secondary);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.5;
}

.empty-state strong { color: var(--color-text); font-size: var(--font-size-body); font-weight: 500; }
.empty-state p { max-width: 42ch; margin: var(--space-2) 0 0; color: var(--color-text-secondary); font-size: var(--font-size-secondary); line-height: 1.6; }
</style>
