<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getApiErrorMessage } from '../api/http'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const loginError = ref('')
const form = reactive({ username: '', password: '' })
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  submitting.value = true
  loginError.value = ''
  try {
    await userStore.login(form)
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
      ? route.query.redirect
      : '/'
    await router.replace(redirect)
  } catch (error) {
    loginError.value = getApiErrorMessage(error, '登录失败，请检查账号信息后重试。')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-story">
      <div class="login-brand"><span aria-hidden="true">知</span> 企业 AI 知识库助手</div>
      <div class="story-content">
        <h1>企业知识管理平台</h1>
        <p>统一管理企业知识文档，通过权限范围内的 AI 问答快速查找信息。</p>
      </div>
    </section>

    <section class="login-panel">
      <div class="login-form-wrap">
        <h2>欢迎回来</h2>
        <p class="login-hint">使用企业账号登录知识库工作台</p>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @keyup.enter="submit">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" autocomplete="username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" autocomplete="current-password" show-password placeholder="请输入密码" />
          </el-form-item>
          <div v-if="loginError" class="login-error" role="alert">{{ loginError }}</div>
          <el-button type="primary" class="login-submit" :loading="submitting" @click="submit">
            进入工作台
          </el-button>
        </el-form>
        <p class="security-note">账号权限由企业管理员统一管理。</p>
      </div>
    </section>
  </main>
</template>
