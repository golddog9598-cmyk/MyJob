import { PLATFORM_IDS, PLATFORMS } from './platformCatalog'

const DB_NAME = 'myjob-client-platform-data'
const DB_VERSION = 1
const CHANNEL_NAME = 'myjob-platform-data'
const STORE_NAMES = ['jobs', 'conversations', 'messages', 'campaigns', 'exchanges', 'tailored', 'meta']
const DEFAULT_SETTINGS = Object.freeze({
  ai_platform: '',
  ai_api_key: '',
  ai_base_url: '',
  ai_model: '',
  default_city: '全国',
  wechat_id: '',
  search_keywords: '',
  greeting_template: '你好，我对{job_title}岗位很感兴趣，希望进一步沟通。',
  daily_apply_limit: 15,
  max_hr_inactive_days: 7,
  min_reply_delay_sec: 30,
  max_reply_delay_sec: 90,
  auto_reply_enabled: false,
  dedup_company_by_default: true,
  filter_inactive_hr: true,
})

let databasePromise
const listeners = new Set()
const channel = typeof BroadcastChannel === 'function' ? new BroadcastChannel(CHANNEL_NAME) : null

channel?.addEventListener('message', () => listeners.forEach(listener => listener()))

function openDatabase() {
  if (databasePromise) return databasePromise
  databasePromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onerror = () => reject(request.error || new Error('无法打开浏览器本地数据库'))
    request.onupgradeneeded = () => {
      const db = request.result
      const jobs = db.createObjectStore('jobs', { keyPath: 'id' })
      jobs.createIndex('platform', 'platform', { unique: false })
      jobs.createIndex('status', 'status', { unique: false })
      jobs.createIndex('updated_at', 'updated_at', { unique: false })

      const conversations = db.createObjectStore('conversations', { keyPath: 'id' })
      conversations.createIndex('platform', 'platform', { unique: false })
      conversations.createIndex('updated_at', 'updated_at', { unique: false })

      const messages = db.createObjectStore('messages', { keyPath: 'id' })
      messages.createIndex('conversation_id', 'conversation_id', { unique: false })
      messages.createIndex('platform', 'platform', { unique: false })

      const campaigns = db.createObjectStore('campaigns', { keyPath: 'id' })
      campaigns.createIndex('platform', 'platform', { unique: false })

      const exchanges = db.createObjectStore('exchanges', { keyPath: 'id' })
      exchanges.createIndex('platform', 'platform', { unique: false })

      const tailored = db.createObjectStore('tailored', { keyPath: 'id' })
      tailored.createIndex('platform', 'platform', { unique: false })

      db.createObjectStore('meta', { keyPath: 'key' })
    }
    request.onsuccess = () => resolve(request.result)
  })
  return databasePromise
}

async function transaction(storeName, mode, operation) {
  const db = await openDatabase()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, mode)
    const store = tx.objectStore(storeName)
    let result
    try {
      result = operation(store)
    } catch (error) {
      reject(error)
      return
    }
    tx.oncomplete = () => resolve(result)
    tx.onerror = () => reject(tx.error || new Error('浏览器本地数据操作失败'))
    tx.onabort = () => reject(tx.error || new Error('浏览器本地数据操作已取消'))
  })
}

async function requestResult(storeName, operation) {
  const db = await openDatabase()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly')
    const request = operation(tx.objectStore(storeName))
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error || new Error('读取浏览器本地数据失败'))
  })
}

function emitChanged() {
  listeners.forEach(listener => listener())
  channel?.postMessage({ type: 'changed', at: Date.now() })
  window.dispatchEvent(new CustomEvent('myjob:platform-data-changed'))
}

function nowIso() {
  return new Date().toISOString()
}

function stableHash(value) {
  let hash = 2166136261
  for (const character of String(value || '')) {
    hash ^= character.charCodeAt(0)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(36)
}

function validPlatform(value) {
  return PLATFORM_IDS.includes(value) ? value : 'boss'
}

function normalizeJob(platform, job) {
  const source = validPlatform(job.platform || platform)
  const url = String(job.job_url || job.url || '').trim()
  const id = String(job.id || `${source}:${stableHash(url || `${job.company}:${job.job_title}`)}`)
  const previousCreated = job.created_at || nowIso()
  return {
    ...job,
    id,
    platform: source,
    job_url: url,
    job_title: String(job.job_title || job.title || '').trim(),
    company: String(job.company || '').trim(),
    city: String(job.city || '').trim(),
    salary: String(job.salary || '').trim(),
    description: String(job.description || '').trim(),
    status: job.status || 'pending',
    created_at: previousCreated,
    updated_at: nowIso(),
  }
}

async function putMany(storeName, values) {
  await transaction(storeName, 'readwrite', store => {
    values.forEach(value => store.put(value))
  })
  emitChanged()
  return values
}

async function getAll(storeName) {
  return requestResult(storeName, store => store.getAll())
}

export async function saveJobs(platform, jobs = []) {
  const normalized = jobs.map(job => normalizeJob(platform, job))
  return putMany('jobs', normalized)
}

export async function listJobs({ platform = '', status = '', limit = 20, offset = 0 } = {}) {
  const all = await getAll('jobs')
  const filtered = all
    .filter(job => !platform || job.platform === platform)
    .filter(job => !status || job.status === status)
    .sort((left, right) => String(right.updated_at).localeCompare(String(left.updated_at)))
  return { jobs: filtered.slice(offset, offset + limit), total: filtered.length }
}

export async function updateJob(id, patch) {
  const existing = await requestResult('jobs', store => store.get(id))
  if (!existing) throw new Error('本地岗位记录不存在')
  const updated = normalizeJob(existing.platform, { ...existing, ...patch, id })
  await putMany('jobs', [updated])
  return updated
}

export async function saveConversations(platform, conversations = []) {
  const source = validPlatform(platform)
  const normalized = conversations.map(item => ({
    ...item,
    id: String(item.id || `${source}:conversation:${stableHash(`${item.hr_name}:${item.job_title}:${item.hr_company}`)}`),
    platform: validPlatform(item.platform || source),
    updated_at: item.updated_at || nowIso(),
    auto_reply_enabled: Boolean(item.auto_reply_enabled),
    unread_count: Number(item.unread_count || 0),
  }))
  return putMany('conversations', normalized)
}

export async function listConversations(platform = '') {
  const all = await getAll('conversations')
  return all
    .filter(item => !platform || item.platform === platform)
    .sort((left, right) => String(right.updated_at).localeCompare(String(left.updated_at)))
}

export async function updateConversation(id, patch) {
  const existing = await requestResult('conversations', store => store.get(id))
  if (!existing) throw new Error('本地会话不存在')
  const updated = { ...existing, ...patch, id, updated_at: nowIso() }
  await putMany('conversations', [updated])
  return updated
}

export async function saveMessages(platform, conversationId, messages = []) {
  const source = validPlatform(platform)
  const normalized = messages.map((item, index) => ({
    ...item,
    id: String(item.id || `${conversationId}:message:${stableHash(`${item.sender}:${item.content}:${item.platform_time || index}`)}`),
    conversation_id: String(conversationId),
    platform: source,
    created_at: item.created_at || item.platform_time || nowIso(),
  }))
  return putMany('messages', normalized)
}

export async function listMessages(conversationId) {
  const all = await requestResult('messages', store => store.index('conversation_id').getAll(String(conversationId)))
  return all.sort((left, right) => String(left.created_at).localeCompare(String(right.created_at)))
}

export async function saveExchanges(platform, exchanges = []) {
  const source = validPlatform(platform)
  const normalized = exchanges.map(item => ({
    ...item,
    id: String(item.id || `${source}:exchange:${stableHash(`${item.hr_name}:${item.hr_wechat}`)}`),
    platform: validPlatform(item.platform || source),
    updated_at: item.updated_at || nowIso(),
  }))
  return putMany('exchanges', normalized)
}

export async function listExchanges() {
  return (await getAll('exchanges')).sort((left, right) => String(right.updated_at).localeCompare(String(left.updated_at)))
}

export async function saveCampaign(campaign) {
  const created = campaign.created_at || nowIso()
  const value = {
    ...campaign,
    id: String(campaign.id || `campaign:${Date.now()}:${stableHash(campaign.name)}`),
    platform: validPlatform(campaign.platform),
    status: campaign.status || 'active',
    created_at: created,
    updated_at: nowIso(),
    pipeline: campaign.pipeline || { review: 0, applied: 0, replied: 0, interview: 0 },
  }
  await putMany('campaigns', [value])
  return value
}

export async function listCampaigns() {
  return (await getAll('campaigns')).sort((left, right) => String(right.updated_at).localeCompare(String(left.updated_at)))
}

export async function saveTailorDraft(job) {
  const value = {
    id: `tailored:${job.id || stableHash(job.job_url)}`,
    platform: validPlatform(job.platform),
    job_id: job.id,
    job_title: job.job_title || '定制简历',
    company: job.company || '',
    city: job.city || '',
    description: job.description || '',
    status: 'local_draft',
    created_at: nowIso(),
  }
  await putMany('tailored', [value])
  return value
}

export async function listTailorDrafts() {
  return (await getAll('tailored')).sort((left, right) => String(right.created_at).localeCompare(String(left.created_at)))
}

export async function getSettings() {
  const record = await requestResult('meta', store => store.get('settings'))
  return { ...DEFAULT_SETTINGS, ...(record?.value || {}) }
}

export async function saveSettings(settings) {
  const value = { ...DEFAULT_SETTINGS, ...settings }
  await transaction('meta', 'readwrite', store => store.put({ key: 'settings', value, updated_at: nowIso() }))
  emitChanged()
  return value
}

function statsFor(jobs, conversations) {
  const today = new Date().toISOString().slice(0, 10)
  return {
    pending: jobs.filter(item => item.status === 'pending').length,
    today_applications: jobs.filter(item => item.status === 'applied' && String(item.applied_at || item.updated_at).startsWith(today)).length,
    replied: jobs.filter(item => item.status === 'replied').length + conversations.filter(item => Number(item.unread_count || 0) > 0).length,
    interview: jobs.filter(item => ['interview', 'wechat'].includes(item.status)).length + conversations.filter(item => ['interview', 'high'].includes(item.interest_level) || item.hr_wechat).length,
  }
}

export async function getSummary() {
  const [jobs, conversations, settings] = await Promise.all([getAll('jobs'), getAll('conversations'), getSettings()])
  const byPlatform = {}
  for (const platform of PLATFORMS) {
    const platformJobs = jobs.filter(item => item.platform === platform.id)
    const platformConversations = conversations.filter(item => item.platform === platform.id)
    byPlatform[platform.id] = {
      platform: platform.id,
      stats: { ...statsFor(platformJobs, platformConversations), daily_limit: Number(settings.daily_apply_limit || 15) },
      recent_jobs: platformJobs.sort((left, right) => String(right.updated_at).localeCompare(String(left.updated_at))).slice(0, 6),
      conversation_count: platformConversations.length,
    }
  }
  return {
    stats: { ...statsFor(jobs, conversations), daily_limit: Number(settings.daily_apply_limit || 15) },
    by_platform: byPlatform,
    recent_jobs: jobs.sort((left, right) => String(right.updated_at).localeCompare(String(left.updated_at))).slice(0, 6),
    recent_conversations: conversations.sort((left, right) => String(right.updated_at).localeCompare(String(left.updated_at))).slice(0, 10),
    storage: { type: 'IndexedDB', local_only: true },
  }
}

export function subscribePlatformData(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export const platformStore = {
  saveJobs,
  listJobs,
  updateJob,
  saveConversations,
  listConversations,
  updateConversation,
  saveMessages,
  listMessages,
  saveExchanges,
  listExchanges,
  saveCampaign,
  listCampaigns,
  saveTailorDraft,
  listTailorDrafts,
  getSettings,
  saveSettings,
  getSummary,
  subscribe: subscribePlatformData,
  stores: STORE_NAMES,
}
