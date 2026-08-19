<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const mobileNavigationOpen = ref(false)
const displayName = computed(
  () => userStore.state.profile?.real_name || userStore.state.profile?.username || '用户',
)
const pageTitle = computed(() => String(route.meta.title || '首页'))

function logout() {
  userStore.logout()
  router.replace('/login')
}
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="216px" class="app-sidebar">
      <AppSidebar />
    </el-aside>

    <el-container class="content-shell">
      <el-header class="topbar">
        <div class="topbar-heading">
          <button
            class="mobile-menu-button"
            type="button"
            aria-label="打开主导航"
            :aria-expanded="mobileNavigationOpen"
            @click="mobileNavigationOpen = true"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
          <h1>{{ pageTitle }}</h1>
        </div>
        <el-dropdown trigger="click">
          <button class="profile-button" type="button" aria-label="打开用户菜单">
            <span class="avatar">{{ displayName.slice(0, 1) }}</span>
            <span class="profile-copy">
              <strong>{{ displayName }}</strong>
              <small>{{ userStore.state.profile?.role?.name || '成员' }}</small>
            </span>
            <svg class="chevron" viewBox="0 0 24 24" aria-hidden="true">
              <path d="m8 10 4 4 4-4" />
            </svg>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>{{ userStore.state.profile?.username }}</el-dropdown-item>
              <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="page-container">
        <RouterView />
      </el-main>
    </el-container>

    <el-drawer
      v-model="mobileNavigationOpen"
      class="mobile-navigation-drawer"
      direction="ltr"
      size="min(320px, 88vw)"
      :with-header="false"
    >
      <AppSidebar @navigate="mobileNavigationOpen = false" />
    </el-drawer>
  </el-container>
</template>
