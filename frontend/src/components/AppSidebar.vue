<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'

defineEmits<{ navigate: [] }>()

const route = useRoute()
const userStore = useUserStore()

interface NavigationItem {
  index: string
  label: string
  icon: 'home' | 'chat' | 'document' | 'search' | 'knowledge' | 'user' | 'audit'
  visible: boolean
  disabled?: boolean
}

const iconPaths: Record<NavigationItem['icon'], string[]> = {
  home: [
    'M3 11.5 12 4l9 7.5',
    'M5 10v10h14V10',
    'M9 20v-6h6v6',
  ],
  chat: [
    'M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z',
    'M8 9h8',
    'M8 13h5',
  ],
  document: [
    'M6 3h9l4 4v14H6z',
    'M15 3v5h4',
    'M9 13h6',
    'M9 17h6',
  ],
  search: [
    'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z',
    'm16 16 4 4',
  ],
  knowledge: [
    'M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3z',
    'M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6',
    'M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6',
  ],
  user: [
    'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
    'M4 21a8 8 0 0 1 16 0',
  ],
  audit: [
    'M5 3h14v18H5z',
    'M9 3V1',
    'M15 3V1',
    'M9 9h6',
    'M9 13h6',
    'M9 17h4',
  ],
}

const navigationGroups = computed(() => {
  const knowledgeItems: NavigationItem[] = [
    { index: '/', label: '首页', icon: 'home', visible: true },
    { index: '/chat', label: 'AI 问答', icon: 'chat', visible: true },
    { index: '/documents', label: '文档管理', icon: 'document', visible: true },
    { index: '/search', label: '智能检索', icon: 'search', visible: userStore.hasPermission('file_view') },
    { index: 'knowledge-unavailable', label: '知识库管理', icon: 'knowledge', visible: true, disabled: true },
  ]
  const organizationItems: NavigationItem[] = [
    {
      index: '/users',
      label: '用户管理',
      icon: 'user',
      visible: userStore.hasPermission('user_manage'),
    },
    {
      index: '/audit',
      label: '审计日志',
      icon: 'audit',
      visible: userStore.hasPermission('audit_view'),
    },
  ]

  return [
    { label: '知识工作', items: knowledgeItems },
    { label: '组织管理', items: organizationItems },
  ].map((group) => ({
    ...group,
    items: group.items.filter((item) => item.visible),
  })).filter((group) => group.items.length > 0)
})
</script>

<template>
  <div class="sidebar-content">
    <div class="brand">
      <div class="brand-symbol" aria-hidden="true">知</div>
      <div class="brand-copy">
        <strong>企业 AI 知识库助手</strong>
        <span>企业知识管理平台</span>
      </div>
    </div>

    <nav class="app-navigation" aria-label="主导航">
      <section v-for="group in navigationGroups" :key="group.label" class="navigation-group">
        <h2>{{ group.label }}</h2>
        <el-menu :default-active="route.path" router class="sidebar-menu" @select="$emit('navigate')">
          <el-menu-item
            v-for="item in group.items"
            :key="item.index"
            :index="item.index"
            :disabled="item.disabled"
          >
            <el-tooltip :disabled="!item.disabled" content="暂未开放" placement="right">
              <span class="navigation-item-content">
                <svg class="navigation-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    v-for="path in iconPaths[item.icon]"
                    :key="path"
                    :d="path"
                  />
                </svg>
                <span class="navigation-item-label">{{ item.label }}</span>
                <span v-if="item.disabled" class="navigation-item-status">未开放</span>
              </span>
            </el-tooltip>
          </el-menu-item>
        </el-menu>
      </section>
    </nav>
  </div>
</template>
