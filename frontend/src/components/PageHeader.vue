<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <header class="page-header">
    <div>
      <h2>{{ title }}</h2>
      <p v-if="description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
}

.page-header h2 {
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-page-title);
  font-weight: 600;
  line-height: 1.35;
  letter-spacing: -0.02em;
}

.page-header p {
  margin: var(--space-2) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  line-height: 1.6;
}

.page-header-actions { flex: 0 0 auto; }

@media (max-width: 640px) {
  .page-header { align-items: flex-start; flex-direction: column; gap: var(--space-4); }
  .page-header-actions, .page-header-actions :deep(.el-button) { width: 100%; }
}
</style>
