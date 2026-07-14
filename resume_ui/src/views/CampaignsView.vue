<template>
  <section class="view-stack" aria-labelledby="campaign-title">
    <header class="view-heading"><div><h1 id="campaign-title">求职计划</h1><p>按岗位和城市组合运行，默认由你确认后再投递。</p></div><button class="secondary-action compact" :disabled="loading" @click="loadCampaigns(true)"><Icon icon="mdi:refresh" :class="{ spin: loading }" />刷新</button></header>

    <div class="campaign-layout">
      <section class="surface-block campaign-form-block">
        <header><div><h2>新建计划</h2><p>定时器只在 BOSS 浏览器已登录时工作。</p></div></header>
        <form class="stack-form" @submit.prevent="createCampaign">
          <label><span>计划名称</span><input v-model.trim="form.name" required placeholder="例如：深圳 AI 产品岗位" /></label>
          <label><span>目标岗位</span><input v-model.trim="form.keywords" required placeholder="AI 产品经理, AI Agent" /><small>使用英文逗号分隔</small></label>
          <label><span>目标城市</span><input v-model.trim="form.cities" required placeholder="深圳, 广州" /><small>使用英文逗号分隔</small></label>
          <div class="form-grid-two">
            <label><span>最低匹配分</span><input v-model.number="form.min_match_score" type="number" min="0" max="100" /></label>
            <label><span>每轮岗位上限</span><input v-model.number="form.max_jobs_per_run" type="number" min="1" max="50" /></label>
            <label><span>运行间隔</span><div class="unit-field"><input v-model.number="form.interval_hours" type="number" min="1" max="168" /><span>小时</span></div></label>
            <label><span>投递模式</span><select v-model="form.apply_mode"><option value="review">人工确认</option><option value="automatic">自动投递</option></select></label>
          </div>
          <label class="check-field"><input v-model="form.auto_tailor" type="checkbox" /><span>匹配后生成 JD 定制简历</span></label>
          <label v-if="form.apply_mode === 'automatic'" class="confirm-risk"><input v-model="form.auto_apply_confirmed" type="checkbox" /><span>我确认启用自动投递。每日上限、公司去重和风控仍然生效。</span></label>
          <p v-if="error" class="form-error" role="alert"><Icon icon="mdi:alert-circle-outline" />{{ error }}</p>
          <div class="form-actions"><button class="secondary-action" type="button" :disabled="saving" @click="createCampaign('paused')">保存为暂停</button><button class="primary-action" type="submit" :disabled="saving"><Icon :icon="saving ? 'mdi:loading' : 'mdi:calendar-check-outline'" :class="{ spin: saving }" />保存并启用</button></div>
        </form>
      </section>

      <section class="surface-block campaign-list-block">
        <header><div><h2>计划与漏斗</h2><p>运行时按匹配分排序，不重复扫描完整历史。</p></div></header>
        <div v-if="loading" class="list-skeleton"><span v-for="item in 4" :key="item"></span></div>
        <div v-else-if="!campaigns.length" class="empty-state"><Icon icon="mdi:calendar-search-outline" /><strong>还没有求职计划</strong><span>先创建一个人工确认模式的计划。</span></div>
        <div v-else class="campaign-list">
          <article v-for="campaign in campaigns" :key="campaign.id">
            <header><div><strong>{{ campaign.name }}</strong><span>{{ campaign.keywords.join(' / ') }} · {{ campaign.cities.join(' / ') }}</span></div><span class="status-text" :data-status="campaign.status">{{ campaign.status === 'active' ? '运行中' : '已暂停' }}</span></header>
            <div class="pipeline-row"><span><b>{{ campaign.pipeline?.review || 0 }}</b>待确认</span><span><b>{{ campaign.pipeline?.applied || 0 }}</b>已投递</span><span><b>{{ campaign.pipeline?.replied || 0 }}</b>已回复</span><span><b>{{ campaign.pipeline?.interview || 0 }}</b>面试</span></div>
            <footer><span>匹配分 {{ campaign.min_match_score }}，每 {{ campaign.interval_hours }} 小时</span><div><button :disabled="busyId === campaign.id" @click="runCampaign(campaign)">立即运行</button><button class="quiet" :disabled="busyId === campaign.id" @click="toggleCampaign(campaign)">{{ campaign.status === 'active' ? '暂停' : '启用' }}</button></div></footer>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Icon } from '@iconify/vue'
import { api } from '../api'

const emit = defineEmits(['notify', 'changed'])
const campaigns = ref([])
const loading = ref(false)
const saving = ref(false)
const busyId = ref(null)
const error = ref('')
const form = reactive({ name: '我的求职计划', keywords: '', cities: '', min_match_score: 60, max_jobs_per_run: 10, interval_hours: 24, auto_tailor: true, apply_mode: 'review', auto_apply_confirmed: false })

const splitValues = value => String(value || '').split(',').map(item => item.trim()).filter(Boolean)

async function loadCampaigns(force = false) {
  loading.value = true
  try { campaigns.value = (await api.get('/api/campaigns', { force })).campaigns || [] }
  catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { loading.value = false }
}

async function createCampaign(status = 'active') {
  if (typeof status !== 'string') status = 'active'
  error.value = ''
  if (form.apply_mode === 'automatic' && !form.auto_apply_confirmed) {
    error.value = '自动投递需要勾选明确确认'
    return
  }
  saving.value = true
  try {
    await api.post('/api/campaigns', { ...form, keywords: splitValues(form.keywords), cities: splitValues(form.cities), status })
    form.name = '我的求职计划'; form.keywords = ''; form.cities = ''; form.auto_apply_confirmed = false
    await loadCampaigns(true)
    emit('changed')
    emit('notify', { type: 'success', message: status === 'active' ? '计划已启用' : '计划已保存' })
  } catch (exc) { error.value = exc.message }
  finally { saving.value = false }
}

async function toggleCampaign(campaign) {
  busyId.value = campaign.id
  try {
    await api.put(`/api/campaigns/${campaign.id}/status`, { status: campaign.status === 'active' ? 'paused' : 'active' })
    await loadCampaigns(true)
    emit('changed')
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { busyId.value = null }
}

async function runCampaign(campaign) {
  busyId.value = campaign.id
  emit('notify', { type: 'info', message: '计划正在运行，完成后会自动刷新' })
  try {
    await api.post(`/api/campaigns/${campaign.id}/run`)
    await loadCampaigns(true)
    emit('changed')
    emit('notify', { type: 'success', message: '求职计划运行完成' })
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { busyId.value = null }
}

onMounted(() => loadCampaigns())
</script>
