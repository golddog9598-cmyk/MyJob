const REQUEST_TYPE = 'MYJOB_PLATFORM_REQUEST'
const RESPONSE_TYPE = 'MYJOB_PLATFORM_RESPONSE'
const EVENT_TYPE = 'MYJOB_PLATFORM_EVENT'

window.addEventListener('message', event => {
  if (event.source !== window || event.data?.source !== 'myjob-web' || event.data.type !== REQUEST_TYPE) return
  const { id, action, payload } = event.data
  chrome.runtime.sendMessage({ type: REQUEST_TYPE, id, action, payload }).then(result => {
    window.postMessage({ source: 'myjob-extension', type: RESPONSE_TYPE, id, ok: true, result }, window.location.origin)
  }).catch(error => {
    window.postMessage({
      source: 'myjob-extension',
      type: RESPONSE_TYPE,
      id,
      ok: false,
      code: error?.code || 'PLATFORM_EXTENSION_ERROR',
      error: error?.message || '浏览器扩展操作失败',
    }, window.location.origin)
  })
})

chrome.runtime.onMessage.addListener(message => {
  if (message?.type !== EVENT_TYPE) return
  window.postMessage({ source: 'myjob-extension', type: EVENT_TYPE, runtime: message.runtime }, window.location.origin)
})
