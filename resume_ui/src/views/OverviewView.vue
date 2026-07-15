<template>
  <section class="view-stack" aria-labelledby="overview-title">
    <header class="view-heading">
      <div><h1 id="overview-title">全部平台求职进度</h1><p>上方汇总四个平台，下方按所选平台查看明细。数据只保存在当前浏览器。</p></div>
      <button class="text-action" :disabled="loading" @click="$emit('refresh')"><Icon icon="mdi:refresh" :class="{ spin: loading }" />刷新</button>
    </header>

    <div v-if="loading && !summary" class="overview-skeleton" aria-label="正在加载概览">
      <span v-for="item in 4" :key="item"></span>
    </div>
    <template v-else>
      <div class="metric-strip" aria-label="全部平台汇总">
        <article><span>全部待投递</span><strong>{{ stats.pending || 0 }}</strong><small>四个平台合计</small></article>
        <article><span>今日已投递</span><strong>{{ stats.today_applications || 0 }}</strong><small>本地上限 {{ stats.daily_limit || 0 }}</small></article>
        <article><span>需要回复</span><strong>{{ stats.replied || 0 }}</strong><small>岗位和未读会话</small></article>
        <article><span>面试或微信</span><strong>{{ stats.interview || 0 }}</strong><small>全部高意向记录</small></article>
      </div>

      <div class="overview-grid">
        <section class="surface-block priority-block">
          <header><div><h2>下一步</h2><p>所有操作在用户浏览器内完成。</p></div></header>
          <div class="priority-list">
            <button @click="$emit('navigate', 'jobs')"><Icon icon="mdi:briefcase-search-outline" /><span><strong>筛选岗位</strong><small>{{ selectedStats.pending || 0 }} 个{{ selectedLabel }}岗位等待处理</small></span><Icon icon="mdi:chevron-right" /></button>
            <button @click="$emit('navigate', 'resume')"><Icon icon="mdi:file-document-edit-outline" /><span><strong>检查主简历</strong><small>确认事实后再准备岗位定制稿</small></span><Icon icon="mdi:chevron-right" /></button>
            <button @click="$emit('navigate', 'communication')"><Icon icon="mdi:message-processing-outline" /><span><strong>处理回复</strong><small>{{ selectedStats.replied || 0 }} 个{{ selectedLabel }}事项需要关注</small></span><Icon icon="mdi:chevron-right" /></button>
          </div>
        </section>

        <section class="surface-block system-block">
          <header><div><h2>用户侧运行状态</h2><p>后端不接收招聘平台数据。</p></div></header>
          <dl class="status-list">
            <div><dt>浏览器扩展</dt><dd :class="runtime.available ? 'good' : 'muted'">{{ runtime.available ? '已连接' : '未连接' }}</dd></div>
            <div><dt>平台窗口</dt><dd :class="runtime.browser_running ? 'good' : 'muted'">{{ runtime.browser_running ? '运行中' : '未启动' }}</dd></div>
            <div><dt>数据位置</dt><dd class="good">IndexedDB 本地缓存</dd></div>
          </dl>
          <button class="secondary-action" @click="$emit('navigate', 'settings')">查看用户侧设置</button>
        </section>
      </div>

      <section class="surface-block platform-detail-block">
        <header>
          <div><h2>平台明细</h2><p>选择平台后只显示该平台的统计和岗位。</p></div>
          <div class="platform-detail-switcher" role="group" aria-label="选择平台明细">
            <button v-for="item in platforms" :key="item.id" :class="{ active: platform === item.id }" :aria-pressed="platform === item.id" @click="$emit('platform-change', item.id)">{{ item.shortLabel }}</button>
          </div>
        </header>
        <div class="platform-detail-metrics">
          <span><b>{{ selectedStats.pending || 0 }}</b>待投递</span>
          <span><b>{{ selectedStats.today_applications || 0 }}</b>今日已投递</span>
          <span><b>{{ selectedStats.replied || 0 }}</b>需要回复</span>
          <span><b>{{ selectedStats.interview || 0 }}</b>面试或微信</span>
        </div>
        <div v-if="!selectedJobs.length" class="empty-state"><Icon icon="mdi:briefcase-outline" /><strong>{{ selectedLabel }}暂无岗位记录</strong><span>登录该平台后到岗位中心搜索，结果会缓存在当前浏览器。</span></div>
        <div v-else class="recent-job-list">
          <article v-for="job in selectedJobs" :key="job.id">
            <div><strong>{{ job.job_title || '未命名岗位' }}</strong><span>{{ job.company || '公司待补充' }} · {{ job.city || '城市不限' }}</span></div>
            <span class="status-text" :data-status="job.status">{{ jobStatus(job.status) }}</span>
          </article>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { Icon } from '@iconify/vue'

const props = defineProps({
  summary: Object,
  loading: Boolean,
  platform: { type: String, default: 'boss' },
  platforms: { type: Array, default: () => [] },
  runtime: { type: Object, default: () => ({}) },
})
defineEmits(['refresh', 'navigate', 'platform-change'])

const stats = computed(() => props.summary?.stats || {})
const selectedDetail = computed(() => props.summary?.by_platform?.[props.platform] || {})
const selectedStats = computed(() => selectedDetail.value.stats || {})
const selectedJobs = computed(() => selectedDetail.value.recent_jobs || [])
const selectedLabel = computed(() => props.platforms.find(item => item.id === props.platform)?.label || '当前平台')

const jobStatus = value => ({ pending: '待投递', applied: '已投递', replied: '需回复', interview: '面试', wechat: '已换微信', filtered: '已过滤', skipped: '已跳过', failed: '失败' }[value] || value || '未知')
</script>
