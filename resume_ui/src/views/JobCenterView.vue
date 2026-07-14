<template>
  <section class="view-stack" aria-labelledby="jobs-title">
    <header class="view-heading">
      <div><h1 id="jobs-title">岗位中心</h1><p>搜索、筛选、投递和简历定制在一个工作流中完成。</p></div>
      <button class="secondary-action compact" :disabled="loadingJobs" @click="loadJobs(true)"><Icon icon="mdi:refresh" :class="{ spin: loadingJobs }" />刷新列表</button>
    </header>

    <section class="search-workbench">
      <form @submit.prevent="searchJobs">
        <label class="field-wide"><span>岗位关键词</span><input v-model.trim="search.keyword" required placeholder="例如：AI Agent, Python 后端" /></label>
        <label><span>城市</span><input v-model.trim="search.city" placeholder="全国" /></label>
        <label><span>薪资</span><select v-model="search.salary"><option value="">不限</option><option value="403">3-5K</option><option value="404">5-10K</option><option value="405">10-20K</option><option value="406">20-50K</option><option value="407">50K 以上</option></select></label>
        <label><span>经验</span><select v-model="search.experience"><option value="">不限</option><option value="102">应届生</option><option value="104">1-3 年</option><option value="105">3-5 年</option><option value="106">5-10 年</option></select></label>
        <label><span>学历</span><select v-model="search.degree"><option value="">不限</option><option value="202">大专</option><option value="203">本科</option><option value="204">硕士</option><option value="205">博士</option></select></label>
        <label><span>福利关键词</span><input v-model.trim="search.welfare" placeholder="双休, 五险一金" /></label>
        <div class="search-options field-wide">
          <label class="check-field"><input v-model="search.dedup_company" type="checkbox" /><span>过滤已投递公司</span></label>
          <label class="check-field"><input v-model="search.filter_inactive_hr" type="checkbox" /><span>跳过不活跃招聘者</span></label>
          <label class="inline-number"><span>最多未活跃</span><input v-model.number="search.max_hr_inactive_days" type="number" min="1" max="60" /><span>天</span></label>
        </div>
        <button class="primary-action search-submit" type="submit" :disabled="searching"><Icon :icon="searching ? 'mdi:loading' : 'mdi:magnify'" :class="{ spin: searching }" />{{ searching ? '正在搜索' : '搜索并入库' }}</button>
      </form>
      <p v-if="searchResult" class="search-result" role="status">找到 {{ searchResult.jobs_found || 0 }} 个岗位，保存 {{ searchResult.saved || 0 }} 个，过滤 {{ totalSkipped }} 个。</p>
      <p v-if="error" class="form-error" role="alert"><Icon icon="mdi:alert-circle-outline" />{{ error }}</p>
    </section>

    <section class="surface-block jobs-surface">
      <header class="jobs-toolbar">
        <div class="segmented" aria-label="岗位状态筛选">
          <button v-for="item in filters" :key="item.value" :class="{ active: statusFilter === item.value }" @click="setFilter(item.value)">{{ item.label }}</button>
        </div>
        <span>共 {{ total }} 条</span>
      </header>

      <div v-if="loadingJobs" class="table-skeleton"><span v-for="item in 6" :key="item"></span></div>
      <div v-else-if="!jobs.length" class="empty-state"><Icon icon="mdi:briefcase-search-outline" /><strong>当前筛选没有岗位</strong><span>调整筛选条件或从上方开始一次新搜索。</span></div>
      <div v-else class="job-table-wrap">
        <table class="job-table">
          <thead><tr><th>岗位</th><th>公司与城市</th><th>薪资</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="job in jobs" :key="job.id">
              <td><a :href="job.job_url" target="_blank" rel="noreferrer">{{ job.job_title || '未命名岗位' }}</a><small>{{ job.experience || '经验不限' }} · {{ job.education || '学历不限' }}</small></td>
              <td><strong>{{ job.company || '公司待补充' }}</strong><small>{{ job.city || '城市不限' }}</small></td>
              <td class="number-cell">{{ job.salary || '面议' }}</td>
              <td><span class="status-text" :data-status="job.status">{{ statusLabel(job.status) }}</span></td>
              <td><div class="row-actions">
                <button v-if="['pending','failed'].includes(job.status)" :disabled="busyId === job.id" @click="applyJob(job)">投递</button>
                <button v-if="job.status !== 'filtered'" :disabled="busyId === job.id" @click="tailorJob(job)">定制简历</button>
                <button v-if="job.status === 'pending'" class="quiet" :disabled="busyId === job.id" @click="skipJob(job)">跳过</button>
              </div></td>
            </tr>
          </tbody>
        </table>
      </div>

      <footer v-if="totalPages > 1" class="pager">
        <button :disabled="page === 1" @click="goPage(page - 1)"><Icon icon="mdi:chevron-left" />上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button :disabled="page === totalPages" @click="goPage(page + 1)">下一页<Icon icon="mdi:chevron-right" /></button>
      </footer>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Icon } from '@iconify/vue'
import { api } from '../api'

const emit = defineEmits(['notify', 'changed'])
const filters = [
  { label: '全部', value: '' }, { label: '待投递', value: 'pending' }, { label: '已投递', value: 'applied' },
  { label: '需回复', value: 'replied' }, { label: '已过滤', value: 'filtered' },
]
const search = reactive({ keyword: '', city: '全国', salary: '', experience: '', degree: '', welfare: '', dedup_company: true, filter_inactive_hr: true, max_hr_inactive_days: 7 })
const jobs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const statusFilter = ref('')
const searching = ref(false)
const loadingJobs = ref(false)
const busyId = ref(null)
const error = ref('')
const searchResult = ref(null)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const totalSkipped = computed(() => ['skipped_company', 'skipped_inactive_hr', 'skipped_keyword', 'skipped_garbled'].reduce((sum, key) => sum + Number(searchResult.value?.[key] || 0), 0))
const statusLabel = value => ({ pending: '待投递', applied: '已投递', replied: '需回复', filtered: '已过滤', skipped: '已跳过', failed: '失败' }[value] || value || '未知')

async function loadJobs(force = false) {
  loadingJobs.value = true
  error.value = ''
  const query = new URLSearchParams({ limit: String(pageSize), offset: String((page.value - 1) * pageSize) })
  if (statusFilter.value) query.set('status', statusFilter.value)
  try {
    const result = await api.get(`/api/jobs?${query}`, { force })
    jobs.value = result.jobs || []
    total.value = Number(result.total || 0)
  } catch (exc) {
    error.value = exc.message
  } finally {
    loadingJobs.value = false
  }
}

async function searchJobs() {
  searching.value = true
  error.value = ''
  searchResult.value = null
  try {
    const payload = { ...search, limit: 60 }
    for (const key of ['experience', 'degree']) payload[key] = payload[key] ? Number(payload[key]) : null
    const result = await api.post('/api/jobs/search', payload)
    searchResult.value = result
    page.value = 1
    statusFilter.value = ''
    await loadJobs(true)
    emit('changed')
  } catch (exc) {
    error.value = exc.message
  } finally {
    searching.value = false
  }
}

async function applyJob(job) {
  busyId.value = job.id
  try {
    const result = await api.post('/api/jobs/apply', { job_url: job.job_url, company_name: job.company, company_id: job.company_id })
    if (!result.success) throw new Error(result.message || '投递失败')
    emit('notify', { type: 'success', message: '岗位已投递' })
    await loadJobs(true)
    emit('changed')
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { busyId.value = null }
}

async function skipJob(job) {
  busyId.value = job.id
  try {
    await api.post(`/api/jobs/${job.id}/skip`)
    await loadJobs(true)
    emit('changed')
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { busyId.value = null }
}

async function tailorJob(job) {
  busyId.value = job.id
  try {
    await api.post('/api/jobs/tailor-resume', { application_id: job.id, job_url: job.job_url, job_title: job.job_title, company: job.company, city: job.city, description: job.description })
    emit('notify', { type: 'success', message: '岗位定制简历已生成，可在简历中心下载' })
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { busyId.value = null }
}

function setFilter(value) { statusFilter.value = value; page.value = 1; loadJobs(true) }
function goPage(value) { page.value = value; loadJobs(true) }

onMounted(() => loadJobs())
</script>
