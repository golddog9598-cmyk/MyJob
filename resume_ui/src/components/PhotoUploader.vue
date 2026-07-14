<template>
  <div class="vre-photo-uploader">
    <div class="vre-photo-preview">
      <img v-if="modelValue" :src="modelValue" alt="简历照片预览" />
      <div v-else><Icon icon="mdi:account" /><span>照片</span></div>
    </div>
    <div class="vre-photo-copy">
      <strong>个人照片</strong>
      <p>建议上传正面职业照，系统会自动压缩并适配模板照片框。</p>
      <div>
        <input ref="input" type="file" accept="image/jpeg,image/png,image/webp" @change="handleFile" />
        <button type="button" class="vre-photo-button" @click="input?.click()"><Icon icon="mdi:camera-plus-outline" />{{ modelValue ? '更换照片' : '上传照片' }}</button>
        <button v-if="modelValue" type="button" class="vre-photo-remove" @click="emit('update:modelValue', '')">删除</button>
      </div>
      <span v-if="error" class="vre-photo-error">{{ error }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Icon } from '@iconify/vue'

defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])
const input = ref(null)
const error = ref('')

function readImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('照片读取失败'))
    reader.onload = () => {
      const image = new Image()
      image.onerror = () => reject(new Error('无法识别该图片'))
      image.onload = () => resolve(image)
      image.src = reader.result
    }
    reader.readAsDataURL(file)
  })
}

async function handleFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  error.value = ''
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    error.value = '仅支持 JPG、PNG 或 WebP 照片'
    return
  }
  if (file.size > 8 * 1024 * 1024) {
    error.value = '照片不能超过 8MB'
    return
  }
  try {
    const image = await readImage(file)
    const maxSide = 900
    const scale = Math.min(1, maxSide / Math.max(image.naturalWidth, image.naturalHeight))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(image.naturalWidth * scale))
    canvas.height = Math.max(1, Math.round(image.naturalHeight * scale))
    const context = canvas.getContext('2d')
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    emit('update:modelValue', canvas.toDataURL('image/jpeg', 0.88))
  } catch (reason) {
    error.value = reason?.message || '照片处理失败'
  }
}
</script>

<style scoped>
.vre-photo-uploader{grid-column:1/-1;display:grid;grid-template-columns:88px minmax(0,1fr);gap:13px;align-items:center;padding:12px;border:1px solid #2a3140;border-radius:10px;background:linear-gradient(135deg,#1d2430,#1a202a)}.vre-photo-preview{width:82px;height:104px;border:2px solid #435166;border-radius:8px;overflow:hidden;background:#242c38;box-shadow:0 6px 18px rgba(0,0,0,.2)}.vre-photo-preview img{width:100%;height:100%;object-fit:cover}.vre-photo-preview>div{height:100%;display:grid;place-items:center;align-content:center;gap:3px;color:#718095}.vre-photo-preview svg{font-size:33px}.vre-photo-preview span{font-size:9px}.vre-photo-copy{min-width:0;display:grid;gap:5px}.vre-photo-copy strong{font-size:11px}.vre-photo-copy p{margin:0;color:#8993a4;font-size:8.5px;line-height:1.5}.vre-photo-copy>div{display:flex;align-items:center;gap:7px;flex-wrap:wrap}.vre-photo-copy input{display:none}.vre-photo-button,.vre-photo-remove{height:30px;border-radius:7px;padding:0 10px;display:inline-flex;align-items:center;gap:5px;cursor:pointer;font-size:9.5px}.vre-photo-button{border:1px solid #238fc0;background:#17384a;color:#80ddfa}.vre-photo-remove{border:0;background:transparent;color:#e78181}.vre-photo-error{font-size:8.5px;color:#fca5a5}
</style>
