<template>
  <section class="view-stack" aria-labelledby="overview-title">
    <header class="view-heading">
      <div><h1 id="overview-title">今天的求职进度</h1><p>只显示当前需要处理的事项，数据来自本地数据库。</p></div>
      <button class="text-action" :disabled="loading" @click="$emit('refresh')"><Icon icon="mdi:refresh" :class="{ spin: loading }" />刷新</button>
    </header>

    <div v-if="loading && !summary" class="overview-skeleton" aria-label="正在加载概览">
      <span v-for="item in 4" :key="item"></span>
    </div>
    <template v-else>
      <div class="metric-strip">
        <article><span>待投递</span><strong>{{ stats.pending || 0 }}</strong><small>需要检查岗位与简历</small></article>
        <article><span>今日已投递</span><strong>{{ stats.today_applications || 0 }}</strong><small>上限 {{ stats.daily_limit || 0 }}</small></article>
        <article><span>需要回复</span><strong>{{ stats.replied || 0 }}</strong><small>最近 24 小时</small></article>
        <article><span>面试或微信</span><strong>{{ stats.interview || 0 }}</strong><small>高意向会话</small></article>
      </div>

      <div class="overview-grid">
        <section class="surface-block priority-block">
          <header><div><h2>下一步</h2><p>按风险从低到高安排操作。</p></div></header>
          <div class="priority-list">
            <button @click="$emit('navigate', 'jobs')"><Icon icon="mdi:briefcase-search-outline" /><span><strong>筛选岗位</strong><small>{{ stats.pending || 0 }} 个岗位等待处理</small></span><Icon icon="mdi:chevron-right" /></button>
            <button @click="$emit('navigate', 'resume')"><Icon icon="mdi:file-document-edit-outline" /><span><strong>检查主简历</strong><small>先确认事实，再生成岗位定制稿</small></span><Icon icon="mdi:chevron-right" /></button>
            <button @click="$emit('navigate', 'communication')"><Icon icon="mdi:message-processing-outline" /><span><strong>处理回复</strong><small>{{ stats.replied || 0 }} 个会话需要关注</small></span><Icon icon="mdi:chevron-right" /></button>
          </div>
        </section>

        <section class="surface-block system-block">
          <header><div><h2>运行状态</h2><p>应用账号已认证，BOSS 登录单独管理。</p></div></header>
          <dl class="status-list">
            <div><dt>浏览器</dt><dd :class="status.browser_running ? 'good' : 'muted'">{{ status.browser_running ? '运行中' : '未启动' }}</dd></div>
            <div><dt>消息监控</dt><dd :class="status.monitor_running ? 'good' : 'muted'">{{ status.monitor_running ? status.monitor_paused ? '已暂停' : '运行中' : '未启动' }}</dd></div>
            <div><dt>自动回复</dt><dd :class="status.auto_reply_enabled ? 'good' : 'muted'">{{ status.auto_reply_enabled ? '已开启' : '已关闭' }}</dd></div>
          </dl>
          <button class="secondary-action" @click="$emit('navigate', 'settings')">查看系统设置</button>
        </section>
      </div>

      <section class="surface-block recent-block">
        <header><div><h2>最近岗位</h2><p>仅加载最近 6 条，避免概览页重复读取完整列表。</p></div><button class="text-action" @click="$emit('navigate', 'jobs')">查看全部</button></header>
        <div v-if="!recentJobs.length" class="empty-state"><Icon icon="mdi:briefcase-outline" /><strong>还没有岗位记录</strong><span>启动 BOSS 浏览器后到岗位中心搜索。</span></div>
        <div v-else class="recent-job-list">
          <article v-for="job in recentJobs" :key="job.id">
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

const props = defineProps({ summary: Object, loading: Boolean })
defineEmits(['refresh', 'navigate'])

const status = computed(() => props.summary?.status || {})
const stats = computed(() => props.summary?.stats || {})
const recentJobs = computed(() => props.summary?.recent_jobs || [])

const jobStatus = value => ({ pending: '待投递', applied: '已投递', replied: '需回复', filtered: '已过滤', skipped: '已跳过', failed: '失败' }[value] || value || '未知')
</script>
