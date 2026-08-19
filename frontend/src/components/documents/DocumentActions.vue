<script setup lang="ts">
defineProps<{ canEdit: boolean; canDelete: boolean }>()
defineEmits<{ view: []; edit: []; delete: [] }>()
</script>

<template>
  <el-dropdown trigger="click" @command="$emit($event)">
    <button type="button" class="document-actions-button" aria-label="打开文档操作菜单" @click.stop>
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></svg>
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="view">查看详情</el-dropdown-item>
        <el-dropdown-item v-if="canEdit" command="edit">修改权限</el-dropdown-item>
        <el-dropdown-item v-if="canDelete" command="delete" divided>删除文档</el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style scoped>
.document-actions-button { display: grid; place-items: center; width: 32px; height: 32px; padding: 0; color: var(--color-text-secondary); border: 1px solid transparent; border-radius: var(--radius-md); background: transparent; cursor: pointer; }
.document-actions-button:hover { color: var(--color-text); background: var(--color-surface); border-color: var(--color-border); }
.document-actions-button svg { width: 18px; height: 18px; fill: currentColor; }
</style>
