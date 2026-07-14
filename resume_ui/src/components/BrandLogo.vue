<template>
  <span class="myjob-brand" :class="{ compact }">
    <span class="myjob-brand-image"><img v-if="!imageFailed" :src="logoUrl" alt="" @error="imageFailed = true" /><span v-else aria-hidden="true">M</span></span>
    <span v-if="!compact" class="myjob-wordmark">MyJob</span>
  </span>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ compact: Boolean })
const imageFailed = ref(false)
const logoUrl = '/static/brand/myjob-logo.png'
</script>
