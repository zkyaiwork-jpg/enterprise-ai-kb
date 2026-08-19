<script setup lang="ts">
defineProps<{ title: string; description: string }>()
</script>

<template>
  <div class="capability-notice" role="note">
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5v.5" /></svg>
    <div><strong>{{ title }}</strong><p>{{ description }}</p></div>
  </div>
</template>

<style scoped>
.capability-notice { display: flex; align-items: flex-start; gap: var(--space-3); padding: var(--space-3) var(--space-4); color: var(--color-text-secondary); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }
.capability-notice svg { width: 18px; height: 18px; flex: 0 0 auto; margin-top: 1px; color: var(--color-primary); fill: none; stroke: currentColor; stroke-linecap: round; stroke-width: 1.6; }
.capability-notice strong { color: var(--color-text); font-size: var(--font-size-body); font-weight: 600; }
.capability-notice p { margin: var(--space-1) 0 0; font-size: var(--font-size-secondary); line-height: 1.6; }
</style>
