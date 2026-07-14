<template>
  <article class="vre-resume-document" :class="documentClasses" :style="documentStyle">
    <template v-if="layout === 'sidebar'">
      <div class="vre-resume-shell">
        <aside class="vre-resume-aside">
          <div v-if="basicVisible" class="vre-sidebar-profile" @click.stop="$emit('activate', 'basic')">
            <div class="vre-resume-photo"><img v-if="resume.basics.photo" :src="resume.basics.photo" alt="个人照片" /><span v-else>照片</span></div>
            <h1 :style="textStyle(resume.basics, 'name')">{{ resume.basics.name || '你的姓名' }}</h1>
            <div class="vre-resume-role" :style="textStyle(resume.basics, 'title')">{{ resume.basics.title || '目标岗位' }}</div>
            <div class="vre-resume-contact">
              <span v-for="value in contactValues" :key="value">{{ value }}</span>
            </div>
          </div>
          <ResumeSection v-for="section in sideSections" :key="section.key" :section="section" @activate="$emit('activate', $event)" />
        </aside>
        <main class="vre-resume-main">
          <ResumeSection v-for="section in mainSections" :key="section.key" :section="section" @activate="$emit('activate', $event)" />
        </main>
      </div>
    </template>

    <template v-else-if="layout === 'two-column'">
      <ResumeHeader v-if="basicVisible" :resume="resume" :header-style="headerStyle" :align="headerAlign" @click="$emit('activate', 'basic')" />
      <div class="vre-resume-columns">
        <div class="vre-resume-column vre-resume-column--side">
          <ResumeSection v-for="section in sideSections" :key="section.key" :section="section" @activate="$emit('activate', $event)" />
        </div>
        <div class="vre-resume-column">
          <ResumeSection v-for="section in mainSections" :key="section.key" :section="section" @activate="$emit('activate', $event)" />
        </div>
      </div>
    </template>

    <template v-else>
      <ResumeHeader v-if="basicVisible" :resume="resume" :header-style="headerStyle" :align="headerAlign" @click="$emit('activate', 'basic')" />
      <main class="vre-resume-body">
        <ResumeSection v-for="section in visibleSections" :key="section.key" :section="section" @activate="$emit('activate', $event)" />
      </main>
    </template>
  </article>
</template>

<script setup>
import { computed, h } from 'vue'
import ResumeSection from './ResumeSection.vue'

const textStyle = (owner, key) => {
  const value = owner?.field_styles?.[key] || {}
  return {
    ...(Number(value.font_size) ? { fontSize: `${Number(value.font_size)}px` } : {}),
    ...(Number(value.line_height) ? { lineHeight: Number(value.line_height) } : {}),
  }
}

const ResumeHeader = {
  props: ['resume', 'headerStyle', 'align'],
  emits: ['click'],
  setup(props, { emit }) {
    return () => h('header', { class: [`vre-header-${props.headerStyle}`, `vre-align-${props.align}`], onClick: () => emit('click') }, [
      h('div', { class: 'vre-resume-photo' }, props.resume.basics.photo ? [h('img', { src: props.resume.basics.photo, alt: '个人照片' })] : [h('span', '照片')]),
      h('h1', { style: textStyle(props.resume.basics, 'name') }, props.resume.basics.name || '你的姓名'),
      h('div', { class: 'vre-resume-role', style: textStyle(props.resume.basics, 'title') }, props.resume.basics.title || '目标岗位'),
      h('div', { class: 'vre-resume-contact' }, contactItems(props.resume.basics).join(' · ')),
    ])
  },
}

const contactItems = basics => [basics.phone, basics.email, basics.location, basics.url, basics.age ? `${basics.age} 岁` : '', basics.wechat ? `微信：${basics.wechat}` : ''].filter(Boolean)

const props = defineProps({
  resume: { type: Object, required: true },
  template: { type: Object, required: true },
})
defineEmits(['activate'])

const layout = computed(() => props.template.layout || 'single')
const headerStyle = computed(() => props.template.header_style || 'plain')
const headerAlign = computed(() => 'center')
const basicVisible = computed(() => !props.resume.hiddenSections.includes('basic'))
const contactValues = computed(() => contactItems(props.resume.basics))
const visibleSections = computed(() => props.resume.sectionOrder.filter(key => key !== 'basic' && !props.resume.hiddenSections.includes(key)).map(key => props.resume.sections[key]).filter(section => section && hasContent(section)))
const sideKeys = computed(() => layout.value === 'sidebar' ? new Set(['skills', 'education']) : new Set(['summary', 'skills', 'education']))
const sideSections = computed(() => visibleSections.value.filter(section => sideKeys.value.has(section.key)))
const mainSections = computed(() => visibleSections.value.filter(section => !sideKeys.value.has(section.key)))

function hasContent(section) {
  if (section.key === 'summary' || section.key === 'evaluation') return Boolean(section.content?.trim())
  return Boolean(section.entries?.length)
}

const documentClasses = computed(() => [
  `vre-layout-${layout.value}`,
  `vre-section-${props.template.section || 'rule'}`,
  { 'vre-is-compact': props.template.compact, 'vre-has-timeline': props.template.timeline },
])
const documentStyle = computed(() => ({
  '--vre-accent': props.resume.style.accent_color || props.template.accent,
  '--vre-muted': props.template.muted,
  '--vre-sidebar': props.template.sidebar_bg || '#dbeafe',
  '--vre-font': `'${props.resume.style.font_family || props.template.font || 'Microsoft YaHei'}'`,
  '--vre-font-size': `${props.resume.style.font_size || 13}px`,
  '--vre-line-height': props.resume.style.line_height || 1.55,
  '--vre-page-padding': `${props.resume.style.page_padding || 42}px`,
  '--vre-section-gap': `${props.resume.style.section_spacing || 15}px`,
}))
</script>

<style>
.vre-resume-document{box-sizing:border-box;background:#fff;color:#1f2937;width:794px;min-height:1123px;font-family:var(--vre-font),Arial,sans-serif;font-size:var(--vre-font-size);line-height:var(--vre-line-height);overflow:hidden;text-rendering:optimizeLegibility}.vre-resume-document *{box-sizing:border-box}.vre-resume-document header{padding:calc(var(--vre-page-padding) * .58) var(--vre-page-padding) calc(var(--vre-page-padding) * .45);border-bottom:2px solid var(--vre-accent);position:relative;cursor:text;text-align:center}.vre-resume-document header:after{content:'';position:absolute;left:50%;transform:translateX(-50%);bottom:-2px;width:54px;height:4px;border-radius:4px;background:var(--vre-accent)}.vre-resume-document header.vre-header-band{background:linear-gradient(135deg,var(--vre-accent),color-mix(in srgb,var(--vre-accent) 72%,#111827));color:#fff;border:0;padding:calc(var(--vre-page-padding) * .58) var(--vre-page-padding)}.vre-resume-document header.vre-header-band:after{display:none}.vre-resume-document header.vre-header-inline{display:block}.vre-resume-document h1{font-size:2.22em;line-height:1.08;letter-spacing:.08em;color:var(--vre-accent);margin:0;font-weight:800}.vre-resume-document .vre-header-band h1{color:#fff}.vre-resume-photo{width:76px;height:96px;margin:0 auto 9px;border:2px solid color-mix(in srgb,var(--vre-accent) 55%,white);border-radius:8px;overflow:hidden;background:color-mix(in srgb,var(--vre-accent) 7%,white);display:grid;place-items:center;color:var(--vre-muted);font-size:.72em;box-shadow:0 4px 12px rgba(15,23,42,.1)}.vre-resume-photo img{width:100%;height:100%;object-fit:cover}.vre-header-band .vre-resume-photo{border-color:rgba(255,255,255,.82);background:rgba(255,255,255,.14);color:rgba(255,255,255,.82)}.vre-resume-role{font-size:1.03em;font-weight:650;letter-spacing:.03em;margin:7px 0 8px}.vre-resume-contact{font-size:.82em;color:var(--vre-muted);overflow-wrap:anywhere;letter-spacing:.015em}.vre-header-band .vre-resume-contact{color:rgba(255,255,255,.84)}.vre-resume-body{padding:8px var(--vre-page-padding) var(--vre-page-padding)}
.vre-resume-columns{display:grid;grid-template-columns:34% 66%;min-height:inherit}.vre-resume-column{padding:8px calc(var(--vre-page-padding) * .55) var(--vre-page-padding)}.vre-resume-column--side{background:linear-gradient(180deg,color-mix(in srgb,var(--vre-accent) 8%,white),#fff);padding-left:calc(var(--vre-page-padding) * .72)}.vre-resume-column:last-child{padding-right:var(--vre-page-padding)}.vre-resume-shell{display:grid;grid-template-columns:31% 69%;min-height:inherit}.vre-resume-aside{background:linear-gradient(180deg,var(--vre-sidebar),color-mix(in srgb,var(--vre-sidebar) 82%,white));padding:var(--vre-page-padding) calc(var(--vre-page-padding) * .5);color:#1e3a5f;position:relative}.vre-resume-aside:before{content:'';position:absolute;inset:0 auto 0 0;width:7px;background:var(--vre-accent)}.vre-sidebar-profile{cursor:text;text-align:center}.vre-resume-aside .vre-resume-photo{width:82px;height:104px}.vre-resume-aside h1{font-size:2em;letter-spacing:.05em}.vre-resume-aside .vre-resume-contact{display:grid;gap:5px;margin-top:12px;color:#334155}.vre-resume-main{padding:calc(var(--vre-page-padding) * .45) var(--vre-page-padding) var(--vre-page-padding)}.vre-is-compact{--vre-font-size:11.5px;--vre-line-height:1.4;--vre-section-gap:9px}
</style>
