export const PLATFORMS = Object.freeze([
  {
    id: 'boss',
    label: 'BOSS 直聘',
    shortLabel: 'BOSS',
    loginUrl: 'https://www.zhipin.com/web/user/',
  },
  {
    id: 'zhilian',
    label: '智联招聘',
    shortLabel: '智联',
    loginUrl: 'https://passport.zhaopin.com/login',
  },
  {
    id: 'liepin',
    label: '猎聘',
    shortLabel: '猎聘',
    loginUrl: 'https://passport.liepin.com/account/v1/login',
  },
  {
    id: 'job51',
    label: '前程无忧',
    shortLabel: '前程无忧',
    loginUrl: 'https://login.51job.com/login.php',
  },
])

export const PLATFORM_IDS = Object.freeze(PLATFORMS.map(item => item.id))

export function platformById(id) {
  return PLATFORMS.find(item => item.id === id) || PLATFORMS[0]
}

export function emptyPlatformRuntime(available = false) {
  return {
    available,
    browser_running: false,
    active_platform: 'boss',
    platforms: Object.fromEntries(PLATFORMS.map(item => [item.id, {
      label: item.label,
      page_open: false,
      logged_in: false,
    }])),
  }
}
