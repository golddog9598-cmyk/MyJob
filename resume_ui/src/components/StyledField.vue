<template>
  <div class="vre-styled-field">
    <div class="vre-styled-field-head">
      <span>{{ label }}</span>
      <TextStyleControl
        :model-value="modelValue"
        :label="label"
        :default-font-size="defaultFontSize"
        :default-line-height="defaultLineHeight"
        @update:model-value="emit('update:modelValue', $event)"
      />
    </div>
    <slot />
  </div>
</template>

<script setup>
import TextStyleControl from './TextStyleControl.vue'

defineProps({
  modelValue: { type: Object, default: () => ({}) },
  label: { type: String, required: true },
  defaultFontSize: { type: Number, default: 13 },
  defaultLineHeight: { type: Number, default: 1.55 },
})
const emit = defineEmits(['update:modelValue'])
</script>

<style scoped>
.vre-styled-field{display:grid;gap:5px;min-width:0}.vre-styled-field-head{display:flex;align-items:center;justify-content:space-between;gap:8px}.vre-styled-field-head>span{font-size:9.5px;color:#a8b2c0;font-weight:600}
</style>
