import test from 'node:test'
import assert from 'node:assert/strict'

import {
  MAX_DAILY_APPLY_LIMIT,
  normalizeDailyApplyLimits,
  platformApplicationAllowance,
  totalDailyApplyLimit,
} from '../src/applicationLimits.js'

test('each platform limit is independently clamped to 1-50', () => {
  const limits = normalizeDailyApplyLimits({ boss: 80, zhilian: 0, liepin: 25, job51: '40' }, 15)
  assert.deepEqual(limits, { boss: 50, zhilian: 1, liepin: 25, job51: 40 })
  assert.equal(MAX_DAILY_APPLY_LIMIT, 50)
})

test('legacy global limit migrates to all four platforms', () => {
  assert.deepEqual(normalizeDailyApplyLimits(null, 30), {
    boss: 30,
    zhilian: 30,
    liepin: 30,
    job51: 30,
  })
})

test('allowance blocks only the platform that reached its own limit', () => {
  assert.deepEqual(platformApplicationAllowance(50, 50), { allowed: false, used: 50, limit: 50, remaining: 0 })
  assert.deepEqual(platformApplicationAllowance(12, 50), { allowed: true, used: 12, limit: 50, remaining: 38 })
})

test('aggregate limit is the sum of four platform limits', () => {
  assert.equal(totalDailyApplyLimit({ boss: 50, zhilian: 40, liepin: 30, job51: 20 }), 140)
})
