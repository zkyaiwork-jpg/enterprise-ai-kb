<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <section class="data-surface">
    <header class="data-surface-header">
      <div>
        <h2>{{ title }}</h2>
        <p v-if="description">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="data-surface-actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="data-surface-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.data-surface {
  overflow: hidden;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.data-surface-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  min-height: 56px;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.data-surface-header h2 {
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-section-title);
  font-weight: 600;
}

.data-surface-header p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-secondary);
}

.data-surface-actions { flex: 0 0 auto; }
.data-surface-body { min-width: 0; }
</style>
