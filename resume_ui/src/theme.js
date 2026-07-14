const THEME_KEY = 'myjob-ui-theme'
const THEME_COLORS = Object.freeze({
  light: '#f2f6f7',
  dark: '#0f151b',
})

export function preferredTheme() {
  const saved = localStorage.getItem(THEME_KEY)
  if (saved === 'light' || saved === 'dark') return saved
  return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function applyTheme(theme) {
  const normalized = theme === 'light' ? 'light' : 'dark'
  document.documentElement.dataset.theme = normalized
  document.documentElement.style.colorScheme = normalized
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLORS[normalized])
  localStorage.setItem(THEME_KEY, normalized)
  return normalized
}
