const REQUEST_TYPE = 'MYJOB_PLATFORM_REQUEST'
const EVENT_TYPE = 'MYJOB_PLATFORM_EVENT'

const PLATFORMS = {
  boss: {
    label: 'BOSS 直聘',
    loginUrl: 'https://www.zhipin.com/web/user/',
    patterns: ['*://*.zhipin.com/*'],
    origins: ['https://www.zhipin.com', 'https://m.zhipin.com', 'https://api.zhipin.com'],
  },
  zhilian: {
    label: '智联招聘',
    loginUrl: 'https://passport.zhaopin.com/login',
    patterns: ['*://*.zhaopin.com/*'],
    origins: ['https://www.zhaopin.com', 'https://sou.zhaopin.com', 'https://passport.zhaopin.com'],
  },
  liepin: {
    label: '猎聘',
    loginUrl: 'https://passport.liepin.com/account/v1/login',
    patterns: ['*://*.liepin.com/*'],
    origins: ['https://www.liepin.com', 'https://passport.liepin.com'],
  },
  job51: {
    label: '前程无忧',
    loginUrl: 'https://login.51job.com/login.php',
    patterns: ['*://*.51job.com/*'],
    origins: ['https://www.51job.com', 'https://we.51job.com', 'https://login.51job.com'],
  },
}

const CITY_CODES = {
  全国: '100010000', 北京: '101010100', 上海: '101020100', 广州: '101280100', 深圳: '101280600',
  杭州: '101210100', 南京: '101190100', 成都: '101270100', 武汉: '101200100', 西安: '101110100',
  苏州: '101190400', 天津: '101030100', 重庆: '101040100', 青岛: '101120200', 济南: '101120100',
}

function platformFromUrl(url = '') {
  try {
    const hostname = new URL(url).hostname.toLowerCase()
    if (hostname === 'zhipin.com' || hostname.endsWith('.zhipin.com')) return 'boss'
    if (hostname === 'zhaopin.com' || hostname.endsWith('.zhaopin.com')) return 'zhilian'
    if (hostname === 'liepin.com' || hostname.endsWith('.liepin.com')) return 'liepin'
    if (hostname === '51job.com' || hostname.endsWith('.51job.com')) return 'job51'
  } catch {}
  return ''
}

async function allPlatformTabs() {
  const tabs = await chrome.tabs.query({})
  return tabs.filter(tab => platformFromUrl(tab.url))
}

async function sendToTab(tabId, action, payload = {}, timeout = 12000) {
  return Promise.race([
    chrome.tabs.sendMessage(tabId, { source: 'myjob-extension', action, payload }),
    new Promise((_, reject) => setTimeout(() => reject(new Error('招聘平台页面响应超时')), timeout)),
  ])
}

async function waitForTab(tabId, timeout = 30000) {
  const current = await chrome.tabs.get(tabId).catch(() => null)
  if (current?.status === 'complete') return current
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener)
      reject(new Error('招聘平台页面加载超时'))
    }, timeout)
    const listener = (updatedId, change, tab) => {
      if (updatedId !== tabId || change.status !== 'complete') return
      clearTimeout(timer)
      chrome.tabs.onUpdated.removeListener(listener)
      resolve(tab)
    }
    chrome.tabs.onUpdated.addListener(listener)
  })
}

async function runtimeStatus() {
  const tabs = await allPlatformTabs()
  const states = {}
  for (const [id, spec] of Object.entries(PLATFORMS)) {
    const matches = tabs.filter(tab => platformFromUrl(tab.url) === id)
    let loggedIn = false
    for (const tab of matches) {
      try {
        const result = await sendToTab(tab.id, 'probe', {}, 3000)
        if (result?.logged_in) loggedIn = true
      } catch {}
    }
    states[id] = { label: spec.label, page_open: matches.length > 0, logged_in: loggedIn }
  }
  const active = tabs.find(tab => tab.active)
  return {
    available: true,
    browser_running: tabs.length > 0,
    active_platform: platformFromUrl(active?.url) || 'boss',
    platforms: states,
  }
}

async function publishRuntime() {
  const runtime = await runtimeStatus()
  const pages = await chrome.tabs.query({})
  const clients = pages.filter(tab => /^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(tab.url || ''))
  await Promise.all(clients.map(tab => chrome.tabs.sendMessage(tab.id, { type: EVENT_TYPE, runtime }).catch(() => null)))
  return runtime
}

async function focusTab(tab) {
  if (!tab) return
  if (tab.windowId != null) await chrome.windows.update(tab.windowId, { focused: true }).catch(() => null)
  if (tab.id != null) await chrome.tabs.update(tab.id, { active: true }).catch(() => null)
}

async function login(platform) {
  const spec = PLATFORMS[platform]
  if (!spec) throw new Error('不支持的招聘平台')
  const current = await runtimeStatus()
  if (current.platforms[platform]?.logged_in) {
    return { status: 'already_logged_in', already_logged_in: true, platform, runtime: current }
  }
  const tabs = (await allPlatformTabs()).filter(tab => platformFromUrl(tab.url) === platform)
  let tab = tabs[0]
  if (tab) {
    tab = await chrome.tabs.update(tab.id, { url: spec.loginUrl, active: true })
    await focusTab(tab)
  } else {
    const window = await chrome.windows.create({ url: spec.loginUrl, focused: true, type: 'normal' })
    tab = window.tabs?.[0]
  }
  if (tab?.id != null) await waitForTab(tab.id, 30000).catch(() => null)
  const runtime = await publishRuntime()
  return { status: 'login_opened', platform, runtime }
}

async function logoutAll() {
  const origins = [...new Set(Object.values(PLATFORMS).flatMap(item => item.origins))]
  await chrome.browsingData.remove({ origins }, {
    cookies: true,
    localStorage: true,
    indexedDB: true,
    cacheStorage: true,
    serviceWorkers: true,
  })
  const tabs = await allPlatformTabs()
  await Promise.all(tabs.map(tab => chrome.tabs.update(tab.id, { url: PLATFORMS[platformFromUrl(tab.url)].loginUrl }).catch(() => null)))
  await Promise.all(tabs.map(tab => waitForTab(tab.id, 20000).catch(() => null)))
  const runtime = await publishRuntime()
  return { status: 'logged_out_all', runtime }
}

async function stopAll() {
  const tabs = await allPlatformTabs()
  const ids = tabs.map(tab => tab.id).filter(id => id != null)
  if (ids.length) await chrome.tabs.remove(ids)
  const runtime = await publishRuntime()
  return { status: 'stopped_all', closed: ids.length, runtime }
}

function searchUrl(platform, payload) {
  const keyword = encodeURIComponent(payload.keyword || '')
  const city = encodeURIComponent(payload.city || '全国')
  if (platform === 'boss') {
    const cityCode = CITY_CODES[payload.city] || CITY_CODES['全国']
    return `https://www.zhipin.com/web/geek/job?query=${keyword}&city=${cityCode}`
  }
  if (platform === 'zhilian') return `https://sou.zhaopin.com/?jl=${city}&kw=${keyword}`
  if (platform === 'liepin') return `https://www.liepin.com/zhaopin/?key=${keyword}&dq=${city}`
  return `https://we.51job.com/pc/search?keyword=${keyword}&jobArea=${city}`
}

async function requireLoggedIn(platform) {
  const runtime = await runtimeStatus()
  if (!runtime.platforms[platform]?.logged_in) throw new Error(`请先登录${PLATFORMS[platform].label}`)
  return runtime
}

async function platformTab(platform) {
  const tabs = (await allPlatformTabs()).filter(tab => platformFromUrl(tab.url) === platform)
  return tabs.find(tab => tab.active) || tabs[0] || null
}

async function search(payload) {
  const platform = payload.platform || 'boss'
  await requireLoggedIn(platform)
  let tab = await platformTab(platform)
  const url = searchUrl(platform, payload)
  if (!tab) throw new Error('招聘平台窗口未打开')
  tab = await chrome.tabs.update(tab.id, { url, active: true })
  await focusTab(tab)
  await waitForTab(tab.id, 40000)
  const result = await sendToTab(tab.id, 'extractJobs', { limit: payload.limit || 60 }, 20000)
  return { platform, jobs: result?.jobs || [], jobs_found: result?.jobs?.length || 0, runtime: await runtimeStatus() }
}

async function apply(payload) {
  const platform = payload.platform || 'boss'
  await requireLoggedIn(platform)
  let tab = await platformTab(platform)
  if (!tab) throw new Error('招聘平台窗口未打开')
  if (payload.job_url && tab.url !== payload.job_url) {
    tab = await chrome.tabs.update(tab.id, { url: payload.job_url, active: true })
    await waitForTab(tab.id, 40000)
  }
  await focusTab(tab)
  const result = await sendToTab(tab.id, 'apply', {}, 20000)
  return { ...result, platform, runtime: await runtimeStatus() }
}

async function getJobDetail(payload) {
  const platform = payload.platform || 'boss'
  await requireLoggedIn(platform)
  let tab = await platformTab(platform)
  if (!tab) throw new Error('招聘平台窗口未打开')
  if (payload.job_url && tab.url !== payload.job_url) {
    tab = await chrome.tabs.update(tab.id, { url: payload.job_url, active: true })
    await waitForTab(tab.id, 40000)
  }
  await focusTab(tab)
  const result = await sendToTab(tab.id, 'extractJobDetail', {}, 20000)
  return { ...result, platform, runtime: await runtimeStatus() }
}

async function syncConversations(payload) {
  const platform = payload.platform || 'boss'
  await requireLoggedIn(platform)
  const tab = await platformTab(platform)
  if (!tab) throw new Error('招聘平台窗口未打开')
  const result = await sendToTab(tab.id, 'syncConversations', {}, 15000)
  return { ...result, platform, runtime: await runtimeStatus() }
}

async function syncMessages(payload) {
  const platform = payload.platform || 'boss'
  await requireLoggedIn(platform)
  const tab = await platformTab(platform)
  if (!tab) throw new Error('招聘平台窗口未打开')
  const result = await sendToTab(tab.id, 'syncMessages', payload, 15000)
  return { ...result, platform, runtime: await runtimeStatus() }
}

async function sendMessage(payload) {
  const platform = payload.platform || 'boss'
  await requireLoggedIn(platform)
  const tab = await platformTab(platform)
  if (!tab) throw new Error('招聘平台窗口未打开')
  const result = await sendToTab(tab.id, 'sendMessage', payload, 15000)
  return { ...result, platform, runtime: await runtimeStatus() }
}

const handlers = { status: runtimeStatus, login: payload => login(payload.platform), logoutAll, stopAll, search, apply, getJobDetail, syncConversations, syncMessages, sendMessage }

chrome.runtime.onMessage.addListener((message, sender) => {
  if (message?.type !== REQUEST_TYPE || !handlers[message.action]) return undefined
  return handlers[message.action](message.payload || {})
})

let publishTimer
function schedulePublish() {
  clearTimeout(publishTimer)
  publishTimer = setTimeout(() => publishRuntime().catch(() => null), 500)
}

chrome.tabs.onRemoved.addListener(schedulePublish)
chrome.tabs.onUpdated.addListener((tabId, change, tab) => {
  if (platformFromUrl(tab.url) && (change.status === 'complete' || change.url)) schedulePublish()
})
