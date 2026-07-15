<template>
  <section class="view-stack" aria-labelledby="settings-title">
    <header class="view-heading"><div><h1 id="settings-title">设置与安全</h1><p>招聘平台与自动化配置只保存在当前浏览器，不会发送到后端。</p></div><button class="secondary-action compact" :disabled="loading" @click="loadSettings"><Icon icon="mdi:refresh" :class="{ spin: loading }" />刷新</button></header>

    <div v-if="loading && !ready" class="settings-skeleton"><span v-for="item in 4" :key="item"></span></div>
    <form v-else class="settings-grid" @submit.prevent="saveSettings">
      <section class="surface-block settings-section">
        <header><div><h2>AI 模型</h2><p>密钥只保存在浏览器 IndexedDB，用于用户侧处理。</p></div><span class="status-text" :data-status="localAiConfigured ? 'active' : 'paused'">{{ localAiConfigured ? '本地已配置' : '未配置' }}</span></header>
        <label><span>平台</span><select v-model="settings.ai_platform"><option value="">选择平台</option><option value="deepseek">DeepSeek</option><option value="openrouter">OpenRouter</option><option value="mimo">小米 MiMo</option><option value="custom">自定义</option></select></label>
        <label><span>API Key</span><input v-model="apiKey" type="password" autocomplete="off" :placeholder="localAiConfigured ? '本地已配置，留空表示不修改' : '输入 API Key'" /></label>
        <label><span>Base URL</span><input v-model.trim="settings.ai_base_url" placeholder="https://api.example.com/v1" /></label>
        <label><span>模型</span><input v-model.trim="settings.ai_model" placeholder="模型名称" /></label>
      </section>

      <section class="surface-block settings-section">
        <header><div><h2>求职资料</h2><p>用于搜索默认值和与招聘者沟通。</p></div></header>
        <label><span>默认城市</span><input v-model.trim="settings.default_city" placeholder="深圳" /></label>
        <label><span>微信号</span><input v-model.trim="settings.wechat_id" placeholder="仅在合适时发送给招聘者" /></label>
        <label><span>默认搜索关键词</span><input v-model.trim="settings.search_keywords" placeholder="AI Agent, 产品经理" /></label>
        <label><span>固定招呼语</span><textarea v-model="settings.greeting_template" rows="4" placeholder="{job_title} 会替换为实际岗位名"></textarea></label>
      </section>

      <section class="surface-block settings-section">
        <header><div><h2>自动化边界</h2><p>保守默认值更适合长期运行。</p></div></header>
        <div class="form-grid-two">
          <label v-for="platform in platforms" :key="platform.id"><span>{{ platform.label }}每日投递上限</span><input v-model.number="settings.daily_apply_limits[platform.id]" type="number" min="1" max="50" /><small>每个平台最多 50</small></label>
          <label><span>不活跃天数</span><input v-model="settings.max_hr_inactive_days" type="number" min="1" max="60" /></label>
          <label><span>最短回复间隔</span><div class="unit-field"><input v-model="settings.min_reply_delay_sec" type="number" min="10" max="300" /><span>秒</span></div></label>
          <label><span>最长回复间隔</span><div class="unit-field"><input v-model="settings.max_reply_delay_sec" type="number" min="20" max="600" /><span>秒</span></div></label>
        </div>
        <label class="check-field"><input v-model="autoReply" type="checkbox" /><span>开启 AI 自动回复</span></label>
        <label class="check-field"><input v-model="dedupCompany" type="checkbox" /><span>默认过滤已投递公司</span></label>
        <label class="check-field"><input v-model="filterInactive" type="checkbox" /><span>默认跳过不活跃招聘者</span></label>
      </section>

      <section class="surface-block settings-section diagnostics-section">
        <header><div><h2>用户侧诊断</h2><p>只检查浏览器扩展和本地缓存，不读取招聘平台后端数据。</p></div><button type="button" class="text-action" @click="loadDoctor"><Icon icon="mdi:stethoscope" />重新检查</button></header>
        <dl v-if="doctor" class="status-list">
          <div v-for="(item, key) in doctor.checks" :key="key"><dt>{{ checkLabel(key) }}</dt><dd :class="item.ok ? 'good' : 'muted'">{{ item.detail ?? item }}</dd></div>
        </dl>
        <div v-else class="empty-state compact-empty"><span>尚未运行诊断</span></div>
      </section>

      <section class="surface-block settings-section security-section">
        <header><div><h2>工作台密码</h2><p>修改后其他已登录会话会立即失效。</p></div></header>
        <label><span>当前密码</span><input v-model="password.current" type="password" autocomplete="current-password" /></label>
        <label><span>新密码</span><input v-model="password.next" type="password" autocomplete="new-password" minlength="8" /></label>
        <label><span>确认新密码</span><input v-model="password.confirm" type="password" autocomplete="new-password" minlength="8" /></label>
        <button type="button" class="secondary-action" :disabled="changingPassword || !password.current || !password.next" @click="changePassword">修改密码</button>
      </section>

      <div class="settings-save-bar"><span>{{ dirtyHint }}</span><button class="primary-action" type="submit" :disabled="saving"><Icon :icon="saving ? 'mdi:loading' : 'mdi:content-save-outline'" :class="{ spin: saving }" />{{ saving ? '保存中' : '保存设置' }}</button></div>
    </form>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Icon } from '@iconify/vue'
import { api } from '../api'
import { platformBridge } from '../platformBridge'
import { PLATFORMS } from '../platformCatalog'
import { platformStore } from '../platformStore'

const emit = defineEmits(['notify', 'changed'])
const platforms = PLATFORMS
const settings = reactive({})
const password = reactive({ current: '', next: '', confirm: '' })
const apiKey = ref('')
const doctor = ref(null)
const loading = ref(false)
const saving = ref(false)
const changingPassword = ref(false)
const ready = ref(false)
const localAiConfigured = computed(() => Boolean(settings.ai_api_key))
const autoReply = computed({ get: () => Boolean(settings.auto_reply_enabled), set: value => { settings.auto_reply_enabled = value } })
const dedupCompany = computed({ get: () => settings.dedup_company_by_default !== false, set: value => { settings.dedup_company_by_default = value } })
const filterInactive = computed({ get: () => settings.filter_inactive_hr !== false, set: value => { settings.filter_inactive_hr = value } })
const dirtyHint = computed(() => apiKey.value ? '新密钥将写入当前浏览器' : '配置仅在点击保存后写入当前浏览器')

async function loadSettings() {
  loading.value = true
  try {
    const result = await platformStore.getSettings()
    Object.keys(settings).forEach(key => delete settings[key])
    Object.assign(settings, result)
    ready.value = true
    await loadDoctor()
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { loading.value = false }
}

async function saveSettings() {
  saving.value = true
  try {
    const payload = { ...settings }
    if (apiKey.value) payload.ai_api_key = apiKey.value
    const saved = await platformStore.saveSettings(payload)
    Object.assign(settings, saved)
    apiKey.value = ''
    emit('notify', { type: 'success', message: '设置已保存到当前浏览器' })
    emit('changed')
    await loadDoctor()
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { saving.value = false }
}

async function loadDoctor() {
  try {
    const [runtime, summary] = await Promise.all([platformBridge.heartbeat(), platformStore.getSummary()])
    doctor.value = {
      checks: {
        extension: { ok: runtime.available, detail: runtime.available ? '已连接' : '未安装或未连接' },
        browser: { ok: runtime.browser_running, detail: runtime.browser_running ? '平台窗口运行中' : '未启动平台窗口' },
        local_cache: { ok: true, detail: 'IndexedDB 可用' },
        today_applications: { ok: true, detail: summary.stats.today_applications || 0 },
        pending_jobs: { ok: true, detail: summary.stats.pending || 0 },
      },
    }
  }
  catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
}

async function changePassword() {
  if (password.next !== password.confirm) {
    emit('notify', { type: 'error', message: '两次输入的新密码不一致' })
    return
  }
  changingPassword.value = true
  try {
    await api.post('/api/auth/change-password', { current_password: password.current, new_password: password.next })
    password.current = ''; password.next = ''; password.confirm = ''
    emit('notify', { type: 'success', message: '工作台密码已修改' })
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { changingPassword.value = false }
}

const checkLabel = key => ({ extension: '浏览器扩展', browser: '平台窗口', local_cache: '本地缓存', today_applications: '今日投递', pending_jobs: '待投递' }[key] || key)
onMounted(() => loadSettings())
</script>
