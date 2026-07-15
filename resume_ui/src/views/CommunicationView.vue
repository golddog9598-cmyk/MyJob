<template>
  <section class="view-stack communication-view" aria-labelledby="communication-title">
    <header class="view-heading"><div><h1 id="communication-title">沟通中心</h1><p>会话和微信记录由浏览器扩展读取，并仅缓存在当前浏览器。</p></div><div class="view-heading-actions"><button class="secondary-action compact" :disabled="syncing" @click="syncPlatform"><Icon icon="mdi:sync" :class="{ spin: syncing }" />同步当前平台</button><button class="secondary-action compact" :disabled="loading" @click="refreshAll"><Icon icon="mdi:refresh" :class="{ spin: loading }" />读取本地</button></div></header>

    <div class="communication-layout">
      <aside class="conversation-list" aria-label="会话列表">
        <header><strong>会话</strong><span>{{ conversations.length }}</span></header>
        <div v-if="loading && !conversations.length" class="list-skeleton"><span v-for="item in 6" :key="item"></span></div>
        <div v-else-if="!conversations.length" class="empty-state compact-empty"><Icon icon="mdi:message-outline" /><strong>暂无会话</strong><span>登录平台后点击“同步当前平台”。</span></div>
        <button v-for="conversation in conversations" :key="conversation.id" class="conversation-item" :class="{ active: selectedId === conversation.id }" @click="selectConversation(conversation)">
          <span class="conversation-avatar">{{ initials(conversation.hr_name) }}</span>
          <span><strong>{{ conversation.hr_name || '招聘者' }}</strong><small>{{ conversation.hr_company || conversation.job_title || '岗位信息待同步' }}</small><em>{{ conversation.last_message_text || '暂无消息' }}</em></span>
          <b v-if="conversation.unread_count">{{ conversation.unread_count }}</b>
        </button>
      </aside>

      <section class="chat-workspace">
        <header v-if="selectedConversation">
          <div><strong>{{ selectedConversation.hr_name }}</strong><span>{{ [selectedConversation.hr_company, selectedConversation.job_title].filter(Boolean).join(' · ') || '岗位信息待同步' }}</span></div>
          <div><button class="text-action" :disabled="syncing" @click="syncMessages"><Icon icon="mdi:sync" :class="{ spin: syncing }" />同步消息</button><button class="text-action" @click="toggleAutoReply">{{ selectedConversation.auto_reply_enabled ? '暂停自动回复' : '恢复自动回复' }}</button></div>
        </header>
        <div v-else class="empty-state chat-empty"><Icon icon="mdi:message-text-outline" /><strong>选择一个会话</strong><span>消息只在选择会话或收到实时事件时加载。</span></div>
        <template v-if="selectedConversation">
          <div class="message-list" aria-live="polite">
            <div v-if="loadingMessages" class="message-skeleton"><span v-for="item in 5" :key="item"></span></div>
            <div v-else-if="!messages.length" class="empty-state compact-empty"><strong>暂无消息内容</strong><span>在招聘平台打开会话后点击同步消息。</span></div>
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
import { platformBridge } from '../platformBridge'
import { platformStore } from '../platformStore'

const props = defineProps({ refreshKey: { type: Number, default: 0 }, platform: { type: String, default: 'boss' } })
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
    const [conversationResult, exchangeResult] = await Promise.all([platformStore.listConversations(), platformStore.listExchanges()])
    conversations.value = conversationResult
    exchanges.value = exchangeResult
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
    messages.value = await platformStore.listMessages(selectedId.value)
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { loadingMessages.value = false }
}

async function syncMessages() {
  syncing.value = true
  try {
    const platform = selectedConversation.value?.platform || props.platform
    const result = await platformBridge.syncMessages({ platform, conversation: selectedConversation.value })
    await platformStore.saveMessages(platform, selectedId.value, result.messages || [])
    messages.value = await platformStore.listMessages(selectedId.value)
    emit('notify', { type: 'success', message: '消息已同步到浏览器本地缓存' })
    await refreshAll()
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { syncing.value = false }
}

async function sendMessage() {
  if (!draft.value || sending.value) return
  sending.value = true
  try {
    const platform = selectedConversation.value?.platform || props.platform
    const content = draft.value
    await platformBridge.sendMessage({ platform, conversation: selectedConversation.value, content })
    await platformStore.saveMessages(platform, selectedId.value, [{ sender: 'me', content, created_at: new Date().toISOString() }])
    draft.value = ''
    await loadMessages()
    emit('changed')
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { sending.value = false }
}

async function toggleAutoReply() {
  const enabled = Boolean(selectedConversation.value?.auto_reply_enabled)
  try {
    selectedConversation.value = await platformStore.updateConversation(selectedId.value, { auto_reply_enabled: !enabled })
    emit('notify', { type: 'success', message: enabled ? '当前会话已暂停自动回复' : '当前会话已恢复自动回复' })
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
}

async function syncPlatform() {
  syncing.value = true
  try {
    const result = await platformBridge.syncConversations({ platform: props.platform })
    await Promise.all([
      platformStore.saveConversations(props.platform, result.conversations || []),
      platformStore.saveExchanges(props.platform, result.exchanges || []),
    ])
    await refreshAll()
    emit('changed')
    emit('notify', { type: 'success', message: '当前平台会话已同步到浏览器本地缓存' })
  } catch (exc) { emit('notify', { type: 'error', message: exc.message }) }
  finally { syncing.value = false }
}

watch(() => props.refreshKey, async () => { await refreshAll(); await loadMessages() })
onMounted(refreshAll)
</script>
