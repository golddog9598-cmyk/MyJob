import { emptyPlatformRuntime, platformById } from './platformCatalog'

const REQUEST_TYPE = 'MYJOB_PLATFORM_REQUEST'
const RESPONSE_TYPE = 'MYJOB_PLATFORM_RESPONSE'
const EVENT_TYPE = 'MYJOB_PLATFORM_EVENT'
const pending = new Map()
const listeners = new Set()
let listening = false
let sequence = 0
let runtime = emptyPlatformRuntime(false)

function bridgeError(message, code = 'PLATFORM_BRIDGE_ERROR') {
  const error = new Error(message)
  error.code = code
  return error
}

function ensureListener() {
  if (listening) return
  listening = true
  window.addEventListener('message', event => {
    if (event.source !== window || event.data?.source !== 'myjob-extension') return
    if (event.data.type === RESPONSE_TYPE) {
      const entry = pending.get(event.data.id)
      if (!entry) return
      pending.delete(event.data.id)
      window.clearTimeout(entry.timer)
      if (event.data.ok) entry.resolve(event.data.result)
      else entry.reject(bridgeError(event.data.error || '浏览器扩展操作失败', event.data.code))
      return
    }
    if (event.data.type === EVENT_TYPE && event.data.runtime) {
      runtime = normalizeRuntime(event.data.runtime, true)
      listeners.forEach(listener => listener(runtime))
    }
  })
}

function normalizeRuntime(value, available = true) {
  const base = emptyPlatformRuntime(available)
  return {
    ...base,
    ...(value || {}),
    available,
    browser_running: Boolean(value?.browser_running),
    platforms: Object.fromEntries(Object.entries(base.platforms).map(([id, state]) => [id, {
      ...state,
      ...(value?.platforms?.[id] || {}),
      page_open: Boolean(value?.platforms?.[id]?.page_open),
      logged_in: Boolean(value?.platforms?.[id]?.logged_in),
    }])),
  }
}

function request(action, payload = {}, timeout = 15000) {
  ensureListener()
  const id = `myjob-${Date.now()}-${++sequence}`
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      pending.delete(id)
      reject(bridgeError('未检测到 MyJob 浏览器扩展，请先安装 browser_extension 目录中的扩展', 'EXTENSION_UNAVAILABLE'))
    }, timeout)
    pending.set(id, { resolve, reject, timer })
    window.postMessage({ source: 'myjob-web', type: REQUEST_TYPE, id, action, payload }, window.location.origin)
  })
}

async function heartbeat() {
  try {
    const result = await request('status', {}, 1200)
    runtime = normalizeRuntime(result, true)
  } catch (error) {
    runtime = emptyPlatformRuntime(false)
    if (error.code !== 'EXTENSION_UNAVAILABLE') throw error
  }
  listeners.forEach(listener => listener(runtime))
  return runtime
}

async function requireExtension(action, payload = {}, timeout = 30000) {
  const result = await request(action, payload, timeout)
  if (result?.runtime) {
    runtime = normalizeRuntime(result.runtime, true)
    listeners.forEach(listener => listener(runtime))
  }
  return result
}

async function startLogin(platform) {
  const current = await heartbeat()
  if (!current.available) {
    throw bridgeError('未检测到 MyJob 浏览器扩展，请先安装 browser_extension 目录中的扩展', 'EXTENSION_UNAVAILABLE')
  }
  if (current.platforms?.[platform]?.logged_in) {
    return { status: 'already_logged_in', already_logged_in: true, platform, runtime: current }
  }
  return requireExtension('login', { platform }, 15000)
}

export const platformBridge = {
  heartbeat,
  startLogin,
  logoutAll: () => requireExtension('logoutAll', {}, 30000),
  stopAll: () => requireExtension('stopAll', {}, 15000),
  search: payload => requireExtension('search', payload, 60000),
  apply: payload => requireExtension('apply', payload, 45000),
  getJobDetail: payload => requireExtension('getJobDetail', payload, 45000),
  syncConversations: payload => requireExtension('syncConversations', payload, 30000),
  syncMessages: payload => requireExtension('syncMessages', payload, 30000),
  sendMessage: payload => requireExtension('sendMessage', payload, 30000),
  getRuntime: () => runtime,
  platformLabel: id => platformById(id).label,
  subscribe(listener) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
}
