<template>
  <main class="auth-page" id="main-content">
    <section class="auth-intro" aria-labelledby="auth-title">
      <BrandLogo />
      <div class="auth-copy">
        <p class="auth-kicker">{{ adminPortal ? '独立管理员控制台' : '本地优先的求职工作台' }}</p>
        <h1 id="auth-title">{{ adminPortal ? '看清运行状态' : '登录后，开始求职' }}</h1>
        <p>{{ adminPortal ? '集中查看用户活跃、在线时长和登录趋势，管理员账号与普通用户注册完全分离。' : '岗位、简历和沟通记录只在认证后加载。工作台账号与 BOSS 登录相互独立。' }}</p>
      </div>
      <div class="auth-principles" aria-label="系统特点">
        <article><Icon :icon="adminPortal ? 'mdi:chart-timeline-variant-shimmer' : 'mdi:database-lock-outline'" /><div><strong>{{ adminPortal ? '多维运行数据' : '认证后加载' }}</strong><span>{{ adminPortal ? '注册、在线、活跃和时长趋势集中呈现。' : '登录工作台后，才可登录 BOSS 和调用业务能力。' }}</span></div></article>
        <article><Icon icon="mdi:server-network-outline" /><div><strong>轻量可部署</strong><span>静态 Vue 前端配合单个 FastAPI 服务，低频心跳减少数据库写入。</span></div></article>
      </div>
    </section>

    <section class="auth-panel" aria-labelledby="form-title">
      <div>
        <p class="auth-step">{{ adminPortal ? '管理员后台' : mode === 'login' ? '用户登录' : '创建用户账号' }}</p>
        <div class="auth-panel-tools"><a href="/">返回首页</a><ThemeToggle :theme="theme" @toggle="$emit('toggle-theme')" /></div>
        <h2 id="form-title">{{ adminPortal ? '进入控制台' : mode === 'login' ? '进入工作台' : '注册 MyJob' }}</h2>
        <p>{{ adminPortal ? '这里只接受管理员和超级管理员账号。' : mode === 'login' ? '验证通过后加载求职功能。' : '注册成功后将直接进入工作台。' }}</p>
      </div>

      <div v-if="!adminPortal" class="auth-mode-switch" aria-label="登录或注册">
        <button type="button" :class="{ active: mode === 'login' }" @click="setMode('login')">登录</button>
        <button type="button" :class="{ active: mode === 'register' }" :disabled="!registrationEnabled" @click="setMode('register')">注册</button>
      </div>

      <form class="auth-form" @submit.prevent="submit">
        <label>
          <span>用户名</span>
          <input v-model.trim="form.username" name="username" autocomplete="username" required :minlength="mode === 'register' ? 8 : 3" :maxlength="mode === 'register' ? 12 : 48" :pattern="mode === 'register' ? '(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9]{8,12}' : undefined" :placeholder="mode === 'register' ? '8-12 位英文和数字' : adminPortal ? '输入管理员用户名' : '输入用户名'" />
          <small v-if="mode === 'register'">只能使用英文字母和数字，且两者都要有。</small>
        </label>
        <label>
          <span>密码</span>
          <div class="password-field">
            <input v-model="form.password" name="password" :type="showPassword ? 'text' : 'password'" :autocomplete="mode === 'register' ? 'new-password' : 'current-password'" required :minlength="adminPortal && mode === 'login' ? 7 : 8" maxlength="128" :pattern="mode === 'register' ? '(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,128}' : undefined" :placeholder="mode === 'register' ? '英文大小写、数字和特殊字符' : '输入密码'" />
            <button type="button" :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword"><Icon :icon="showPassword ? 'mdi:eye-off-outline' : 'mdi:eye-outline'" /></button>
          </div>
        </label>
        <label v-if="mode === 'register'">
          <span>确认密码</span>
          <input v-model="form.confirmPassword" name="confirm-password" type="password" autocomplete="new-password" required minlength="8" maxlength="128" pattern="(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,128}" placeholder="再次输入密码" />
        </label>

        <p v-if="error" class="form-error" role="alert"><Icon icon="mdi:alert-circle-outline" />{{ error }}</p>
        <p v-else-if="!adminPortal && !registrationEnabled" class="form-notice"><Icon icon="mdi:account-lock-outline" />管理员当前已关闭新用户注册。</p>
        <button class="primary-action" type="submit" :disabled="submitting">
          <Icon :icon="submitting ? 'mdi:loading' : mode === 'register' ? 'mdi:account-plus-outline' : 'mdi:login'" :class="{ spin: submitting }" />
          {{ submitting ? '正在验证' : mode === 'register' ? '注册并登录' : '登录' }}
        </button>
      </form>

      <p v-if="adminPortal" class="auth-footnote"><Icon icon="mdi:shield-key-outline" />首次部署账号为 Admin，密码为 123456*。首次登录后必须修改密码。</p>
      <p v-else class="auth-footnote"><Icon icon="mdi:information-outline" />此处只注册普通用户，管理员使用独立后台入口。</p>
      <a v-if="adminPortal" class="auth-back-link" href="/"><Icon icon="mdi:arrow-left" />返回用户工作台</a>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { Icon } from '@iconify/vue'
import { api } from '../api'
import BrandLogo from './BrandLogo.vue'
import ThemeToggle from './ThemeToggle.vue'

const props = defineProps({
  adminPortal: Boolean,
  registrationEnabled: { type: Boolean, default: true },
  initialMode: { type: String, default: 'login' },
  theme: { type: String, required: true },
})
const emit = defineEmits(['authenticated', 'toggle-theme'])
const mode = ref(props.adminPortal ? 'login' : props.initialMode === 'register' && props.registrationEnabled ? 'register' : 'login')
const form = reactive({ username: '', password: '', confirmPassword: '' })
const showPassword = ref(false)
const submitting = ref(false)
const error = ref('')

watch(() => props.registrationEnabled, enabled => {
  if (!enabled && mode.value === 'register') setMode('login')
})

function setMode(value) {
  if (value === 'register' && !props.registrationEnabled) return
  mode.value = value
  form.password = ''
  form.confirmPassword = ''
  error.value = ''
}

async function submit() {
  error.value = ''
  if (mode.value === 'register' && !/^(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9]{8,12}$/.test(form.username)) {
    error.value = '用户名必须为 8-12 位英文和数字，且两者都要有'
    return
  }
  if (mode.value === 'register' && !/^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,128}$/.test(form.password)) {
    error.value = '密码必须包含英文大写、小写、数字和特殊字符'
    return
  }
  if (mode.value === 'register' && form.password !== form.confirmPassword) {
    error.value = '两次输入的密码不一致'
    return
  }
  submitting.value = true
  try {
    const path = props.adminPortal ? '/api/admin/login' : mode.value === 'register' ? '/api/auth/register' : '/api/auth/login'
    const result = await api.post(path, { username: form.username, password: form.password })
    emit('authenticated', result.user)
  } catch (exc) {
    error.value = exc.message || (mode.value === 'register' ? '注册失败，请稍后重试' : '登录失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>
