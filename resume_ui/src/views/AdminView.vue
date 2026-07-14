<template>
  <div class="admin-shell">
    <header class="admin-topbar">
      <BrandLogo />
      <div class="admin-top-actions">
        <a href="/"><Icon icon="mdi:briefcase-outline" />用户工作台</a>
        <ThemeToggle :theme="theme" @toggle="$emit('toggle-theme')" />
        <span>{{ user.username }} · {{ roleLabel(user.role) }}</span>
        <button type="button" aria-label="退出管理员后台" @click="$emit('logout')"><Icon icon="mdi:exit-to-app" /></button>
      </div>
    </header>

    <main v-if="user.must_change_password" class="password-gate" id="main-content">
      <section>
        <Icon icon="mdi:shield-key-outline" />
        <p class="auth-step">首次登录安全检查</p>
        <h1>修改默认密码</h1>
        <p>默认密码只能用于首次登录。新密码保存后，当前会话会自动更新。</p>
        <form class="auth-form" @submit.prevent="changePassword">
          <label><span>当前密码</span><input v-model="passwordForm.current" type="password" autocomplete="current-password" required minlength="7" maxlength="128" /></label>
          <label><span>新密码</span><input v-model="passwordForm.next" type="password" autocomplete="new-password" required minlength="8" maxlength="128" pattern="(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,128}" placeholder="英文大小写、数字和特殊字符" /></label>
          <label><span>确认新密码</span><input v-model="passwordForm.confirm" type="password" autocomplete="new-password" required minlength="8" maxlength="128" pattern="(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,128}" /></label>
          <p v-if="formError" class="form-error" role="alert"><Icon icon="mdi:alert-circle-outline" />{{ formError }}</p>
          <button class="primary-action" type="submit" :disabled="saving"><Icon :icon="saving ? 'mdi:loading' : 'mdi:check'" :class="{ spin: saving }" />保存新密码</button>
        </form>
      </section>
    </main>

    <main v-else class="admin-main" id="main-content">
      <header class="admin-heading">
        <div><p>运行概览</p><h1>用户与在线数据</h1><span>在线按最近 {{ overview?.online_window_seconds || 150 }} 秒收到心跳计算，页面仅低频读取统计。</span></div>
        <button class="secondary-action" type="button" :disabled="loading" @click="loadData"><Icon :icon="loading ? 'mdi:loading' : 'mdi:refresh'" :class="{ spin: loading }" />刷新数据</button>
      </header>

      <p v-if="error" class="admin-error" role="alert"><Icon icon="mdi:alert-circle-outline" />{{ error }}</p>
      <div v-if="loading && !overview" class="admin-loading" aria-label="正在加载统计"><span v-for="item in 6" :key="item"></span></div>
      <template v-else-if="overview">
        <section class="admin-metrics" aria-label="关键指标">
          <article><span>注册用户</span><strong>{{ metrics.registered }}</strong><small>不含管理员</small></article>
          <article><span>当前在线</span><strong>{{ metrics.online }}</strong><small>低频心跳口径</small></article>
          <article><span>今日活跃</span><strong>{{ metrics.active_today }}</strong><small>今日到访用户</small></article>
          <article><span>累计在线</span><strong>{{ formatDuration(metrics.total_online_seconds) }}</strong><small>用户有效在线时长</small></article>
          <article><span>累计登录</span><strong>{{ metrics.total_logins }}</strong><small>成功登录次数</small></article>
          <article><span>管理员</span><strong>{{ metrics.admins }}</strong><small>含超级管理员</small></article>
        </section>

        <section class="trend-section surface-block">
          <header><div><h2>近 7 日趋势</h2><p>注册、活跃和在线时长使用各自量纲，避免数据被错误压缩。</p></div></header>
          <div class="trend-grid">
            <article v-for="trend in trends" :key="trend.key" class="trend-panel">
              <header><span>{{ trend.label }}</span><strong>{{ trend.total }}</strong></header>
              <div class="trend-bars" :aria-label="trend.label">
                <div v-for="point in trend.points" :key="point.date" class="trend-column" :title="`${point.date}: ${point.display}`">
                  <span :style="{ height: `${point.height}%` }"></span><small>{{ point.day }}</small>
                </div>
              </div>
            </article>
          </div>
        </section>

        <div class="admin-control-grid">
          <section class="surface-block admin-settings">
            <header><div><h2>用户注册</h2><p>只控制普通用户注册，不影响已有账号登录。</p></div></header>
            <label class="admin-toggle"><span><strong>开放新用户注册</strong><small>{{ overview.registration_enabled ? '用户端可创建普通账号' : '用户端只保留登录' }}</small></span><input type="checkbox" :checked="overview.registration_enabled" :disabled="saving" @change="setRegistration($event.target.checked)" /></label>
          </section>

          <section v-if="user.role === 'superadmin'" class="surface-block admin-create">
            <header><div><h2>创建管理员</h2><p>仅超级管理员可创建，新管理员首次登录必须改密。</p></div></header>
            <form @submit.prevent="createAdmin">
              <label><span>管理员用户名</span><input v-model.trim="adminForm.username" required minlength="8" maxlength="12" pattern="(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9]{8,12}" placeholder="8-12 位英文和数字" /></label>
              <label><span>初始密码</span><input v-model="adminForm.password" type="password" required minlength="8" maxlength="128" pattern="(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,128}" placeholder="英文大小写、数字和特殊字符" /></label>
              <button class="primary-action" type="submit" :disabled="saving"><Icon icon="mdi:account-plus-outline" />创建管理员</button>
            </form>
          </section>
        </div>

        <section class="surface-block admin-users">
          <header><div><h2>账号列表</h2><p>查看账号状态、最近登录、在线时长和登录次数。</p></div><span>{{ users.length }} 个账号</span></header>
          <div class="admin-table-wrap">
            <table>
              <thead><tr><th>账号</th><th>角色</th><th>状态</th><th>最近登录</th><th>在线时长</th><th>登录次数</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="account in users" :key="account.id">
                  <td><strong>{{ account.username }}</strong><small>注册于 {{ formatTime(account.created_at) }}</small></td>
                  <td>{{ roleLabel(account.role) }}</td>
                  <td><span class="account-state" :data-online="account.online">{{ account.online ? '在线' : account.is_active ? '离线' : '已停用' }}</span></td>
                  <td>{{ formatTime(account.last_login_at) }}</td>
                  <td>{{ formatDuration(account.total_online_seconds) }}</td>
                  <td>{{ account.login_count }}</td>
                  <td><button class="text-action" type="button" :disabled="saving || account.id === user.user_id || (account.role !== 'user' && user.role !== 'superadmin')" @click="toggleAccount(account)">{{ account.is_active ? '停用' : '启用' }}</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="surface-block recent-sessions">
          <header><div><h2>最近会话</h2><p>用于识别登录时间与活跃时长，不保存原始 IP 和浏览器标识。</p></div></header>
          <div v-if="!overview.recent_sessions.length" class="empty-state compact-empty"><Icon icon="mdi:history" /><strong>暂无会话记录</strong></div>
          <div v-else class="session-list">
            <article v-for="session in overview.recent_sessions" :key="session.id"><span><strong>{{ session.username }}</strong><small>{{ roleLabel(session.role) }}</small></span><time>{{ formatTime(session.issued_at) }}</time><b>{{ formatDuration(session.active_seconds) }}</b></article>
          </div>
        </section>
      </template>
    </main>

    <div class="toast-stack" aria-live="polite"><article v-for="notice in notices" :key="notice.id" :data-type="notice.type"><Icon :icon="notice.type === 'error' ? 'mdi:alert-circle-outline' : 'mdi:check-circle-outline'" /><span>{{ notice.message }}</span><button aria-label="关闭提示" @click="removeNotice(notice.id)"><Icon icon="mdi:close" /></button></article></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { Icon } from '@iconify/vue'
import { api } from '../api'
import BrandLogo from '../components/BrandLogo.vue'
import ThemeToggle from '../components/ThemeToggle.vue'

const props = defineProps({ user: { type: Object, required: true }, theme: { type: String, required: true } })
const emit = defineEmits(['logout', 'user-changed', 'toggle-theme'])
const overview = ref(null)
const users = ref([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const formError = ref('')
const passwordForm = reactive({ current: '', next: '', confirm: '' })
const adminForm = reactive({ username: '', password: '' })
const notices = ref([])
let noticeId = 0
let refreshTimer

const metrics = computed(() => overview.value?.metrics || {})
const trends = computed(() => {
  const series = overview.value?.series || []
  const definitions = [
    { key: 'registrations', label: '新增注册', formatter: value => `${value} 人` },
    { key: 'active_users', label: '活跃用户', formatter: value => `${value} 人次` },
    { key: 'online_seconds', label: '在线时长', formatter: value => formatDuration(value) },
  ]
  return definitions.map(definition => {
    const maximum = Math.max(1, ...series.map(item => Number(item[definition.key] || 0)))
    const totalValue = series.reduce((sum, item) => sum + Number(item[definition.key] || 0), 0)
    return {
      ...definition,
      total: definition.formatter(totalValue),
      points: series.map(item => ({
        date: item.date,
        day: item.date.slice(5).replace('-', '/'),
        display: definition.formatter(Number(item[definition.key] || 0)),
        height: Math.max(Number(item[definition.key] || 0) ? 8 : 2, Math.round(Number(item[definition.key] || 0) / maximum * 100)),
      })),
    }
  })
})

function roleLabel(role) {
  return { user: '普通用户', admin: '管理员', superadmin: '超级管理员' }[role] || role
}

function formatDuration(seconds) {
  const value = Math.max(0, Number(seconds || 0))
  if (value < 60) return `${Math.floor(value)} 秒`
  if (value < 3600) return `${Math.floor(value / 60)} 分钟`
  const hours = Math.floor(value / 3600)
  const minutes = Math.floor((value % 3600) / 60)
  return minutes ? `${hours} 小时 ${minutes} 分` : `${hours} 小时`
}

function formatTime(timestamp) {
  if (!timestamp) return '从未'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(Number(timestamp) * 1000))
}

async function loadData() {
  if (loading.value || props.user.must_change_password) return
  loading.value = true
  error.value = ''
  try {
    const [summary, accounts] = await Promise.all([
      api.get('/api/admin/overview?days=7', { force: true }),
      api.get('/api/admin/users?limit=100', { force: true }),
    ])
    overview.value = summary
    users.value = accounts.users || []
  } catch (exc) {
    error.value = exc.message || '管理员数据加载失败'
  } finally {
    loading.value = false
  }
}

async function changePassword() {
  formError.value = ''
  if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,128}$/.test(passwordForm.next)) {
    formError.value = '新密码必须包含英文大写、小写、数字和特殊字符'
    return
  }
  if (passwordForm.next !== passwordForm.confirm) {
    formError.value = '两次输入的新密码不一致'
    return
  }
  saving.value = true
  try {
    const result = await api.post('/api/auth/change-password', { current_password: passwordForm.current, new_password: passwordForm.next })
    emit('user-changed', result.user)
    notify('success', '密码已修改，可以使用管理员控制台')
    await nextTick()
    await loadData()
  } catch (exc) {
    formError.value = exc.message || '密码修改失败'
  } finally {
    saving.value = false
  }
}

async function setRegistration(enabled) {
  saving.value = true
  try {
    const result = await api.put('/api/admin/registration', { enabled })
    overview.value.registration_enabled = result.registration_enabled
    notify('success', result.registration_enabled ? '新用户注册已开放' : '新用户注册已关闭')
  } catch (exc) { notify('error', exc.message) }
  finally { saving.value = false }
}

async function createAdmin() {
  if (!/^(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9]{8,12}$/.test(adminForm.username)) {
    notify('error', '管理员用户名必须为 8-12 位英文和数字，且两者都要有')
    return
  }
  if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,128}$/.test(adminForm.password)) {
    notify('error', '初始密码必须包含英文大写、小写、数字和特殊字符')
    return
  }
  saving.value = true
  try {
    await api.post('/api/admin/accounts', { username: adminForm.username, password: adminForm.password })
    adminForm.username = ''
    adminForm.password = ''
    notify('success', '管理员账号已创建')
    await loadData()
  } catch (exc) { notify('error', exc.message) }
  finally { saving.value = false }
}

async function toggleAccount(account) {
  saving.value = true
  try {
    await api.put(`/api/admin/users/${account.id}/status`, { active: !account.is_active })
    notify('success', account.is_active ? '账号已停用' : '账号已启用')
    await loadData()
  } catch (exc) { notify('error', exc.message) }
  finally { saving.value = false }
}

function notify(type, message) {
  const item = { id: ++noticeId, type, message }
  notices.value.push(item)
  window.setTimeout(() => removeNotice(item.id), 4200)
}
function removeNotice(id) { notices.value = notices.value.filter(item => item.id !== id) }

onMounted(() => {
  if (!props.user.must_change_password) loadData()
  refreshTimer = window.setInterval(() => {
    if (document.visibilityState === 'visible' && !props.user.must_change_password) loadData()
  }, 30000)
})
onBeforeUnmount(() => window.clearInterval(refreshTimer))
</script>
