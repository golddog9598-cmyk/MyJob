export const MODULES = [
  { id: 'basic', label: '个人资料', icon: 'mdi:account-outline', hint: '姓名、联系方式与求职信息' },
  { id: 'summary', label: '个人简介', icon: 'mdi:text-account', hint: '三到五行职业概述' },
  { id: 'experience', label: '工作经历', icon: 'mdi:briefcase-outline', hint: '公司、职位、时间与成果' },
  { id: 'education', label: '教育经历', icon: 'mdi:school-outline', hint: '学校、专业、学历与时间' },
  { id: 'projects', label: '项目经历', icon: 'mdi:rocket-launch-outline', hint: '项目角色、技术与产出' },
  { id: 'skills', label: '专业技能', icon: 'mdi:lightning-bolt-outline', hint: '工具、技术栈与能力标签' },
  { id: 'evaluation', label: '自我评价', icon: 'mdi:star-outline', hint: '工作风格与个人特质' },
]

export const MODULE_MAP = Object.fromEntries(MODULES.map(item => [item.id, item]))
export const DEFAULT_ORDER = MODULES.map(item => item.id)

export const uid = (prefix = 'item') => `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`

const blankSections = () => ({
  summary: { id: 'section-summary', key: 'summary', title: '个人简介', content: '', field_styles: {} },
  experience: { id: 'section-experience', key: 'experience', title: '工作经历', entries: [] },
  education: { id: 'section-education', key: 'education', title: '教育经历', entries: [] },
  projects: { id: 'section-projects', key: 'projects', title: '项目经历', entries: [] },
  skills: { id: 'section-skills', key: 'skills', title: '专业技能', entries: [] },
  evaluation: { id: 'section-evaluation', key: 'evaluation', title: '自我评价', content: '', field_styles: {} },
})

export function createResume() {
  return {
    name: '我的简历',
    templateId: 'vivi_elegant',
    basics: { name: '', title: '', phone: '', email: '', location: '', url: '', wechat: '', age: '', photo: '', field_styles: {} },
    sections: blankSections(),
    sectionOrder: [...DEFAULT_ORDER],
    hiddenSections: [],
    style: {
      accent_color: '',
      font_family: 'Microsoft YaHei',
      font_size: 13,
      line_height: 1.55,
      page_padding: 42,
      section_spacing: 15,
    },
  }
}

function splitHeadline(value = '') {
  return String(value).split(/[|｜]/).map(part => part.trim()).filter(Boolean)
}

function parseLegacyEntries(key, items = []) {
  const values = items.map(item => String(item || '').trim()).filter(Boolean)
  if (!values.length) return []
  const entries = []
  for (const value of values) {
    const parts = splitHeadline(value)
    const looksLikeHeadline = parts.length >= 2
    if (looksLikeHeadline) {
      if (key === 'experience') {
        entries.push({ id: uid('work'), company: parts[0] || '', role: parts[1] || '', start_date: '', end_date: parts.slice(2).join(' - '), description: '', field_styles: {} })
      } else if (key === 'education') {
        entries.push({ id: uid('edu'), school: parts[0] || '', major: parts[1] || '', degree: parts[2] || '', start_date: '', end_date: parts.slice(3).join(' - '), description: '', field_styles: {} })
      } else {
        entries.push({ id: uid('project'), name: parts[0] || '', role: parts[1] || '', start_date: '', end_date: parts.slice(2).join(' - '), description: '', technologies: [], field_styles: {} })
      }
    } else if (entries.length) {
      entries[entries.length - 1].description = [entries[entries.length - 1].description, value].filter(Boolean).join('\n')
    } else {
      const base = key === 'experience'
        ? { id: uid('work'), company: '', role: '', start_date: '', end_date: '', field_styles: {} }
        : key === 'education'
          ? { id: uid('edu'), school: '', major: '', degree: '', start_date: '', end_date: '', field_styles: {} }
          : { id: uid('project'), name: '', role: '', start_date: '', end_date: '', technologies: [], field_styles: {} }
      entries.push({ ...base, description: value })
    }
  }
  return entries
}

function cleanEntries(key, section) {
  const raw = Array.isArray(section?.entries) ? section.entries : []
  if (key === 'skills') {
    if (raw.length) return raw.map(entry => ({ id: entry.id || uid('skill'), content: String(entry.content || ''), field_styles: { ...(entry.field_styles || {}) } }))
    const items = section?.items || []
    const content = [section?.content, ...items].filter(Boolean).join('\n')
    return content ? [{ id: uid('skill'), content, field_styles: {} }] : []
  }
  if (raw.length) {
    return raw.map(entry => ({ ...entry, id: entry.id || uid(key), field_styles: { ...(entry.field_styles || {}) }, technologies: key === 'projects' ? (Array.isArray(entry.technologies) ? entry.technologies : String(entry.technologies || '').split(/[,，/、]/).filter(Boolean)) : undefined }))
  }
  return parseLegacyEntries(key, section?.items || [])
}

export function fromApiResume(apiResume) {
  const result = createResume()
  if (!apiResume) return result
  result.name = apiResume.name || result.name
  result.templateId = apiResume.template_id || result.templateId
  const structured = apiResume.structured || {}
  const apiBasics = structured.basics || {}
  result.basics = { ...result.basics, ...apiBasics, age: apiBasics.age || '', field_styles: { ...(apiBasics.field_styles || {}) } }
  delete result.basics.birthday
  result.style = { ...result.style, ...(structured.style || {}) }
  const rawSections = Array.isArray(structured.sections) ? structured.sections : []
  const byKey = Object.fromEntries(rawSections.map(section => [section.key === 'work' ? 'experience' : section.key, section]))
  for (const key of ['summary', 'evaluation']) {
    const section = byKey[key] || {}
    result.sections[key] = {
      ...result.sections[key],
      ...section,
      key,
      content: String(section.content || (section.items || []).join('\n') || ''),
      field_styles: { ...(section.field_styles || {}) },
    }
  }
  for (const key of ['experience', 'education', 'projects', 'skills']) {
    const section = byKey[key] || {}
    result.sections[key] = { ...result.sections[key], ...section, key, entries: cleanEntries(key, section) }
  }
  const requested = (structured.section_order || []).map(key => key === 'work' ? 'experience' : key)
  result.sectionOrder = [...new Set([...requested, ...DEFAULT_ORDER])].filter(key => DEFAULT_ORDER.includes(key))
  result.hiddenSections = [...new Set((structured.hidden_sections || []).map(key => key === 'work' ? 'experience' : key))].filter(key => DEFAULT_ORDER.includes(key))
  return result
}

export function toApiStructure(resume) {
  const sections = resume.sectionOrder
    .filter(key => key !== 'basic')
    .map(key => {
      const section = resume.sections[key] || {}
      if (key === 'summary' || key === 'evaluation') {
        return { id: section.id || `section-${key}`, key, title: section.title || MODULE_MAP[key].label, content: section.content || '', items: [], entries: [], field_styles: { ...(section.field_styles || {}) } }
      }
      return {
        id: section.id || `section-${key}`,
        key,
        title: section.title || MODULE_MAP[key].label,
        content: '',
        items: [],
        entries: (section.entries || []).map(entry => ({ ...entry })),
      }
    })
  return {
    schema_version: 2,
    basics: { ...resume.basics },
    sections,
    section_order: [...resume.sectionOrder],
    hidden_sections: [...resume.hiddenSections],
    style: { ...resume.style },
  }
}

export function newEntry(key) {
  if (key === 'experience') return { id: uid('work'), company: '', role: '', start_date: '', end_date: '', description: '', field_styles: {} }
  if (key === 'education') return { id: uid('edu'), school: '', major: '', degree: '', start_date: '', end_date: '', description: '', field_styles: {} }
  if (key === 'projects') return { id: uid('project'), name: '', role: '', start_date: '', end_date: '', description: '', technologies: [], field_styles: {} }
  return { id: uid('skill'), content: '', field_styles: {} }
}
