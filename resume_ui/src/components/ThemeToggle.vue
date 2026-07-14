<template>
  <button class="theme-toggle" type="button" :aria-label="theme === 'dark' ? '切换到日间模式' : '切换到夜间模式'" :title="theme === 'dark' ? '日间模式' : '夜间模式'" @click="$emit('toggle')">
    <Icon :icon="theme === 'dark' ? 'mdi:white-balance-sunny' : 'mdi:weather-night'" />
    <span v-if="showLabel">{{ theme === 'dark' ? '日间' : '夜间' }}</span>
  </button>
</template>

<script setup>
import { Icon } from '@iconify/vue'

defineProps({
  theme: { type: String, required: true },
  showLabel: Boolean,
})
defineEmits(['toggle'])
</script>
