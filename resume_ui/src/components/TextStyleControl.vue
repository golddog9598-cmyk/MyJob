<template>
  <details ref="root" class="vre-text-style-control" @click.stop>
    <summary :aria-label="`${label}字号与行距`" :title="`${label}字号与行距`">
      <Icon icon="mdi:format-size" />
      <span>{{ displayFontSize }}px · {{ displayLineHeight }}</span>
    </summary>
    <div class="vre-text-style-popover">
      <label>
        <span>字号</span>
        <input type="range" min="8" max="40" step="0.5" :value="fontSize" :aria-label="`${label}字号`" @input="updateStyle('font_size', $event.target.value)" />
        <b>{{ displayFontSize }}px</b>
      </label>
      <label>
        <span>行距</span>
        <input type="range" min="1" max="2.4" step="0.01" :value="lineHeight" :aria-label="`${label}行距`" @input="updateStyle('line_height', $event.target.value)" />
        <b>{{ displayLineHeight }}</b>
      </label>
      <button v-if="hasCustomStyle" type="button" @click="emit('update:modelValue', {})">恢复模板默认</button>
    </div>
  </details>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Icon } from '@iconify/vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  label: { type: String, default: '当前字段' },
  defaultFontSize: { type: Number, default: 13 },
  defaultLineHeight: { type: Number, default: 1.55 },
})
const emit = defineEmits(['update:modelValue'])
const root = ref(null)

const fontSize = computed(() => Number(props.modelValue?.font_size || props.defaultFontSize))
const lineHeight = computed(() => Number(props.modelValue?.line_height || props.defaultLineHeight))
const displayFontSize = computed(() => Number(fontSize.value.toFixed(1)))
const displayLineHeight = computed(() => Number(lineHeight.value.toFixed(2)))
const hasCustomStyle = computed(() => Boolean(props.modelValue?.font_size || props.modelValue?.line_height))

function updateStyle(key, rawValue) {
  const value = Number(rawValue)
  emit('update:modelValue', {
    ...(props.modelValue || {}),
    [key]: value,
  })
}

function closeOnOutside(event) {
  if (!root.value?.open || root.value.contains(event.target)) return
  root.value.open = false
}

onMounted(() => document.addEventListener('click', closeOnOutside, true))
onBeforeUnmount(() => document.removeEventListener('click', closeOnOutside, true))
</script>

<style scoped>
.vre-text-style-control{position:relative;flex:0 0 auto}.vre-text-style-control summary{list-style:none;height:25px;padding:0 7px;border:1px solid #364154;border-radius:6px;background:#202733;color:#9eabba;display:inline-flex;align-items:center;gap:4px;cursor:pointer;font-size:8.5px;line-height:1}.vre-text-style-control summary::-webkit-details-marker{display:none}.vre-text-style-control summary:hover,.vre-text-style-control[open] summary{border-color:#258eb9;color:#78d9f7;background:#183343}.vre-text-style-control summary svg{font-size:14px}.vre-text-style-popover{position:absolute;z-index:30;right:0;top:30px;width:224px;padding:10px;border:1px solid #39465a;border-radius:9px;background:#171d26;box-shadow:0 13px 30px rgba(0,0,0,.38);display:grid;gap:9px}.vre-text-style-popover label{display:grid;grid-template-columns:30px minmax(0,1fr) 40px;align-items:center;gap:7px;color:#aeb8c6;font-size:9px}.vre-text-style-popover input{width:100%;accent-color:#22b8e6}.vre-text-style-popover b{text-align:right;color:#e7ebf1;font-size:9px}.vre-text-style-popover button{justify-self:end;border:0;background:transparent;color:#77cce9;font-size:8.5px;cursor:pointer;padding:2px 0}
</style>
