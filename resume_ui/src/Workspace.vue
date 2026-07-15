<template>
  <LandingView v-if="pageKind === 'home'" :theme="theme" @toggle-theme="toggleTheme" />
  <ProductDocsView v-else-if="pageKind === 'docs'" :theme="theme" @toggle-theme="toggleTheme" />
  <ChangelogView v-else-if="pageKind === 'changelog'" :theme="theme" @toggle-theme="toggleTheme" />
  <template v-else>
  <div v-if="booting" class="app-boot" aria-live="polite"><BrandLogo compact /><p>正在检查 MyJob 登录状态</p></div>
  <LoginView
    v-else-if="authEntryPage || !portalAuthenticated"
    :admin-portal="adminPortal"
    :current-user="authEntryPage && portalAuthenticated ? auth.user : null"
    :initial-mode="pageKind === 'register' ? 'register' : 'login'"
    :registration-enabled="auth.registration_enabled"
    :theme="theme"
    @toggle-theme="toggleTheme"
    @authenticated="onAuthenticated"
    @switch-account="logoutForAuthSwitch"
  />
  <AdminView v-else-if="adminPortal" :user="auth.user" :theme="theme" @toggle-theme="toggleTheme" @logout="logoutApp" @user-changed="onUserChanged" />
  <div v-else class="workspace-shell">
    <aside class="app-sidebar" :class="{ open: mobileNavOpen }">
      <div class="sidebar-brand"><BrandLogo /><button class="mobile-close" aria-label="关闭导航" @click="mobileNavOpen = false"><Icon icon="mdi:close" /></button></div>
      <nav aria-label="主要导航">
        <button v-for="item in navigation" :key="item.id" :class="{ active: currentView === item.id }" @click="navigate(item.id)"><Icon :icon="item.icon" /><span>{{ item.label }}</span><small v-if="item.id === 'communication' && unreadCount">{{ unreadCount }}</small></button>
      </nav>
      <div class="sidebar-foot"><span :class="['connection-state', socketState]"><Icon icon="mdi:lan-connect" />{{ socketLabel }}</span><small>数据库与自动化均由后端管理</small></div>
    </aside>
    <div v-if="mobileNavOpen" class="mobile-scrim" @click="mobileNavOpen = false"></div>

    <div class="workspace-body">
      <header class="app-topbar">
        <button class="mobile-menu" aria-label="打开导航" @click="mobileNavOpen = true"><Icon icon="mdi:menu" /></button>
        <div class="runtime-summary"><span :class="{ active: browserStatus.browser_running }"><Icon icon="mdi:heart-pulse" />{{ browserStatus.browser_running ? '登录心跳运行中' : '登录服务未启动' }}</span><span class="desktop-only">今日投递 {{ summary?.stats?.today_applications || 0 }} / {{ summary?.stats?.daily_limit || 0 }}</span></div>
        <PlatformLoginStatus class="topbar-platform-status" :platforms="platforms" :platform-status="browserStatus.platforms" :active-platform="activePlatform" @select="setActivePlatform" />
        <div class="browser-actions desktop-only">
          <button :disabled="systemBusy" @click="startLogin"><Icon icon="mdi:account-key-outline" />启动登录</button>
          <button :disabled="systemBusy || !browserStatus.browser_running" @click="logoutPlatform"><Icon icon="mdi:logout-variant" />登出</button>
          <button :disabled="systemBusy || !browserStatus.browser_running" @click="stopBrowser"><Icon icon="mdi:stop-outline" />停止</button>
        </div>
        <ThemeToggle :theme="theme" @toggle="toggleTheme" />
        <div class="user-menu"><span>{{ auth.user?.username }}</span><button title="退出工作台" aria-label="退出工作台" @click="logoutApp"><Icon icon="mdi:exit-to-app" /></button></div>
      </header>

      <div class="mobile-runtime-actions">
        <div class="mobile-platform-status"><PlatformLoginStatus :platforms="platforms" :platform-status="browserStatus.platforms" :active-platform="activePlatform" @select="setActivePlatform" /></div>
        <button :disabled="systemBusy" @click="startLogin">启动登录</button><button :disabled="systemBusy || !browserStatus.browser_running" @click="logoutPlatform">登出</button><button :disabled="systemBusy || !browserStatus.browser_running" @click="stopBrowser">停止</button>
      </div>

      <main id="main-content" class="workspace-main">
        <KeepAlive>
          <OverviewView v-if="currentView === 'overview'" :summary="summary" :loading="summaryLoading" @refresh="loadSummary(true)" @navigate="navigate" />
          <JobCenterView v-else-if="currentView === 'jobs'" :platform="activePlatform" :platforms="platforms" @platform-change="setActivePlatform" @notify="notify" @changed="onDataChanged" />
          <ResumeEditor v-else-if="currentView === 'resume'" class="resume-editor-host" />
          <CampaignsView v-else-if="currentView === 'campaigns'" @notify="notify" @changed="onDataChanged" />
          <CommunicationView v-else-if="currentView === 'communication'" :refresh-key="eventVersion" @notify="notify" @changed="onDataChanged" />
          <SettingsView v-else-if="currentView === 'settings'" @notify="notify" @changed="onDataChanged" />
        </KeepAlive>
      </main>
    </div>

    <div class="toast-stack" aria-live="polite"><article v-for="toast in toasts" :key="toast.id" :data-type="toast.type"><Icon :icon="toastIcon(toast.type)" /><span>{{ toast.message }}</span><button aria-label="关闭提示" @click="removeToast(toast.id)"><Icon icon="mdi:close" /></button></article></div>

    <Teleport to="body">
      <div v-if="modal" class="result-modal-backdrop" @click.self="modal = null">
        <section class="result-modal" role="dialog" aria-modal="true" :aria-labelledby="`modal-${modal.id}`">
          <Icon :icon="modal.icon" :class="modal.type" />
          <h2 :id="`modal-${modal.id}`">{{ modal.title }}</h2>
          <p>{{ modal.message }}</p>
          <button class="primary-action" @click="modal = null">知道了</button>
        </section>
      </div>
    </Teleport>
  </div>
  </template>
</template>

<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { Icon } from '@iconify/vue'
import BrandLogo from './components/BrandLogo.vue'
import LoginView from './components/LoginView.vue'
import PlatformLoginStatus from './components/PlatformLoginStatus.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import OverviewView from './views/OverviewView.vue'
import { api, connectSocket, sleep } from './api'
import { ROUTES } from './product'
import { applyTheme, preferredTheme } from './theme'

const JobCenterView = defineAsyncComponent(() => import('./views/JobCenterView.vue'))
const ResumeEditor = defineAsyncComponent(() => import('./App.vue'))
const CampaignsView = defineAsyncComponent(() => import('./views/CampaignsView.vue'))
const CommunicationView = defineAsyncComponent(() => import('./views/CommunicationView.vue'))
const SettingsView = defineAsyncComponent(() => import('./views/SettingsView.vue'))
const AdminView = defineAsyncComponent(() => import('./views/AdminView.vue'))
const LandingView = defineAsyncComponent(() => import('./views/LandingView.vue'))
const ProductDocsView = defineAsyncComponent(() => import('./views/ProductDocsView.vue'))
const ChangelogView = defineAsyncComponent(() => import('./views/ChangelogView.vue'))

const navigation = [
  { id: 'overview', label: '工作台', icon: 'mdi:view-dashboard-outline' },
  { id: 'jobs', label: '岗位中心', icon: 'mdi:briefcase-search-outline' },
  { id: 'resume', label: '简历中心', icon: 'mdi:file-document-edit-outline' },
  { id: 'campaigns', label: '求职计划', icon: 'mdi:calendar-multiselect-outline' },
  { id: 'communication', label: '沟通中心', icon: 'mdi:message-processing-outline' },
  { id: 'settings', label: '设置与安全', icon: 'mdi:tune-variant' },
]
const platforms = [
  { id: 'boss', label: 'BOSS 直聘', shortLabel: 'BOSS' },
  { id: 'zhilian', label: '智联招聘', shortLabel: '智联' },
  { id: 'liepin', label: '猎聘', shortLabel: '猎聘' },
  { id: 'job51', label: '前程无忧', shortLabel: '前程无忧' },
]
const validViews = new Set(navigation.map(item => item.id))
const normalizedPath = location.pathname.length > 1 ? location.pathname.replace(/\/+$/, '') : '/'
const pageKind = ({
  [ROUTES.home]: 'home',
  [ROUTES.login]: 'login',
  [ROUTES.register]: 'register',
  [ROUTES.docs]: 'docs',
  [ROUTES.changelog]: 'changelog',
  [ROUTES.admin]: 'admin',
  [ROUTES.app]: 'app',
})[normalizedPath] || 'home'
const publicPage = ['home', 'docs', 'changelog'].includes(pageKind)
const adminPortal = pageKind === 'admin'
const authEntryPage = ['login', 'register'].includes(pageKind)
const theme = ref(preferredTheme())
const auth = reactive({ configured: true, registration_enabled: true, authenticated: false, user: null })
const booting = ref(!publicPage)
const currentView = ref(validViews.has(location.hash.slice(1)) ? location.hash.slice(1) : 'overview')
const mobileNavOpen = ref(false)
const summary = ref(null)
const summaryLoading = ref(false)
const socketState = ref('closed')
const eventVersion = ref(0)
const systemBusy = ref(false)
const activePlatform = ref(platforms.some(item => item.id === localStorage.getItem('myjob.activePlatform')) ? localStorage.getItem('myjob.activePlatform') : 'boss')
const modal = ref(null)
const toasts = ref([])
let toastId = 0
let pollTimer
let authHeartbeatTimer
let platformHeartbeatTimer
let socketCleanup
let summaryDebounce
let pendingLoginPlatform = ''
let platformHeartbeatBusy = false

const platformRuntime = reactive({ browser_running: false, active_platform: 'boss', platforms: {} })
const browserStatus = computed(() => {
  const status = summary.value?.status || {}
  const hasHeartbeatState = Object.keys(platformRuntime.platforms || {}).length > 0
  return {
    ...status,
    ...(hasHeartbeatState ? platformRuntime : {}),
    platforms: hasHeartbeatState ? platformRuntime.platforms : (status.platforms || {}),
  }
})
const portalAuthenticated = computed(() => {
  if (!auth.authenticated) return false
  return adminPortal
    ? ['admin', 'superadmin'].includes(auth.user?.role)
    : auth.user?.role === 'user'
})
const unreadCount = computed(() => (summary.value?.recent_conversations || []).reduce((sum, item) => sum + Number(item.unread_count || 0), 0))
const socketLabel = computed(() => ({ open: '实时连接正常', connecting: '正在连接', closed: '等待连接' }[socketState.value] || '等待连接'))

function navigate(view) {
  if (!validViews.has(view)) return
  currentView.value = view
  location.hash = view
  mobileNavOpen.value = false
}

function setActivePlatform(platform) {
  if (!platforms.some(item => item.id === platform)) return
  activePlatform.value = platform
  localStorage.setItem('myjob.activePlatform', platform)
}

function applyPlatformRuntime(runtime) {
  if (!runtime) return
  platformRuntime.browser_running = Boolean(runtime.browser_running)
  platformRuntime.active_platform = runtime.active_platform || activePlatform.value
  platformRuntime.platforms = runtime.platforms || {}
}

function toggleTheme() {
  theme.value = applyTheme(theme.value === 'dark' ? 'light' : 'dark')
}

async function checkAuth() {
  try {
    const status = await api.get('/api/auth/status', { force: true })
    Object.assign(auth, status)
    if (portalAuthenticated.value) {
      if (adminPortal || pageKind === 'app') startRuntime()
    }
  } catch (exc) {
    notify({ type: 'error', message: `无法连接后端：${exc.message}` })
  } finally { booting.value = false }
}

function onAuthenticated(user) {
  auth.authenticated = true
  auth.user = user
  if (!adminPortal && pageKind !== 'app') {
    location.replace(ROUTES.app)
    return
  }
  startRuntime()
}

function onUserChanged(user) {
  auth.user = user
}

function startRuntime() {
  stopRuntime()
  authHeartbeatTimer = window.setInterval(() => {
    if (document.visibilityState === 'visible') api.post('/api/auth/heartbeat').catch(() => {})
  }, 60000)
  if (adminPortal) return
  loadSummary(true).then(() => refreshPlatformHeartbeat())
  socketCleanup = connectSocket(handleSocketEvent, value => { socketState.value = value })
  pollTimer = window.setInterval(() => {
    if (document.visibilityState === 'visible') loadSummary()
  }, 15000)
  platformHeartbeatTimer = window.setInterval(() => {
    if (document.visibilityState === 'visible') refreshPlatformHeartbeat()
  }, 15000)
}

function stopRuntime() {
  window.clearInterval(pollTimer)
  window.clearInterval(authHeartbeatTimer)
  window.clearInterval(platformHeartbeatTimer)
  window.clearTimeout(summaryDebounce)
  socketCleanup?.()
  socketCleanup = null
}

async function logoutApp() {
  try { await api.post('/api/auth/logout') } catch { /* Cookie is cleared locally on the next auth check. */ }
  stopRuntime()
  auth.authenticated = false
  auth.user = null
  summary.value = null
  api.invalidate()
  location.replace(adminPortal ? ROUTES.admin : ROUTES.login)
}

async function logoutForAuthSwitch() {
  try { await api.post('/api/auth/logout') } catch { /* The local view still returns to signed-out mode. */ }
  stopRuntime()
  auth.authenticated = false
  auth.user = null
  summary.value = null
  api.invalidate()
}

async function loadSummary(force = false) {
  if (!auth.authenticated || summaryLoading.value) return
  summaryLoading.value = true
  try {
    summary.value = await api.get('/api/dashboard/summary', { ttl: 10000, force })
    applyPlatformRuntime(summary.value?.status)
  }
  catch (exc) { if (exc.status !== 401) notify({ type: 'error', message: exc.message }) }
  finally { summaryLoading.value = false }
}

function handleSocketEvent(message) {
  if (message.type === 'connected' || message.type === 'pong') return
  if (message.type === 'platform_login_status') applyPlatformRuntime(message)
  eventVersion.value += 1
  api.invalidate('/api/dashboard')
  window.clearTimeout(summaryDebounce)
  summaryDebounce = window.setTimeout(() => loadSummary(true), 350)
}

function onDataChanged() {
  api.invalidate('/api/dashboard')
  loadSummary(true)
}

async function startLogin() {
  if (systemBusy.value) return
  systemBusy.value = true
  const platform = activePlatform.value
  const platformLabel = platforms.find(item => item.id === platform)?.label || '招聘平台'
  pendingLoginPlatform = platform
  try {
    const result = await api.post(`/api/system/start?platform=${encodeURIComponent(platform)}&login=true`)
    if (result.status === 'error') throw new Error(result.message)
    if (result.logged_in) {
      pendingLoginPlatform = ''
      showModal('success', '登录成功', `${platformLabel}登录状态验证通过。`)
    } else {
      showModal('info', '请登录', `${platformLabel}登录页已打开，完成登录后状态会由心跳自动更新。`)
    }
    await sleep(600)
    await refreshPlatformHeartbeat()
    await loadSummary(true)
  } catch (exc) {
    pendingLoginPlatform = ''
    showModal('error', '启动登录失败', exc.message)
  }
  finally { systemBusy.value = false }
}

async function refreshPlatformHeartbeat() {
  if (!auth.authenticated || adminPortal || platformHeartbeatBusy) return
  platformHeartbeatBusy = true
  try {
    const result = await api.post('/api/system/heartbeat')
    applyPlatformRuntime(result)
    if (pendingLoginPlatform && result.platforms?.[pendingLoginPlatform]?.logged_in) {
      const platform = platforms.find(item => item.id === pendingLoginPlatform)
      pendingLoginPlatform = ''
      showModal('success', '登录成功', `${platform?.label || '招聘平台'}登录状态验证通过。`)
    }
  } catch (exc) {
    if (exc.status !== 401) notify({ type: 'error', message: `登录心跳异常：${exc.message}` })
  } finally {
    platformHeartbeatBusy = false
  }
}

async function logoutPlatform() {
  if (systemBusy.value) return
  systemBusy.value = true
  const platform = activePlatform.value
  const platformLabel = platforms.find(item => item.id === platform)?.label || '招聘平台'
  try {
    const result = await api.post(`/api/system/logout?platform=${encodeURIComponent(platform)}`)
    showModal(result.status === 'ok' ? 'success' : 'error', result.status === 'ok' ? `已登出${platformLabel}` : '登出失败', result.message)
    pendingLoginPlatform = ''
    await refreshPlatformHeartbeat()
    await loadSummary(true)
  } catch (exc) { showModal('error', '登出失败', exc.message) }
  finally { systemBusy.value = false }
}

async function stopBrowser() {
  if (systemBusy.value) return
  systemBusy.value = true
  try {
    await api.post('/api/system/stop')
    pendingLoginPlatform = ''
    applyPlatformRuntime({ browser_running: false, active_platform: activePlatform.value, platforms: {} })
    await refreshPlatformHeartbeat()
    await loadSummary(true)
    showModal('success', '已停止', '招聘平台浏览器与消息监控已停止。')
  } catch (exc) { showModal('error', '停止失败', exc.message) }
  finally { systemBusy.value = false }
}

function showModal(type, title, message) {
  modal.value = { id: Date.now(), type, title, message, icon: type === 'success' ? 'mdi:check-circle-outline' : type === 'error' ? 'mdi:alert-circle-outline' : 'mdi:information-outline' }
}

function notify(value) {
  const toast = { id: ++toastId, type: value.type || 'info', message: value.message }
  toasts.value.push(toast)
  window.setTimeout(() => removeToast(toast.id), 4200)
}
function removeToast(id) { toasts.value = toasts.value.filter(item => item.id !== id) }
const toastIcon = type => ({ success: 'mdi:check-circle-outline', error: 'mdi:alert-circle-outline', info: 'mdi:information-outline' }[type] || 'mdi:information-outline')

function onHashChange() { const view = location.hash.slice(1); if (validViews.has(view)) currentView.value = view }
function onUnauthorized() { if (auth.authenticated) { stopRuntime(); auth.authenticated = false; auth.user = null; summary.value = null } }

onMounted(() => {
  window.addEventListener('hashchange', onHashChange)
  window.addEventListener('myjob:unauthorized', onUnauthorized)
  if (!publicPage) checkAuth()
})
onBeforeUnmount(() => {
  stopRuntime()
  window.removeEventListener('hashchange', onHashChange)
  window.removeEventListener('myjob:unauthorized', onUnauthorized)
})
</script>
