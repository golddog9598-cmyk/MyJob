<template>
  <section class="view-stack communication-view" aria-labelledby="communication-title">
    <header class="view-heading"><div><h1 id="communication-title">沟通中心</h1><p>会话与已获取的微信记录合并显示，实时事件到达时再刷新。</p></div><button class="secondary-action compact" :disabled="loading" @click="refreshAll"><Icon icon="mdi:refresh" :class="{ spin: loading }" />刷新</button></header>

    <div class="communication-layout">
      <aside class="conversation-list" aria-label="会话列表">
        <header><strong>会话</strong><span>{{ conversations.length }}</span></header>
        <div v-if="loading && !conversations.length" class="list-skeleton"><span v-for="item in 6" :key="item"></span></div>
        <div v-else-if="!conversations.length" class="empty-state compact-empty"><Icon icon="mdi:message-outline" /><strong>暂无会话</strong><span>同步 BOSS 消息后会显示在这里。</span></div>
        <button v-for="conversation in conversations" :key="conversation.id" class="conversation-item" :class="{ active: selectedId === conversation.id }" @click="selectConversation(conversation)">
          <span class="conversation-avatar">{{ initials(conversation.hr_name) }}</span>
          <span><strong>{{ conversation.hr_name || '招聘者' }}</strong><small>{{ conversation.hr_company || conversation.job_title || '岗位信息待同步' }}</small><em>{{ conversation.last_message_text || '暂无消息' }}</em></span>
          <b v-if="conversation.unread_count">{{ conversation.unread_count }}</b>
        </button>
      </aside>

      <section class="chat-workspace">
        <header v-if="selectedConversation">
          <div><strong>{{ selectedConversation.hr_name }}</strong><span>{{ [selectedConversation.hr_company, selectedConversation.job_title].filter(Boolean).join(' · ') || '岗位信息待同步' }}</span></div>
          <div><button class="text-action" :disabled="syncing" @click="syncMessages"><Icon icon="mdi:sync" :class="{ spin: syncing }" />同步 BOSS</button><button class="text-action" @click="toggleAutoReply">{{ selectedConversation.auto_reply_enabled ? '暂停自动回复' : '恢复自动回复' }}</button></div>
        </header>
        <div v-else class="empty-state chat-empty"><Icon icon="mdi:message-text-outline" /><strong>选择一个会话</strong><span>消息只在选择会话或收到实时事件时加载。</span></div>
        <template v-if="selectedConversation">
          <div class="message-list" aria-live="polite">
            <div v-if="loadingMessages" class="message-skeleton"><span v-for="item in 5" :key="item"></span></div>
            <div v-else-if="!messages.length" class="empty-state compact-empty"><strong>暂无消息内容</strong><span>点击同步 BOSS 读取当前会话。</span></div>
            <article v-for="message in messages" :key="message.id || `${message.sender}-${message.created_at}-${message.content}`" :class="message.sender === 'me' ? 'mine' : 'theirs'">
              <p>{{ message.content }}</p><time>{{ formatTime(message.platform_time || message.created_at) }}</time>
            </article>
          </div>
          <form class="message-composer" @submit.prevent="sendMessage">
            <label for="message-input">发送消息</label>
            <textarea id="message-input" v-model.trim="draft" rows="2" placeholder="输入要发送给招聘者的内容" @keydown.enter.exact.prevent="sendMessage"></textarea>
            <button class="primary-action" :disabled="sending || !draft"><Icon :icon="sending ? 'mdi:loading' : 'mdi:send-outline'" :class="{ spin: sending }" />发送</button>
          </form>
        </template>
      </section>

      <aside class="wechat-panel" aria-label="微信记录">
        <header><strong>微信记录</strong><span>{{ exchanges.length }}</span></header>
        <div v-if="!exchanges.length" class="empty-state compact-empty"><Icon icon="mdi:wechat" /><strong>还没有微信记录</strong><span>识别到招聘者微信后会自动汇总。</span></div>
        <article v-for="item in exchanges" :key="item.id"><div><strong>{{ item.hr_name || '招聘者' }}</strong><span>{{ item.hr_company || item.job_title || '公司待补充' }}</span></div><code>{{ item.hr_wechat }}</code></article>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { Icon } from '@iconify/vue'
import { api } from '../api'

const props = defineProps({ refreshKey: { type: Number, default: 0 } })
const emit = defineEmits(['notify', 'changed'])
const conversations = ref([])
const exchanges = ref([])
const selectedId = ref(null)
const selectedConversation = ref(null)
const messages = ref([])
const draft = ref('')
const loading = ref(false)
const loadingMessages = ref(false)
const syncing = ref(false)
const sending = ref(false)

const initials = value => String(value || 'HR').trim().slice(0, 2).toUpperCase()
const formatTime = value => value ? new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''

async function refreshAll() {
  loading.value = true
  try {
    const [conversationResult, exchangeResult] = await Promise.all([
      api.get('/api/conversations', { force: true }), api.get('/api/wechat-exchanges', { force: true }),
    ])
    conversations.value = conversationResult.conversations || []
    exchanges.value = exchangeResult.exchanges || []
    if (selectedId.value) {
      const fresh = conversations.value.find(item => item.id === selectedId.value)
      if (fresh) selectedConversation.value = fresh
    }
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { loading.value = false }
}

async function selectConversation(conversation) {
  selectedId.value = conversation.id
  selectedConversation.value = conversation
  await loadMessages()
}

async function loadMessages() {
  if (!selectedId.value) return
  loadingMessages.value = true
  try {
    const result = await api.get(`/api/conversations/${selectedId.value}/messages?limit=100`, { force: true })
    messages.value = result.messages || []
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { loadingMessages.value = false }
}

async function syncMessages() {
  syncing.value = true
  try {
    const result = await api.post(`/api/conversations/${selectedId.value}/sync`)
    messages.value = result.messages || []
    emit('notify', { type: result.success ? 'success' : 'info', message: result.message || '消息已同步' })
    await refreshAll()
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { syncing.value = false }
}

async function sendMessage() {
  if (!draft.value || sending.value) return
  sending.value = true
  try {
    await api.post(`/api/conversations/${selectedId.value}/send`, { content: draft.value })
    draft.value = ''
    await loadMessages()
    emit('changed')
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { sending.value = false }
}

async function toggleAutoReply() {
  const enabled = Boolean(selectedConversation.value?.auto_reply_enabled)
  try {
    await api.post(`/api/conversations/${selectedId.value}/${enabled ? 'pause' : 'resume'}`)
    selectedConversation.value.auto_reply_enabled = enabled ? 0 : 1
    emit('notify', { type: 'success', message: enabled ? '当前会话已暂停自动回复' : '当前会话已恢复自动回复' })
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
}

watch(() => props.refreshKey, async () => { await refreshAll(); await loadMessages() })
onMounted(refreshAll)
</script>
