const cache = new Map()
const inflight = new Map()

function normalizeError(payload, response) {
  const message = payload?.detail || payload?.message || `请求失败 (${response.status})`
  const error = new Error(message)
  error.status = response.status
  error.payload = payload
  return error
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'include',
    headers: options.body instanceof FormData ? undefined : { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/api/auth/')) {
      window.dispatchEvent(new CustomEvent('myjob:unauthorized'))
    }
    throw normalizeError(payload, response)
  }
  return payload
}

export const api = {
  async get(path, { ttl = 0, force = false } = {}) {
    const now = Date.now()
    const cached = cache.get(path)
    if (!force && cached && cached.expiresAt > now) return cached.value
    if (!force && inflight.has(path)) return inflight.get(path)
    const promise = request(path).then(value => {
      if (ttl > 0) cache.set(path, { value, expiresAt: Date.now() + ttl })
      return value
    }).finally(() => inflight.delete(path))
    inflight.set(path, promise)
    return promise
  },
  post(path, body) {
    return request(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
  },
  put(path, body) {
    return request(path, { method: 'PUT', body: JSON.stringify(body) })
  },
  delete(path) {
    return request(path, { method: 'DELETE' })
  },
  invalidate(prefix = '') {
    for (const key of cache.keys()) if (!prefix || key.startsWith(prefix)) cache.delete(key)
  },
}

export function sleep(milliseconds) {
  return new Promise(resolve => window.setTimeout(resolve, milliseconds))
}

export function connectSocket(onMessage, onState = () => {}) {
  let socket
  let stopped = false
  let retryTimer
  let retryDelay = 1200

  const connect = () => {
    if (stopped || document.visibilityState === 'hidden') return
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    socket = new WebSocket(`${protocol}//${location.host}/ws`)
    onState('connecting')
    socket.onopen = () => {
      retryDelay = 1200
      onState('open')
    }
    socket.onmessage = event => {
      try { onMessage(JSON.parse(event.data)) } catch { /* Ignore malformed server events. */ }
    }
    socket.onclose = event => {
      onState('closed')
      if (event.code === 4401) {
        window.dispatchEvent(new CustomEvent('myjob:unauthorized'))
        return
      }
      if (!stopped) {
        retryTimer = window.setTimeout(connect, retryDelay)
        retryDelay = Math.min(retryDelay * 1.7, 15000)
      }
    }
  }

  const onVisibility = () => {
    if (document.visibilityState === 'visible' && (!socket || socket.readyState > WebSocket.OPEN)) connect()
  }
  document.addEventListener('visibilitychange', onVisibility)
  connect()

  return () => {
    stopped = true
    window.clearTimeout(retryTimer)
    document.removeEventListener('visibilitychange', onVisibility)
    socket?.close()
  }
}
