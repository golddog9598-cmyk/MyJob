import { PLATFORM_IDS } from './platformCatalog.js'

export const MAX_DAILY_APPLY_LIMIT = 50
export const DEFAULT_DAILY_APPLY_LIMIT = 50

function clampLimit(value, fallback = DEFAULT_DAILY_APPLY_LIMIT) {
  const parsed = Number(value)
  const safe = Number.isFinite(parsed) ? Math.trunc(parsed) : Number(fallback)
  return Math.min(MAX_DAILY_APPLY_LIMIT, Math.max(1, safe))
}

export function normalizeDailyApplyLimits(value, legacyLimit = DEFAULT_DAILY_APPLY_LIMIT) {
  const source = value && typeof value === 'object' ? value : {}
  return Object.fromEntries(PLATFORM_IDS.map(platform => [
    platform,
    clampLimit(source[platform], legacyLimit),
  ]))
}

export function platformApplicationAllowance(used, limit) {
  const normalizedUsed = Math.max(0, Math.trunc(Number(used) || 0))
  const normalizedLimit = clampLimit(limit)
  const remaining = Math.max(0, normalizedLimit - normalizedUsed)
  return { allowed: remaining > 0, used: normalizedUsed, limit: normalizedLimit, remaining }
}

export function totalDailyApplyLimit(limits) {
  const normalized = normalizeDailyApplyLimits(limits)
  return PLATFORM_IDS.reduce((total, platform) => total + normalized[platform], 0)
}
