<script setup lang="ts">
import type { ManagedUser } from '../../api/users'

defineProps<{ user: ManagedUser; canDelete?: boolean; disabled?: boolean }>()
const emit = defineEmits<{ edit: [user: ManagedUser]; resetPassword: [user: ManagedUser]; toggleStatus: [user: ManagedUser]; delete: [user: ManagedUser] }>()

function handleCommand(command: string, user: ManagedUser) {
  if (command === 'edit') emit('edit', user)
  else if (command === 'resetPassword') emit('resetPassword', user)
  else if (command === 'toggleStatus') emit('toggleStatus', user)
  else if (command === 'delete') emit('delete', user)
}
</script>

<template>
  <el-dropdown trigger="click" placement="bottom-end" :disabled="disabled" @command="(command: string) => handleCommand(command, user)">
    <button class="action-trigger" type="button" :disabled="disabled" :aria-label="`打开 ${user.username} 的操作菜单`">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></svg>
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="edit">编辑用户</el-dropdown-item>
        <el-dropdown-item command="resetPassword">重置密码</el-dropdown-item>
        <el-dropdown-item command="toggleStatus" :class="{ 'danger-action': user.status === 'active' }">{{ user.status === 'active' ? '禁用用户' : '启用用户' }}</el-dropdown-item>
        <el-dropdown-item v-if="canDelete" command="delete" divided class="danger-action">删除用户</el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style scoped>
.action-trigger { display: grid; place-items: center; width: 32px; height: 32px; padding: 0; color: var(--color-text-secondary); border: 1px solid transparent; border-radius: var(--radius-md); background: transparent; cursor: pointer; }
.action-trigger:hover { color: var(--color-text); border-color: var(--color-border); background: var(--color-surface); }
.action-trigger:disabled { color: #9ca3af; cursor: wait; }
.action-trigger:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
.action-trigger svg { width: 18px; height: 18px; fill: currentColor; }
:global(.danger-action) { color: var(--color-error) !important; }
</style>
