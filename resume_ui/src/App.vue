<template>
  <div class="vre-app">
    <header class="vre-toolbar">
      <div class="vre-toolbar-title">
        <div class="vre-title-mark"><Icon icon="mdi:file-document-edit-outline" /></div>
        <div>
          <div class="vre-title-row">
            <input v-model="resume.name" class="vre-resume-name" aria-label="简历名称" @input="markDirty" />
          </div>
          <p>结构化编辑 · 实时 A4 预览 · 模板化导出</p>
        </div>
      </div>
      <div class="vre-toolbar-actions">
        <input ref="fileInput" type="file" class="vre-file-input" accept=".docx,.pdf,.txt,.md,.markdown,.html,.htm,.rtf,.json,.odt" @change="uploadResume" />
        <button class="vre-btn" @click="fileInput?.click()"><Icon icon="mdi:upload-outline" />导入简历</button>
        <button class="vre-btn" @click="resetResume"><Icon icon="mdi:file-plus-outline" />新建</button>
        <button class="vre-btn vre-btn-template" @click="showTemplates = true"><Icon icon="mdi:view-grid-outline" />更换模板</button>
        <button class="vre-btn" @click="openTailored"><Icon icon="mdi:file-star-outline" />JD 定制稿</button>
        <button class="vre-btn vre-btn-primary" :disabled="saving" @click="saveResume"><Icon :icon="saving ? 'mdi:loading' : 'mdi:content-save-outline'" :class="{ spin: saving }" />{{ saving ? '保存中' : '保存' }}</button>
        <div class="vre-export-group">
          <button class="vre-btn vre-btn-export" @click="download('docx')">DOCX</button>
          <button class="vre-btn vre-btn-export" @click="download('pdf')">PDF</button>
        </div>
      </div>
    </header>

    <div v-if="errorMessage" class="vre-banner vre-banner-error">{{ errorMessage }}<button @click="errorMessage = ''">×</button></div>
    <div v-if="successMessage" class="vre-banner vre-banner-success">{{ successMessage }}</div>

    <main v-if="!loading" class="vre-editor-layout">
      <aside class="vre-module-panel">
        <div class="vre-panel-head">
          <div><strong>简历模块</strong><span>拖动调整排版顺序</span></div>
          <span>{{ visibleModuleCount }}/7</span>
        </div>
        <draggable v-model="resume.sectionOrder" :item-key="item => item" handle=".vre-drag-handle" class="vre-module-list" @end="markDirty">
          <template #item="{ element }">
            <div class="vre-module-item" :class="{ active: activeId === element, hidden: isHidden(element) }" @click="activeId = element">
              <button class="vre-drag-handle" :aria-label="`拖拽${moduleInfo(element).label}排序`" title="拖拽排序" @click.stop><Icon icon="mdi:drag-vertical" /></button>
              <Icon :icon="moduleInfo(element).icon" class="vre-module-icon" />
              <div class="vre-module-copy"><strong>{{ moduleInfo(element).label }}</strong><span>{{ moduleInfo(element).hint }}</span></div>
              <div class="vre-module-order-actions">
                <button :aria-label="`上移${moduleInfo(element).label}`" :disabled="resume.sectionOrder.indexOf(element) === 0" title="上移" @click.stop="moveSection(element, -1)"><Icon icon="mdi:chevron-up" /></button>
                <button :aria-label="`下移${moduleInfo(element).label}`" :disabled="resume.sectionOrder.indexOf(element) === resume.sectionOrder.length - 1" title="下移" @click.stop="moveSection(element, 1)"><Icon icon="mdi:chevron-down" /></button>
              </div>
              <label class="vre-switch" :title="isHidden(element) ? '启用模块' : '隐藏模块'" @click.stop>
                <input type="checkbox" :checked="!isHidden(element)" @change="toggleSection(element)" />
                <span></span>
              </label>
            </div>
          </template>
        </draggable>

        <div class="vre-style-panel">
          <div class="vre-style-title"><Icon icon="mdi:palette-outline" />排版与样式</div>
          <label>主题色<div class="vre-color-row"><input v-model="resume.style.accent_color" type="color" :value="effectiveAccent" @input="markDirty" /><span>{{ resume.style.accent_color || currentTemplate.accent }}</span><button @click="resume.style.accent_color = '';markDirty()">重置</button></div></label>
          <label>字体<select v-model="resume.style.font_family" @change="markDirty"><option>Microsoft YaHei</option><option>DengXian</option><option>SimSun</option><option>Arial</option><option>Noto Sans SC</option></select></label>
          <label>全局页边距 <b>{{ resume.style.page_padding }}px</b><input v-model.number="resume.style.page_padding" type="range" min="24" max="72" step="2" @input="markDirty" /></label>
          <label>全局模块间距 <b>{{ resume.style.section_spacing }}px</b><input v-model.number="resume.style.section_spacing" type="range" min="8" max="28" step="1" @input="markDirty" /></label>
        </div>
      </aside>

      <section class="vre-form-panel">
        <div class="vre-form-head">
          <div class="vre-form-icon"><Icon :icon="moduleInfo(activeId).icon" /></div>
          <div><h3>{{ moduleInfo(activeId).label }}</h3><p>{{ moduleInfo(activeId).hint }}</p></div>
          <span v-if="isHidden(activeId)" class="vre-hidden-badge">当前未显示</span>
        </div>

        <div class="vre-form-scroll">
          <template v-if="activeId === 'basic'">
            <div class="vre-field-grid">
              <PhotoUploader v-model="resume.basics.photo" @update:model-value="markDirty" />
              <StyledField v-model="resume.basics.field_styles.name" class="wide" label="姓名" :default-font-size="fieldFontSize('name')" :default-line-height="fieldLineHeight('name')" @update:model-value="markDirty"><input v-model="resume.basics.name" aria-label="姓名" placeholder="你的姓名" @input="markDirty" /></StyledField>
              <StyledField v-model="resume.basics.field_styles.title" class="wide" label="目标岗位" :default-font-size="fieldFontSize('basicRole')" :default-line-height="fieldLineHeight('basicRole')" @update:model-value="markDirty"><input v-model="resume.basics.title" aria-label="目标岗位" placeholder="例如：AI 产品经理" @input="markDirty" /></StyledField>
              <label><span>手机</span><input v-model="resume.basics.phone" placeholder="手机号码" @input="markDirty" /></label>
              <label><span>邮箱</span><input v-model="resume.basics.email" placeholder="name@example.com" @input="markDirty" /></label>
              <label><span>所在城市</span><input v-model="resume.basics.location" placeholder="深圳" @input="markDirty" /></label>
              <label><span>个人主页</span><input v-model="resume.basics.url" placeholder="作品集或 GitHub" @input="markDirty" /></label>
              <label><span>微信</span><input v-model="resume.basics.wechat" placeholder="可选" @input="markDirty" /></label>
              <label><span>年龄</span><input v-model="resume.basics.age" type="number" min="16" max="80" placeholder="例如：28" @input="markDirty" /></label>
            </div>
          </template>

          <template v-else-if="activeId === 'summary' || activeId === 'evaluation'">
            <StyledField v-model="activeSection.field_styles.content" class="vre-textarea-field" :label="activeId === 'summary' ? '简介内容' : '评价内容'" :default-font-size="fieldFontSize('body')" :default-line-height="fieldLineHeight('body')" @update:model-value="markDirty"><textarea v-model="activeSection.content" rows="14" :aria-label="activeId === 'summary' ? '简介内容' : '评价内容'" :placeholder="activeId === 'summary' ? '用 3-5 行概括经验、方向和核心优势。' : '描述你的工作风格、优势和职业态度。'" @input="markDirty"></textarea><small>{{ activeSection.content.length }} 字</small></StyledField>
            <div class="vre-writing-tip"><Icon icon="mdi:lightbulb-on-outline" /><div><strong>写作建议</strong><p>{{ activeId === 'summary' ? '优先写年限、领域、能力和结果，避免空泛的“学习能力强”。' : '写可验证的工作习惯和合作方式，避免堆砌形容词。' }}</p></div></div>
          </template>

          <template v-else>
            <div class="vre-list-toolbar">
              <button class="vre-btn vre-btn-primary" @click="addEntry(activeId)"><Icon icon="mdi:plus" />添加{{ entryLabel }}</button>
            </div>
            <draggable v-model="activeSection.entries" item-key="id" handle=".vre-entry-drag" class="vre-edit-entry-list" @end="markDirty">
              <template #item="{ element: entry, index }">
                <article class="vre-edit-card">
                  <div class="vre-edit-card-head"><button class="vre-entry-drag" title="拖动条目"><Icon icon="mdi:drag" /></button><strong>{{ entryLabel }} {{ index + 1 }}</strong><button class="vre-remove" @click="removeEntry(index)"><Icon icon="mdi:trash-can-outline" />删除</button></div>
                  <div v-if="activeId === 'experience'" class="vre-field-grid">
                    <StyledField v-model="entry.field_styles.company" class="wide" label="公司" :default-font-size="fieldFontSize('body')" :default-line-height="fieldLineHeight('meta')" @update:model-value="markDirty"><input v-model="entry.company" aria-label="公司" placeholder="公司名称" @input="markDirty" /></StyledField><StyledField v-model="entry.field_styles.role" class="wide" label="职位" :default-font-size="fieldFontSize('subtitle')" :default-line-height="fieldLineHeight('meta')" @update:model-value="markDirty"><input v-model="entry.role" aria-label="职位" placeholder="职位名称" @input="markDirty" /></StyledField>
                    <label><span>开始时间</span><MonthPicker v-model="entry.start_date" aria-label="工作开始时间" @update:model-value="markDirty" /></label><label><span>结束时间</span><MonthPicker v-model="entry.end_date" aria-label="工作结束时间" :min-value="entry.start_date" allow-present @update:model-value="markDirty" /></label>
                    <p v-if="dateError(entry)" class="vre-date-error wide"><Icon icon="mdi:alert-circle-outline" />{{ dateError(entry) }}</p>
                    <BulletEditor v-model="entry.description" v-model:text-style="entry.field_styles.description" class="wide" label="工作内容与成果" :default-font-size="fieldFontSize('body')" :default-line-height="fieldLineHeight('body')" :rows="6" placeholder="每行写一项职责或可核实成果，可选择无序或有序分点" @update:model-value="markDirty" @update:text-style="markDirty" />
                  </div>
                  <div v-else-if="activeId === 'education'" class="vre-field-grid">
                    <StyledField v-model="entry.field_styles.school" class="wide" label="学校" :default-font-size="fieldFontSize('body')" :default-line-height="fieldLineHeight('meta')" @update:model-value="markDirty"><input v-model="entry.school" aria-label="学校" placeholder="学校名称" @input="markDirty" /></StyledField><StyledField v-model="entry.field_styles.major" label="专业" :default-font-size="fieldFontSize('subtitle')" :default-line-height="fieldLineHeight('meta')" @update:model-value="markDirty"><input v-model="entry.major" aria-label="专业" placeholder="专业" @input="markDirty" /></StyledField><StyledField v-model="entry.field_styles.degree" label="学历" :default-font-size="fieldFontSize('subtitle')" :default-line-height="fieldLineHeight('meta')" @update:model-value="markDirty"><input v-model="entry.degree" aria-label="学历" placeholder="本科" @input="markDirty" /></StyledField>
                    <label><span>开始时间</span><MonthPicker v-model="entry.start_date" aria-label="教育开始时间" @update:model-value="markDirty" /></label><label><span>结束时间</span><MonthPicker v-model="entry.end_date" aria-label="教育结束时间" :min-value="entry.start_date" @update:model-value="markDirty" /></label><p v-if="dateError(entry)" class="vre-date-error wide"><Icon icon="mdi:alert-circle-outline" />{{ dateError(entry) }}</p><StyledField v-model="entry.field_styles.description" class="wide" label="补充说明" :default-font-size="fieldFontSize('body')" :default-line-height="fieldLineHeight('body')" @update:model-value="markDirty"><textarea v-model="entry.description" aria-label="补充说明" rows="4" placeholder="主修课程、荣誉或校园经历（可选）" @input="markDirty"></textarea></StyledField>
                  </div>
                  <div v-else-if="activeId === 'projects'" class="vre-field-grid">
                    <StyledField v-model="entry.field_styles.name" class="wide" label="项目名称" :default-font-size="fieldFontSize('body')" :default-line-height="fieldLineHeight('meta')" @update:model-value="markDirty"><input v-model="entry.name" aria-label="项目名称" placeholder="项目名称" @input="markDirty" /></StyledField><StyledField v-model="entry.field_styles.role" class="wide" label="担任角色" :default-font-size="fieldFontSize('subtitle')" :default-line-height="fieldLineHeight('meta')" @update:model-value="markDirty"><input v-model="entry.role" aria-label="担任角色" placeholder="产品负责人 / 核心开发" @input="markDirty" /></StyledField>
                    <label><span>开始时间</span><MonthPicker v-model="entry.start_date" aria-label="项目开始时间" @update:model-value="markDirty" /></label><label><span>结束时间</span><MonthPicker v-model="entry.end_date" aria-label="项目结束时间" :min-value="entry.start_date" allow-present @update:model-value="markDirty" /></label>
                    <p v-if="dateError(entry)" class="vre-date-error wide"><Icon icon="mdi:alert-circle-outline" />{{ dateError(entry) }}</p>
                    <StyledField v-model="entry.field_styles.technologies" class="wide" label="技术/关键词" :default-font-size="fieldFontSize('tag')" :default-line-height="fieldLineHeight('tag')" @update:model-value="markDirty"><input :value="(entry.technologies || []).join(', ')" aria-label="技术/关键词" placeholder="Python, FastAPI, RAG" @input="setTechnologies(entry, $event.target.value)" /></StyledField><BulletEditor v-model="entry.description" v-model:text-style="entry.field_styles.description" class="wide" label="项目内容与成果" :default-font-size="fieldFontSize('body')" :default-line-height="fieldLineHeight('body')" :rows="6" placeholder="分点说明背景、动作、产物和结果" @update:model-value="markDirty" @update:text-style="markDirty" />
                  </div>
                  <div v-else class="vre-field-grid"><StyledField v-model="entry.field_styles.content" class="wide" label="技能内容" :default-font-size="fieldFontSize('tag')" :default-line-height="fieldLineHeight('tag')" @update:model-value="markDirty"><textarea v-model="entry.content" aria-label="技能内容" rows="5" placeholder="例如：Python / FastAPI / PostgreSQL / RAG" @input="markDirty"></textarea></StyledField></div>
                </article>
              </template>
            </draggable>
            <button v-if="!activeSection.entries.length" class="vre-empty-add" @click="addEntry(activeId)"><Icon icon="mdi:plus-circle-outline" />添加第一条{{ entryLabel }}</button>
          </template>
        </div>
      </section>

      <section ref="previewHost" class="vre-preview-panel">
        <div class="vre-preview-head"><div><strong>实时预览</strong><span>{{ currentTemplate.name }} · A4</span></div><div class="vre-zoom"><button @click="previewScale = Math.max(.35, previewScale - .05)">−</button><span>{{ Math.round(previewScale * 100) }}%</span><button @click="previewScale = Math.min(1, previewScale + .05)">＋</button></div></div>
        <div class="vre-page-stage">
          <div class="vre-page-space" :style="{ width: `${794 * previewScale}px`, height: `${1123 * previewScale}px` }">
            <div class="vre-page-transform" :style="{ transform: `scale(${previewScale})` }">
              <ResumeDocument :resume="resume" :template="currentTemplate" @activate="activeId = $event" />
            </div>
          </div>
        </div>
      </section>
    </main>

    <div v-else class="vre-loading"><span></span><p>正在加载简历编辑器...</p></div>

    <Teleport to="body">
      <div v-if="showTemplates" class="vre-modal-backdrop" @click.self="showTemplates = false">
        <section class="vre-modal vre-template-modal">
          <header><div><h2>选择简历模板</h2><p>模板只改变视觉与布局，不会改写简历内容</p></div><button @click="showTemplates = false">×</button></header>
          <div class="vre-template-tools"><input v-model="templateQuery" placeholder="搜索模板名称或场景" /><label><input v-model="atsOnly" type="checkbox" />仅看 ATS 友好</label></div>
          <div class="vre-template-grid">
            <button v-for="template in filteredTemplates" :key="template.id" class="vre-template-card" :class="{ selected: resume.templateId === template.id }" @click="selectTemplate(template.id)">
              <div class="vre-template-preview"><div class="vre-template-canvas"><ResumeDocument :resume="resume" :template="template" /></div></div>
              <div class="vre-template-meta"><div><strong>{{ template.name }}</strong><p>{{ template.description }}</p></div><span>{{ template.category }}</span></div>
              <div class="vre-template-tags"><span v-for="feature in template.features" :key="feature">{{ feature }}</span></div>
            </button>
          </div>
        </section>
      </div>

      <div v-if="showTailored" class="vre-modal-backdrop" @click.self="showTailored = false">
        <section class="vre-modal vre-tailored-modal">
          <header><div><h2>JD 定制简历</h2><p>当前浏览器直连你配置的 AI 服务，不经过 MyJob 后端</p></div><button @click="showTailored = false">×</button></header>
          <div v-if="!tailoredResumes.length" class="vre-modal-empty">暂无本地 JD 草稿，请先在岗位中心选择“定制简历”。</div>
          <div v-else class="vre-tailor-workspace">
            <aside class="vre-tailored-list">
              <article v-for="item in tailoredResumes" :key="item.id" :class="{ selected: selectedTailor?.id === item.id }">
                <button class="vre-tailor-select" @click="selectTailorDraft(item)"><strong>{{ item.job_title || '定制简历' }}</strong><span>{{ item.company || '未填写公司' }} · {{ item.description ? '完整 JD' : 'JD 待补充' }}</span></button>
              </article>
            </aside>
            <main v-if="selectedTailor" class="vre-tailor-main">
              <section class="vre-tailor-context"><div><strong>{{ selectedTailor.job_title }}</strong><span>{{ selectedTailor.company }} · {{ selectedTailor.city }}</span></div><p>{{ selectedTailor.description || '尚未读取到岗位 JD，请回到岗位中心重新创建定制稿。' }}</p></section>
              <section class="vre-tailor-controls">
                <label>事实约束强度<select v-model="tailorLevel"><option v-for="(profile, key) in factLevels" :key="key" :value="key">{{ profile.label }}</option></select></label>
                <div class="vre-tailor-privacy"><p>{{ factLevels[tailorLevel].description }}</p><label><input v-model="tailorAiConsent" type="checkbox" />同意将当前 JD 和五个可优化模块发送到已配置的 AI 服务</label></div>
                <button class="vre-btn vre-btn-primary" :disabled="tailoring || !selectedTailor.description || !tailorAiConsent" @click="runTailorOptimization"><Icon :icon="tailoring ? 'mdi:loading' : 'mdi:auto-fix'" :class="{ spin: tailoring }" />{{ tailoring ? '正在优化' : '开始优化' }}</button>
              </section>
              <template v-if="tailorResult">
                <div v-if="tailorResult.jd_keywords.length" class="vre-tailor-keywords"><span>JD 关键词</span><b v-for="keyword in tailorResult.jd_keywords" :key="keyword">{{ keyword }}</b></div>
                <div class="vre-tailor-result-head"><strong>{{ tailorResult.suggestions.length }} 条候选修改</strong><button class="vre-btn" @click="applyReadySuggestions">应用无需确认及已确认建议</button></div>
                <div v-if="!tailorResult.suggestions.length" class="vre-modal-empty compact">当前强度下没有可用的优化建议</div>
                <article v-for="(suggestion, index) in tailorResult.suggestions" :key="`${suggestion.section}-${suggestion.entry_id}-${suggestion.field}`" class="vre-tailor-suggestion" :class="{ applied: suggestion.applied }">
                  <header><div><strong>{{ suggestionLabel(suggestion) }}</strong><span v-if="suggestion.matched_keywords.length">匹配 {{ suggestion.matched_keywords.join('、') }}</span></div><b v-if="suggestion.needs_confirmation">待确认事实</b></header>
                  <div class="vre-tailor-diff"><section><span>原内容</span><p>{{ formatSuggestionValue(suggestion.original) || '（空）' }}</p></section><section><span>优化建议</span><p>{{ formatSuggestionValue(suggestion.optimized) }}</p></section></div>
                  <p v-if="suggestion.reason" class="vre-tailor-reason">{{ suggestion.reason }}</p>
                  <ul v-if="suggestion.additions.length" class="vre-tailor-additions"><li v-for="addition in suggestion.additions" :key="`${addition.type}-${addition.text}`"><b>{{ addition.type === 'metric' ? '量化结果' : '新增事实' }}</b><span>{{ addition.text }}</span></li></ul>
                  <footer><label v-if="suggestion.needs_confirmation"><input v-model="tailorConfirmations[index]" type="checkbox" />我确认新增内容真实、可在面试中说明</label><span v-else>仅改写原有内容</span><button class="vre-btn" :disabled="suggestion.applied || (suggestion.needs_confirmation && !tailorConfirmations[index])" @click="applySuggestion(index)">{{ suggestion.applied ? '已应用' : '应用此建议' }}</button></footer>
                </article>
              </template>
              <div v-else class="vre-tailor-placeholder"><Icon icon="mdi:file-search-outline" /><strong>选择约束强度后开始优化</strong><span>只会修改个人简介、工作经历、项目经历、专业技能和自我评价。</span></div>
            </main>
            <div v-else class="vre-tailor-placeholder"><Icon icon="mdi:briefcase-search-outline" /><strong>选择一个岗位草稿</strong><span>完整 JD 将用于生成结构化修改建议。</span></div>
          </div>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { Icon } from '@iconify/vue'
import draggable from 'vuedraggable'
import BulletEditor from './components/BulletEditor.vue'
import MonthPicker from './components/MonthPicker.vue'
import PhotoUploader from './components/PhotoUploader.vue'
import ResumeDocument from './components/ResumeDocument.vue'
import StyledField from './components/StyledField.vue'
import { MODULE_MAP, createResume, fromApiResume, newEntry, toApiStructure } from './model'
import { platformStore } from './platformStore'
import { FACT_CONSTRAINT_LEVELS, applyTailorSuggestion, optimizeResumeForJd, tailorFingerprint } from './resumeTailor'

const resume = reactive(createResume())
const templates = ref([])
const tailoredResumes = ref([])
const selectedTailor = ref(null)
const tailoring = ref(false)
const tailorLevel = ref('high')
const tailorResult = ref(null)
const tailorConfirmations = ref({})
const tailorAiConsent = ref(false)
const factLevels = FACT_CONSTRAINT_LEVELS
const activeId = ref('basic')
const loading = ref(true)
const saving = ref(false)
const dirty = ref(false)
const saved = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const showTemplates = ref(false)
const showTailored = ref(false)
const templateQuery = ref('')
const atsOnly = ref(false)
const fileInput = ref(null)
const previewHost = ref(null)
const previewScale = ref(.72)
let resizeObserver
let successTimer

const currentTemplate = computed(() => templates.value.find(item => item.id === resume.templateId) || templates.value[0] || { id: 'ats_classic', name: 'ATS 经典', accent: '#202124', muted: '#64748b', font: 'Microsoft YaHei', layout: 'single', header: 'center', header_style: 'plain', section: 'rule', features: ['单栏', 'ATS'] })
const effectiveAccent = computed(() => resume.style.accent_color || currentTemplate.value.accent)
const activeSection = computed(() => resume.sections[activeId.value] || resume.sections.summary)
const entryLabel = computed(() => ({ experience: '工作经历', education: '教育经历', projects: '项目经历', skills: '技能项' }[activeId.value] || '条目'))
const visibleModuleCount = computed(() => resume.sectionOrder.filter(key => !resume.hiddenSections.includes(key)).length)
const filteredTemplates = computed(() => {
  const query = templateQuery.value.trim().toLowerCase()
  return templates.value.filter(item => (!atsOnly.value || item.ats_friendly) && (!query || [item.name, item.category, item.description, ...(item.features || [])].join(' ').toLowerCase().includes(query)))
})
const invalidDateEntries = computed(() => ['experience', 'education', 'projects'].flatMap(key =>
  (resume.sections[key]?.entries || []).filter(entry => dateError(entry)).map(entry => ({ key, entry })),
))

const moduleInfo = key => MODULE_MAP[key] || MODULE_MAP.summary
const isHidden = key => resume.hiddenSections.includes(key)
const markDirty = () => { dirty.value = true; successMessage.value = '' }

const fieldFontSize = variant => {
  const base = Number(resume.style.font_size || 13)
  const ratio = { name: 2.22, basicRole: 1.03, subtitle: .88, tag: .78 }[variant] || 1
  return Math.round(base * ratio * 2) / 2
}
const fieldLineHeight = variant => ({ name: 1.08, basicRole: 1.35, meta: 1.35, tag: 1.3 }[variant] || Number(resume.style.line_height || 1.55))

function dateValue(value) {
  const normalized = String(value || '').trim()
  if (/^(至今|现在|present)$/i.test(normalized)) return Number.POSITIVE_INFINITY
  const match = normalized.match(/^(\d{4})[.\-/年](\d{1,2})/)
  return match ? Number(match[1]) * 12 + Number(match[2]) : null
}

function dateError(entry) {
  const start = dateValue(entry?.start_date)
  const end = dateValue(entry?.end_date)
  return start !== null && end !== null && end < start ? '结束时间不能早于开始时间' : ''
}

function replaceResume(next) {
  Object.keys(resume).forEach(key => delete resume[key])
  Object.assign(resume, next)
}

function toggleSection(key) {
  if (isHidden(key)) resume.hiddenSections = resume.hiddenSections.filter(item => item !== key)
  else resume.hiddenSections.push(key)
  markDirty()
}

function moveSection(key, direction) {
  const from = resume.sectionOrder.indexOf(key)
  const to = from + direction
  if (from < 0 || to < 0 || to >= resume.sectionOrder.length) return
  const [section] = resume.sectionOrder.splice(from, 1)
  resume.sectionOrder.splice(to, 0, section)
  markDirty()
}

function addEntry(key) {
  resume.sections[key].entries.push(newEntry(key))
  markDirty()
  nextTick(() => { const panel = document.querySelector('.vre-form-scroll'); if (panel) panel.scrollTop = panel.scrollHeight })
}

function removeEntry(index) {
  activeSection.value.entries.splice(index, 1)
  markDirty()
}

function setTechnologies(entry, value) {
  entry.technologies = String(value).split(/[,，/、]/).map(item => item.trim()).filter(Boolean)
  markDirty()
}

function selectTemplate(id) {
  resume.templateId = id
  showTemplates.value = false
  markDirty()
}

function notify(message) {
  successMessage.value = message
  clearTimeout(successTimer)
  successTimer = setTimeout(() => { successMessage.value = '' }, 2400)
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [templateResponse, resumeResponse, localTailored] = await Promise.all([
      fetch('/api/resume-templates'), fetch('/api/resumes/master'), platformStore.listTailorDrafts(),
    ])
    if (!templateResponse.ok || !resumeResponse.ok) throw new Error('简历编辑器数据加载失败')
    const templateData = await templateResponse.json()
    const resumeData = await resumeResponse.json()
    templates.value = templateData.templates || []
    replaceResume(fromApiResume(resumeData.resume))
    tailoredResumes.value = localTailored
    saved.value = Boolean(resumeData.resume)
    dirty.value = false
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
    nextTick(updatePreviewScale)
  }
}

async function saveResume() {
  if (saving.value) return false
  if (invalidDateEntries.value.length) {
    const labels = { experience: '工作经历', education: '教育经历', projects: '项目经历' }
    errorMessage.value = `${labels[invalidDateEntries.value[0].key]}存在错误：结束时间不能早于开始时间`
    return false
  }
  saving.value = true
  errorMessage.value = ''
  try {
    const response = await fetch('/api/resumes/master/structured', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: resume.name || '主简历', template_id: resume.templateId, structured: toApiStructure(resume) }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || '保存失败')
    replaceResume(fromApiResume(data.resume))
    saved.value = true
    dirty.value = false
    notify('简历已保存')
    return true
  } catch (error) {
    errorMessage.value = error.message
    return false
  } finally {
    saving.value = false
  }
}

async function uploadResume(event) {
  const file = event.target.files?.[0]
  if (!file) return
  errorMessage.value = ''
  try {
    const body = new FormData()
    body.append('file', file)
    body.append('template_id', resume.templateId)
    const response = await fetch('/api/resumes/upload', { method: 'POST', body })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || '解析失败')
    replaceResume(fromApiResume(data.resume))
    saved.value = true
    dirty.value = false
    notify(`已解析 ${data.parse.sections} 个模块`)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    event.target.value = ''
  }
}

function resetResume() {
  if (dirty.value && !window.confirm('当前修改尚未保存，确定新建简历吗？')) return
  replaceResume(createResume())
  saved.value = false
  dirty.value = true
  activeId.value = 'basic'
}

async function download(format) {
  if (!saved.value || dirty.value) {
    const ok = await saveResume()
    if (!ok) return
  }
  const link = document.createElement('a')
  link.href = `/api/resumes/master/export?format=${format}&template_id=${encodeURIComponent(resume.templateId)}`
  link.click()
}

function copyJson(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value))
}

function selectTailorDraft(item) {
  selectedTailor.value = item
  tailorConfirmations.value = {}
  tailorAiConsent.value = false
  tailorResult.value = item.optimization?.level === tailorLevel.value ? copyJson(item.optimization.result) : null
}

async function openTailored() {
  showTailored.value = true
  try {
    tailoredResumes.value = await platformStore.listTailorDrafts()
    if (selectedTailor.value) {
      selectedTailor.value = tailoredResumes.value.find(item => item.id === selectedTailor.value.id) || null
    }
  } catch (error) {
    errorMessage.value = error.message
  }
}

async function runTailorOptimization() {
  if (!selectedTailor.value?.description || tailoring.value) return
  tailoring.value = true
  errorMessage.value = ''
  try {
    const fingerprint = tailorFingerprint({ resume, jd: selectedTailor.value.description, level: tailorLevel.value })
    if (selectedTailor.value.optimization?.fingerprint === fingerprint) {
      tailorResult.value = copyJson(selectedTailor.value.optimization.result)
      tailorConfirmations.value = {}
      notify('已载入相同 JD 与简历的本地优化缓存')
      return
    }
    const settings = await platformStore.getSettings()
    const result = await optimizeResumeForJd({ resume, jd: selectedTailor.value.description, level: tailorLevel.value, settings })
    tailorResult.value = result
    tailorConfirmations.value = {}
    const updated = await platformStore.updateTailorDraft(selectedTailor.value.id, {
      optimization: { fingerprint, level: tailorLevel.value, result: copyJson(result), created_at: new Date().toISOString() },
    })
    selectedTailor.value = updated
    const index = tailoredResumes.value.findIndex(item => item.id === updated.id)
    if (index >= 0) tailoredResumes.value[index] = updated
    notify(`已生成 ${result.suggestions.length} 条优化建议`)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    tailoring.value = false
  }
}

function suggestionLabel(suggestion) {
  const labels = { summary: '个人简介', experience: '工作经历', projects: '项目经历', skills: '专业技能', evaluation: '自我评价' }
  const fieldLabels = { content: '内容', description: '描述', technologies: '技术关键词' }
  return `${labels[suggestion.section] || suggestion.section} · ${fieldLabels[suggestion.field] || suggestion.field}`
}

function formatSuggestionValue(value) {
  return Array.isArray(value) ? value.join(' / ') : String(value || '')
}

function applySuggestion(index) {
  const suggestion = tailorResult.value?.suggestions?.[index]
  if (!suggestion || suggestion.applied) return
  try {
    applyTailorSuggestion(resume, suggestion, Boolean(tailorConfirmations.value[index]))
    suggestion.applied = true
    markDirty()
    activeId.value = suggestion.section
    notify('优化建议已应用，可在编辑器中继续调整')
  } catch (error) {
    errorMessage.value = error.message
  }
}

function applyReadySuggestions() {
  try {
    let applied = 0
    for (let index = 0; index < (tailorResult.value?.suggestions?.length || 0); index += 1) {
      const suggestion = tailorResult.value.suggestions[index]
      if (suggestion.applied || (suggestion.needs_confirmation && !tailorConfirmations.value[index])) continue
      applyTailorSuggestion(resume, suggestion, Boolean(tailorConfirmations.value[index]))
      suggestion.applied = true
      applied += 1
    }
    if (applied) {
      markDirty()
      notify(`已应用 ${applied} 条优化建议`)
    } else notify('没有可应用的建议，请先确认标记为新增的内容')
  } catch (error) {
    errorMessage.value = error.message
  }
}

function updatePreviewScale() {
  const width = previewHost.value?.clientWidth || 720
  previewScale.value = Math.max(.42, Math.min(.92, (width - 56) / 794))
}

const handleEditorOpen = () => nextTick(updatePreviewScale)

watch(tailorLevel, () => {
  tailorConfirmations.value = {}
  tailorResult.value = selectedTailor.value?.optimization?.level === tailorLevel.value
    ? copyJson(selectedTailor.value.optimization.result)
    : null
})

onMounted(() => {
  load()
  document.addEventListener('resume-editor-open', handleEditorOpen)
  resizeObserver = new ResizeObserver(updatePreviewScale)
  if (previewHost.value) resizeObserver.observe(previewHost.value)
})
onBeforeUnmount(() => { resizeObserver?.disconnect(); document.removeEventListener('resume-editor-open', handleEditorOpen); clearTimeout(successTimer) })
</script>
