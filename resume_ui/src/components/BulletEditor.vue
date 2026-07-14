<template>
  <div class="vre-bullet-editor">
    <div class="vre-bullet-editor-head">
      <span>{{ label }}</span>
      <div class="vre-bullet-editor-actions">
        <TextStyleControl :model-value="textStyle" :label="label" :default-font-size="defaultFontSize" :default-line-height="defaultLineHeight" @update:model-value="emit('update:textStyle', $event)" />
        <div class="vre-list-buttons" role="toolbar" :aria-label="`${label}分点格式`">
          <button type="button" title="无序分点" :aria-label="`${label}无序分点`" @mousedown.prevent @click="applyList('bullet')"><Icon icon="mdi:format-list-bulleted" /></button>
          <button type="button" title="有序分点" :aria-label="`${label}有序分点`" @mousedown.prevent @click="applyList('number')"><Icon icon="mdi:format-list-numbered" /></button>
        </div>
      </div>
    </div>
    <textarea ref="textarea" :value="modelValue" :rows="rows" :placeholder="placeholder" :aria-label="label" @input="emit('update:modelValue', $event.target.value)"></textarea>
  </div>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { Icon } from '@iconify/vue'
import TextStyleControl from './TextStyleControl.vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, required: true },
  placeholder: { type: String, default: '' },
  rows: { type: Number, default: 6 },
  textStyle: { type: Object, default: () => ({}) },
  defaultFontSize: { type: Number, default: 13 },
  defaultLineHeight: { type: Number, default: 1.55 },
})
const emit = defineEmits(['update:modelValue', 'update:textStyle'])
const textarea = ref(null)

const bulletPattern = /^(\s*)[-*•]\s*/
const numberPattern = /^(\s*)\d+[.)、]\s*/

function applyList(type) {
  const element = textarea.value
  if (!element) return
  const value = props.modelValue || ''
  const start = element.selectionStart ?? 0
  const end = element.selectionEnd ?? start
  const hasSelection = end > start
  const lineStart = hasSelection ? value.lastIndexOf('\n', Math.max(0, start - 1)) + 1 : 0
  const nextBreak = hasSelection ? value.indexOf('\n', end) : -1
  const lineEnd = hasSelection && nextBreak >= 0 ? nextBreak : value.length
  const selected = value.slice(lineStart, lineEnd)
  const lines = selected.split('\n')
  const targetPattern = type === 'number' ? numberPattern : bulletPattern
  const nonEmpty = lines.filter(line => line.trim())
  const shouldRemove = nonEmpty.length > 0 && nonEmpty.every(line => targetPattern.test(line))
  let order = 1
  const replacement = lines.map(line => {
    if (!line.trim()) return lines.length === 1 ? (type === 'number' ? '1. ' : '• ') : line
    const indent = line.match(/^\s*/)?.[0] || ''
    const content = line.replace(bulletPattern, '$1').replace(numberPattern, '$1').trimStart()
    if (shouldRemove) return `${indent}${content}`
    if (type === 'number') return `${indent}${order++}. ${content}`
    return `${indent}• ${content}`
  }).join('\n')
  const nextValue = value.slice(0, lineStart) + replacement + value.slice(lineEnd)
  emit('update:modelValue', nextValue)
  nextTick(() => {
    element.focus()
    element.setSelectionRange(lineStart, lineStart + replacement.length)
  })
}
</script>

<style scoped>
.vre-bullet-editor{display:grid;gap:5px}.vre-bullet-editor-head{display:flex;align-items:center;justify-content:space-between;gap:10px}.vre-bullet-editor-head>span{font-size:9.5px;color:#a8b2c0;font-weight:600}.vre-bullet-editor-actions{display:flex;align-items:center;gap:6px}.vre-list-buttons{display:flex;align-items:center;border:1px solid #30394a;border-radius:6px;overflow:hidden;background:#1b212b}.vre-list-buttons button{width:29px;height:25px;border:0;background:transparent;color:#9eabba;display:grid;place-items:center;cursor:pointer;font-size:16px}.vre-list-buttons button+button{border-left:1px solid #30394a}.vre-list-buttons button:hover{background:#273243;color:#6bd5f4}.vre-bullet-editor textarea{width:100%;resize:vertical;line-height:1.55}
</style>
