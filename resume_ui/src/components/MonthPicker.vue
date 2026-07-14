<template>
  <div class="vre-month-picker">
    <select :value="year" :aria-label="`${ariaLabel}年份`" @change="setYear($event.target.value)">
      <option value="">年份</option>
      <option v-if="allowPresent" value="present">至今</option>
      <option v-for="item in availableYears" :key="item" :value="String(item)">{{ item }} 年</option>
    </select>
    <select :value="month" :aria-label="`${ariaLabel}月份`" :disabled="!year || year === 'present'" @change="setMonth($event.target.value)">
      <option value="">月份</option>
      <option v-for="item in months" :key="item" :value="item" :disabled="isMonthDisabled(item)">{{ item }} 月</option>
    </select>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  allowPresent: { type: Boolean, default: false },
  ariaLabel: { type: String, default: '时间' },
  minValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const currentYear = new Date().getFullYear()
const years = Array.from({ length: currentYear - 1969 + 1 }, (_, index) => currentYear + 1 - index)
const months = Array.from({ length: 12 }, (_, index) => String(index + 1).padStart(2, '0'))
const year = ref('')
const month = ref('')
const minParts = computed(() => {
  const match = String(props.minValue || '').match(/^(\d{4})[.\-/年](\d{1,2})/)
  return match ? { year: Number(match[1]), month: Number(match[2]) } : null
})
const availableYears = computed(() => years.filter(item => !minParts.value || item >= minParts.value.year))

watch(() => props.modelValue, value => {
  const normalized = String(value || '').trim()
  if (props.allowPresent && /^(至今|现在|present)$/i.test(normalized)) {
    year.value = 'present'
    month.value = ''
    return
  }
  const match = normalized.match(/^(\d{4})[.\-/年](\d{1,2})/)
  year.value = match?.[1] || ''
  month.value = match ? String(Number(match[2])).padStart(2, '0') : ''
}, { immediate: true })

function publish() {
  if (year.value === 'present') emit('update:modelValue', '至今')
  else emit('update:modelValue', year.value && month.value ? `${year.value}.${month.value}` : '')
}

function setYear(value) {
  year.value = value
  if (value === 'present' || !value) month.value = ''
  else if (!month.value) month.value = String(minParts.value?.year === Number(value) ? minParts.value.month : 1).padStart(2, '0')
  else if (minParts.value?.year === Number(value) && Number(month.value) < minParts.value.month) month.value = String(minParts.value.month).padStart(2, '0')
  publish()
}

function setMonth(value) {
  month.value = value
  publish()
}

function isMonthDisabled(value) {
  return Boolean(minParts.value && Number(year.value) === minParts.value.year && Number(value) < minParts.value.month)
}
</script>

<style scoped>
.vre-month-picker{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:7px}.vre-month-picker select{height:38px!important;box-sizing:border-box;padding:0 9px!important;line-height:normal!important}.vre-month-picker select:disabled{opacity:.45;cursor:not-allowed}
</style>
