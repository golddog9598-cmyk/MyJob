<template>
  <section class="vre-resume-section" :data-section="section.key" @click.stop="$emit('activate', section.key)">
    <h3><span>{{ section.title || label }}</span></h3>

    <div v-if="section.key === 'summary' || section.key === 'evaluation'" class="vre-section-copy" :style="textStyle(section, 'content')">
      <p v-for="(line, index) in textLines(section.content)" :key="index">{{ line }}</p>
    </div>

    <div v-else-if="section.key === 'skills'" class="vre-skill-list">
      <span v-for="(skill, index) in skills" :key="index" :style="skill.style">{{ skill.value }}</span>
    </div>

    <div v-else class="vre-entry-list">
      <article v-for="entry in section.entries" :key="entry.id" class="vre-resume-entry">
        <div class="vre-entry-heading">
          <div>
            <strong :style="textStyle(entry, entryTitleField)">{{ entryTitle(entry) }}</strong>
            <span v-for="(part, index) in entrySubtitleParts(entry)" :key="part.field" :style="textStyle(entry, part.field)">{{ index ? `· ${part.text}` : part.text }}</span>
          </div>
          <time v-if="dateRange(entry)">{{ dateRange(entry) }}</time>
        </div>
        <div v-if="descriptionItems(entry.description).length" class="vre-entry-description-list">
          <p v-for="(item, index) in descriptionItems(entry.description)" :key="index" class="vre-entry-description" :style="textStyle(entry, 'description')"><span>{{ item.marker }}</span><span>{{ item.text }}</span></p>
        </div>
        <div v-if="section.key === 'projects' && entry.technologies?.length" class="vre-entry-tags">
          <span v-for="technology in entry.technologies" :key="technology" :style="textStyle(entry, 'technologies')">{{ technology }}</span>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { MODULE_MAP } from '../model'

const props = defineProps({ section: { type: Object, required: true } })
defineEmits(['activate'])

const label = computed(() => MODULE_MAP[props.section.key]?.label || '其他')
const entryTitleField = computed(() => props.section.key === 'education' ? 'school' : props.section.key === 'experience' ? 'company' : 'name')
const textLines = value => String(value || '').split('\n').map(line => line.trim()).filter(Boolean)
const dateRange = entry => [entry.start_date, entry.end_date].filter(Boolean).join(' - ')
const descriptionItems = value => textLines(value).map(line => {
  const ordered = line.match(/^\s*(\d+)[.)、]\s*(.*)$/)
  if (ordered) return { marker: `${ordered[1]}.`, text: ordered[2].trim() }
  return { marker: '•', text: line.replace(/^\s*[-*•]\s*/, '').trim() }
}).filter(item => item.text)

function entryTitle(entry) {
  if (props.section.key === 'education') return entry.school || '学校名称'
  if (props.section.key === 'experience') return entry.company || '公司名称'
  return entry.name || '项目名称'
}

function entrySubtitleParts(entry) {
  if (props.section.key === 'education') return [{ field: 'major', text: entry.major }, { field: 'degree', text: entry.degree }].filter(item => item.text)
  return entry.role ? [{ field: 'role', text: entry.role }] : []
}

const textStyle = (owner, key) => {
  const value = owner?.field_styles?.[key] || {}
  return {
    ...(Number(value.font_size) ? { fontSize: `${Number(value.font_size)}px` } : {}),
    ...(Number(value.line_height) ? { lineHeight: Number(value.line_height) } : {}),
  }
}
const skills = computed(() => (props.section.entries || []).flatMap(entry => String(entry.content || '').split(/[,，/、|\n]/).map(value => value.trim()).filter(Boolean).map(value => ({ value, style: textStyle(entry, 'content') }))))
</script>

<style scoped>
.vre-resume-section{break-inside:avoid;margin-top:var(--vre-section-gap);cursor:text}.vre-resume-section h3{display:flex;align-items:center;gap:9px;font-size:1.08em;line-height:1.35;color:var(--vre-accent);margin:0 0 8px;padding:0 0 5px;border-bottom:1px solid color-mix(in srgb,var(--vre-accent) 42%,white);font-weight:750;letter-spacing:.08em}.vre-resume-section h3:before{content:'';width:4px;height:1.05em;border-radius:4px;background:var(--vre-accent);flex:0 0 auto}
.vre-section-copy p{margin:0;white-space:pre-wrap;color:#374151}.vre-section-copy p+p{margin-top:5px}.vre-resume-entry{position:relative;margin:0 0 11px;padding:0 0 0 14px;border-left:2px solid color-mix(in srgb,var(--vre-accent) 25%,white)}.vre-resume-entry:last-child{margin-bottom:0}.vre-resume-entry:before{content:'';position:absolute;left:-5px;top:5px;width:8px;height:8px;border:2px solid #fff;border-radius:50%;background:var(--vre-accent)}.vre-entry-heading{display:flex;justify-content:space-between;gap:14px;align-items:baseline}.vre-entry-heading strong{font-size:1em;color:#111827}.vre-entry-heading span{font-size:.88em;color:var(--vre-muted);margin-left:8px}.vre-entry-heading time{font-size:.78em;color:var(--vre-muted);white-space:nowrap}.vre-entry-description-list{margin-top:4px}.vre-entry-description{display:grid;grid-template-columns:1.25em minmax(0,1fr);gap:2px;margin:2px 0;color:#374151;white-space:pre-wrap}.vre-entry-description>span:first-child{color:var(--vre-accent);font-weight:700}.vre-entry-tags,.vre-skill-list{display:flex;gap:5px;flex-wrap:wrap;margin-top:5px}.vre-entry-tags span,.vre-skill-list span{border-radius:999px;background:color-mix(in srgb,var(--vre-accent) 9%,white);color:color-mix(in srgb,var(--vre-accent) 76%,#111827);padding:3px 8px;font-size:.78em}
:global(.vre-resume-document.vre-section-plain) .vre-resume-section h3{border:0;text-transform:uppercase;letter-spacing:.13em}:global(.vre-resume-document.vre-section-band) .vre-resume-section h3{border:0;background:color-mix(in srgb,var(--vre-accent) 9%,white);padding:6px 9px;border-radius:4px}:global(.vre-resume-document.vre-section-card) .vre-resume-section{border:1px solid color-mix(in srgb,var(--vre-accent) 18%,white);border-radius:10px;padding:11px 13px;box-shadow:0 3px 12px rgba(15,23,42,.035)}:global(.vre-resume-document.vre-section-card) .vre-resume-section h3{border:0}:global(.vre-resume-document.vre-section-dark) .vre-resume-section h3{background:linear-gradient(90deg,var(--vre-accent),color-mix(in srgb,var(--vre-accent) 78%,#111827));color:#fff;border:0;padding:6px 10px;border-radius:2px}:global(.vre-resume-document.vre-section-dark) .vre-resume-section h3:before{background:#fff}
:global(.vre-resume-document.vre-layout-sidebar .vre-resume-aside) .vre-resume-section h3{font-size:1em}:global(.vre-resume-document.vre-layout-sidebar .vre-resume-aside) .vre-skill-list{display:grid}:global(.vre-resume-document.vre-layout-sidebar .vre-resume-aside) .vre-skill-list span{background:rgba(255,255,255,.58)}
</style>
