const CONTENT_ADAPTER_VERSION = '0.0.12'

function platformId() {
  const host = location.hostname.toLowerCase()
  if (host === 'zhipin.com' || host.endsWith('.zhipin.com')) return 'boss'
  if (host === 'zhaopin.com' || host.endsWith('.zhaopin.com')) return 'zhilian'
  if (host === 'liepin.com' || host.endsWith('.liepin.com')) return 'liepin'
  if (host === '51job.com' || host.endsWith('.51job.com')) return 'job51'
  return ''
}

function visible(element) {
  if (!element) return false
  const style = getComputedStyle(element)
  const rect = element.getBoundingClientRect()
  return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0
}

function hasVisible(selectors) {
  return selectors.some(selector => Array.from(document.querySelectorAll(selector)).some(visible))
}

function bodyText() {
  return (document.body?.innerText || '').slice(0, 12000)
}

function safetyIssue() {
  const text = bodyText().toLowerCase()
  if (/(验证码|滑块|拼图|captcha|verify|安全验证)/i.test(text.slice(0, 3000))) return '检测到验证码或安全验证，请在平台页面人工处理'
  if (/(账号异常|违规|限制使用|冻结|操作太频繁|稍后再试)/i.test(text.slice(0, 3000))) return '检测到平台风控提示，请停止自动操作并人工处理'
  return ''
}

const LOGIN_RULES = {
  boss: {
    negative: ['input[placeholder*="手机号"]', 'input[placeholder*="验证码"]', 'input[type="password"]', '.qrcode-img', '[class*="login-panel"]', '[class*="login-modal"]'],
    positive: ['[class*="user-avatar"]', '[class*="nav-user"]', '[class*="geek-avatar"]', 'a[href*="/web/geek/resume"]', 'a[href*="/web/geek/chat"]'],
    paths: ['/web/geek/'],
  },
  zhilian: {
    negative: ['input[type="password"]', '[class*="login"] input[placeholder*="手机"]', '[class*="qrcode"]'],
    positive: ['[class*="user-name"]', '[class*="user-info"]', 'a[href*="resume"]', 'a[href*="personal"]'],
    paths: ['/resume/', '/personal/'],
  },
  liepin: {
    negative: ['input[type="password"]', '[class*="login"] input', '[class*="qrcode"]'],
    positive: ['[class*="user-name"]', '[class*="avatar"]', 'a[href*="resume"]', 'a[href*="message"]'],
    paths: ['/resume/', '/message/'],
  },
  job51: {
    negative: ['input[type="password"]', 'input[name="loginname"]', '[class*="login"] input'],
    positive: ['[class*="user-name"]', '[class*="username"]', 'a[href*="resume"]', 'a[href*="account"]'],
    paths: ['/resume/', '/account/', '/pc/my/'],
  },
}

function loggedIn() {
  const platform = platformId()
  const rules = LOGIN_RULES[platform]
  if (!rules || hasVisible(rules.negative)) return false
  const text = bodyText()
  if (/(请登录|扫码登录|密码登录|验证码登录)/.test(text.slice(0, 4000))) return false
  return hasVisible(rules.positive) || rules.paths.some(path => location.pathname.startsWith(path))
}

function pick(root, selectors) {
  for (const selector of selectors) {
    const element = root.querySelector(selector)
    const value = (element?.getAttribute('title') || element?.innerText || '').trim()
    if (value) return value
  }
  return ''
}

function decodeBossText(value) {
  return Array.from(value || '', character => {
    const code = character.charCodeAt(0)
    return code >= 0xE031 && code <= 0xE03A ? String(code - 0xE031) : character
  }).join('')
}

function extractBoss(limit) {
  const jobs = []
  const seen = new Set()
  const anchors = document.querySelectorAll('a[href*="/job_detail/"]')

  for (const anchor of anchors) {
    if (jobs.length >= limit) break
    const jobUrl = anchor.href || anchor.getAttribute('href') || ''
    if (!/\/job_detail\/[^/?#]+/.test(jobUrl) || seen.has(jobUrl)) continue

    const card = anchor.closest('li.job-card-wrapper, .job-card-box, [class*="job-card-wrapper"], .job-card-body, .job-primary, .job-list-box, .search-job-result')
    if (!card) continue
    const labels = (card.innerText || '').split('\n').map(value => decodeBossText(value.trim())).filter(Boolean)
    const jobTitle = pick(card, [
      '.job-name',
      '.job-title',
      '.job-card-left .job-name',
      '[class*="job-name"]',
      '[class*="job-title"]',
    ]) || (anchor.getAttribute('title') || anchor.innerText || '').trim().split('\n')[0] || labels[0] || ''

    if (!jobTitle) continue
    seen.add(jobUrl)
    const salary = decodeBossText(pick(card, ['.salary', '.red', '[class*="salary"]']))
      || labels.find(value => /\d+\s*[-~]\s*\d+\s*K|\d+\s*K以上|面议/i.test(value))
      || ''
    jobs.push({
      job_title: jobTitle.replace(/\s+/g, ' ').trim(),
      salary,
      company: pick(card, ['.company-name', '.brand-name', '.company-text', '[class*="company-name"]', '[class*="brand-name"]']),
      city: pick(card, ['.job-area', '[class*="job-area"]']) || labels.find(value => value.includes('·') && value.length < 40) || '',
      experience: labels.find(value => /经验|应届|在校|不限/.test(value) && value.length < 30) || '',
      education: labels.find(value => /本科|硕士|博士|大专|学历不限|中专|高中/.test(value) && value.length < 30) || '',
      job_url: jobUrl,
    })
  }

  return jobs
}

function extractZhilian(limit) {
  return Array.from(document.querySelectorAll('div.joblist-box__item, [class*="joblist-box__item"]')).slice(0, limit).map(card => {
    const anchor = card.querySelector('a[href*="jobdetail"], a[href*="jobs.zhaopin.com"]')
    const labels = (card.innerText || '').split('\n').map(value => value.trim()).filter(Boolean)
    return {
      job_title: pick(card, ['[class*="jobinfo__name"]', '[class*="job-name"]', 'a']),
      salary: pick(card, ['[class*="jobinfo__salary"]', '[class*="salary"]']),
      company: pick(card, ['[class*="companyinfo__name"]', '[class*="company-name"]']),
      city: pick(card, ['[class*="jobinfo__other"]', '[class*="area"]']),
      experience: labels.find(value => /年|应届|经验/.test(value)) || '',
      education: labels.find(value => /本科|硕士|博士|大专|学历/.test(value)) || '',
      job_url: anchor?.href || '',
    }
  }).filter(item => item.job_url && item.job_title)
}

function extractLiepin(limit) {
  return Array.from(document.querySelectorAll('div[class*="job-card-pc-container"], [class*="job-card"]')).slice(0, limit).map(card => {
    const anchor = card.querySelector('a[href*="job"]')
    const labels = (card.innerText || '').split('\n').map(value => value.trim()).filter(Boolean)
    return {
      job_title: pick(card, ['[class*="job-title"]', '[class*="job-name"]']),
      salary: pick(card, ['[class*="job-salary"]', '[class*="salary"]']),
      company: pick(card, ['[class*="company-name"]', '[class*="company-title"]']),
      city: pick(card, ['[class*="job-dq"]', '[class*="job-area"]', '[class*="area"]']),
      experience: labels.find(value => /年|应届|经验/.test(value)) || '',
      education: labels.find(value => /本科|硕士|博士|大专|学历/.test(value)) || '',
      job_url: anchor?.href || '',
    }
  }).filter(item => item.job_url && item.job_title)
}

function extractJob51(limit) {
  const seen = new Set()
  const result = []
  for (const anchor of document.querySelectorAll('a.jname[href], a[href*="/pc/jobdetail"], a[href*="jobs.51job.com"]')) {
    if (result.length >= limit) break
    const url = anchor.href || ''
    if (!url || seen.has(url)) continue
    seen.add(url)
    const card = anchor.closest('.joblist-item, .e, [class*="joblist-item"]') || anchor.parentElement?.parentElement || anchor
    const labels = (card.innerText || '').split('\n').map(value => value.trim()).filter(Boolean)
    result.push({
      job_title: (anchor.getAttribute('title') || anchor.innerText || '').trim(),
      salary: pick(card, ['.sal', '[class*="salary"]']),
      company: pick(card, ['a.cname', '.cname', '[class*="company"]']),
      city: pick(card, ['.d', '[class*="area"]', '[class*="location"]']),
      experience: labels.find(value => /年经验|应届|无需经验/.test(value)) || '',
      education: labels.find(value => /本科|硕士|博士|大专|学历/.test(value)) || '',
      job_url: url,
    })
  }
  return result
}

function extractJobs(limit = 60) {
  const issue = safetyIssue()
  if (issue) throw new Error(issue)
  if (!loggedIn()) throw new Error('当前平台登录状态已失效')
  const platform = platformId()
  const methods = { boss: extractBoss, zhilian: extractZhilian, liepin: extractLiepin, job51: extractJob51 }
  return methods[platform]?.(limit) || []
}

const DETAIL_SELECTORS = {
  boss: ['.job-sec-text', '.job-detail-section .text', '.job-detail-section', '.job-detail'],
  zhilian: ['.describtion__detail-content', '.job-detail-content', '[class*="job-detail-content"]', '.job-detail'],
  liepin: ['.job-intro-container', '[class*="job-intro"]', '.job-detail-box', '.job-detail'],
  job51: ['.job_msg', '[class*="job-detail"]', '.jobdetail'],
}

function extractJobDetail() {
  const issue = safetyIssue()
  if (issue) throw new Error(issue)
  if (!loggedIn()) throw new Error('当前平台登录状态已失效')
  const platform = platformId()
  const containers = (DETAIL_SELECTORS[platform] || [])
    .flatMap(selector => Array.from(document.querySelectorAll(selector)))
    .filter(visible)
  const description = containers
    .map(element => (element.innerText || '').trim())
    .filter(text => text.length >= 30)
    .sort((left, right) => right.length - left.length)[0]
  if (!description) throw new Error('未读取到完整岗位 JD，请确认当前页面为岗位详情页')
  return {
    job: {
      job_title: pick(document, ['h1', '.job-name', '[class*="job-title"]']),
      company: pick(document, ['.company-name', '[class*="company-name"]', '[class*="company-title"]']),
      description: description.slice(0, 24000),
      job_url: location.href,
    },
  }
}

const APPLY_TEXT = ['立即沟通', '继续沟通', '聊一聊', '立即申请', '申请职位', '投递简历', '应聘']

function applyCurrentJob() {
  const issue = safetyIssue()
  if (issue) throw new Error(issue)
  if (!loggedIn()) throw new Error('当前平台登录状态已失效')
  const candidates = Array.from(document.querySelectorAll('button, a, [role="button"]')).filter(visible)
  const button = candidates.find(element => APPLY_TEXT.some(text => (element.innerText || '').trim().includes(text)))
  if (!button) throw new Error('未找到可用的投递或沟通按钮，平台页面结构可能已更新')
  button.click()
  return { success: true, message: '已在平台页面执行投递操作，请核对页面结果' }
}

function syncConversations() {
  const issue = safetyIssue()
  if (issue) throw new Error(issue)
  const platform = platformId()
  const selectors = ['li[role="listitem"]', '.friend-content', '[class*="conversation-item"]', '[class*="chat-item"]']
  const items = Array.from(document.querySelectorAll(selectors.join(','))).filter(visible).slice(0, 100)
  const conversations = items.map((item, index) => {
    const lines = (item.innerText || '').split('\n').map(value => value.trim()).filter(Boolean)
    return {
      id: `${platform}:conversation:${index}:${lines[0] || ''}`,
      hr_name: lines[0] || '招聘者',
      hr_company: lines[1] || '',
      job_title: lines[2] || '',
      last_message_text: lines.at(-1) || '',
      unread_count: Number((item.querySelector('[class*="unread"], [class*="badge"]')?.textContent || '').replace(/\D/g, '') || 0),
    }
  })
  return { conversations, exchanges: [] }
}

function syncMessages() {
  const selectors = ['li.message-item', 'li[class*="message-item"]', '[class*="message-item"]', '[class*="message-content"]']
  const messages = Array.from(document.querySelectorAll(selectors.join(','))).filter(visible).slice(-100).map((item, index) => ({
    id: `${platformId()}:message:${index}:${(item.innerText || '').slice(0, 24)}`,
    sender: /self|mine|right|my-/i.test(item.className) ? 'me' : 'hr',
    content: (item.innerText || '').trim(),
    platform_time: new Date().toISOString(),
  })).filter(item => item.content)
  return { messages }
}

function sendMessage(payload) {
  const issue = safetyIssue()
  if (issue) throw new Error(issue)
  const inputSelectors = ['#chat-input', 'div[contenteditable="true"]', 'textarea[placeholder*="请输入"]', 'textarea', '[contenteditable="true"]']
  const input = inputSelectors.map(selector => document.querySelector(selector)).find(visible)
  if (!input) throw new Error('未找到消息输入框，请先在平台页面打开对应会话')
  input.focus()
  if (input.matches('[contenteditable="true"]')) {
    input.textContent = payload.content
    input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: payload.content }))
  } else {
    input.value = payload.content
    input.dispatchEvent(new Event('input', { bubbles: true }))
  }
  const buttons = Array.from(document.querySelectorAll('button, [role="button"]')).filter(visible)
  const send = buttons.find(button => /发送/.test(button.innerText || ''))
  if (!send) throw new Error('未找到发送按钮')
  send.click()
  return { success: true }
}

chrome.runtime.onMessage.addListener(message => {
  if (message?.source !== 'myjob-extension') return undefined
  if (message.action === 'probe') return Promise.resolve({ platform: platformId(), logged_in: loggedIn(), url: location.href, adapter_version: CONTENT_ADAPTER_VERSION })
  if (message.action === 'extractJobs') return Promise.resolve({ jobs: extractJobs(message.payload?.limit || 60), adapter_version: CONTENT_ADAPTER_VERSION })
  if (message.action === 'extractJobDetail') return Promise.resolve(extractJobDetail())
  if (message.action === 'apply') return Promise.resolve(applyCurrentJob())
  if (message.action === 'syncConversations') return Promise.resolve(syncConversations())
  if (message.action === 'syncMessages') return Promise.resolve(syncMessages())
  if (message.action === 'sendMessage') return Promise.resolve(sendMessage(message.payload || {}))
  return undefined
})
