<script setup>
import { Icon } from '@iconify/vue'
import BrandLogo from '../components/BrandLogo.vue'
import ThemeToggle from '../components/ThemeToggle.vue'

defineProps({ theme: { type: String, required: true } })
defineEmits(['toggle-theme'])

const capabilities = [
  {
    icon: 'mdi:filter-variant',
    title: '岗位自动筛选',
    text: '围绕职位要求、经验与偏好整理候选岗位，把注意力留给更值得跟进的机会。',
    className: 'marketing-capability-featured',
  },
  {
    icon: 'mdi:map-marker-radius-outline',
    title: '目标城市聚焦',
    text: '按城市与求职方向组织搜索条件，减少跨地区浏览带来的重复操作。',
  },
  {
    icon: 'mdi:message-processing-outline',
    title: 'HR 沟通衔接',
    text: '统一梳理沟通节奏与岗位上下文，让每次对话更清楚。',
  },
  {
    icon: 'mdi:file-document-edit-outline',
    title: '简历定向投递',
    text: '结合职位描述准备对应简历，再进入投递流程。',
  },
  {
    icon: 'mdi:calendar-check-outline',
    title: '面试邀约跟进',
    text: '集中查看进展与邀约信息，减少重要节点遗漏。',
  },
]

const workflow = [
  { icon: 'mdi:tune-variant', title: '设定方向', text: '明确岗位与城市' },
  { icon: 'mdi:briefcase-search-outline', title: '筛选机会', text: '聚焦匹配岗位' },
  { icon: 'mdi:message-text-outline', title: '推进沟通', text: '保留上下文' },
  { icon: 'mdi:send-outline', title: '完成投递', text: '使用定向简历' },
  { icon: 'mdi:calendar-month-outline', title: '跟进邀约', text: '管理面试节点' },
]
</script>

<template>
  <div class="marketing-shell">
    <header class="marketing-header">
      <a class="marketing-brand" href="/" aria-label="MyJob 首页">
        <BrandLogo />
      </a>

      <nav class="marketing-nav" aria-label="主导航">
        <a href="#capabilities">产品能力</a>
        <a href="/docs">产品文档</a>
        <a href="/changelog">更新日志</a>
      </nav>

      <div class="marketing-actions">
        <ThemeToggle :theme="theme" @toggle="$emit('toggle-theme')" />
        <a class="marketing-button marketing-button-small" href="/login">登录 / 注册</a>
      </div>
    </header>

    <main id="main-content">
      <section class="marketing-hero" aria-labelledby="hero-title">
        <div class="marketing-hero-copy">
          <p class="marketing-eyebrow">把求职流程连成一条清晰路径</p>
          <h1 id="hero-title">找到合适岗位，让下一步自动发生。</h1>
          <p class="marketing-hero-summary">按岗位与目标城市筛选，衔接沟通、简历投递和面试邀约。</p>
          <div class="marketing-hero-actions">
            <a class="marketing-button" href="/register">注册</a>
            <a class="marketing-text-link" href="/docs">
              查看产品文档
              <Icon icon="mdi:arrow-right" aria-hidden="true" />
            </a>
          </div>
        </div>

        <div class="marketing-hero-visual" aria-label="MyJob 自动化求职链路">
          <div class="marketing-visual-brand">
            <BrandLogo compact />
            <span>自动化求职链路</span>
          </div>
          <div class="marketing-route marketing-route-primary">
            <Icon icon="mdi:filter-variant" aria-hidden="true" />
            <span><strong>岗位</strong>匹配方向</span>
          </div>
          <div class="marketing-route marketing-route-secondary">
            <Icon icon="mdi:map-marker-radius-outline" aria-hidden="true" />
            <span><strong>城市</strong>锁定范围</span>
          </div>
          <div class="marketing-route marketing-route-final">
            <Icon icon="mdi:calendar-check-outline" aria-hidden="true" />
            <span><strong>面试</strong>跟进邀约</span>
          </div>
          <div class="marketing-route-line" aria-hidden="true"></div>
        </div>
      </section>

      <section class="marketing-platforms" aria-label="产品对接平台">
        <span class="marketing-platform-label">产品对接平台</span>
        <div class="marketing-platform-list">
          <div><strong>BOSS 直聘</strong><span>已接入</span></div>
          <div><strong>智联招聘</strong><span>已接入</span></div>
          <div><strong>前程无忧</strong><span>已接入</span></div>
          <div><strong>猎聘</strong><span>已接入</span></div>
        </div>
      </section>

      <section id="capabilities" class="marketing-section marketing-capabilities" aria-labelledby="capability-title">
        <div class="marketing-section-heading">
          <h2 id="capability-title">从发现岗位到收到邀约</h2>
          <p>把分散在多个环节的操作放进同一套求职工作流，每一步都能接着上一步继续。</p>
        </div>

        <div class="marketing-capability-grid">
          <article
            v-for="capability in capabilities"
            :key="capability.title"
            class="marketing-capability"
            :class="capability.className"
          >
            <Icon :icon="capability.icon" aria-hidden="true" />
            <div>
              <h3>{{ capability.title }}</h3>
              <p>{{ capability.text }}</p>
            </div>
          </article>
        </div>
      </section>

      <section class="marketing-section marketing-city-focus" aria-labelledby="city-title">
        <div class="marketing-city-copy">
          <h2 id="city-title">先确定去哪里，再决定看什么</h2>
          <p>目标城市与岗位方向共同参与筛选，让搜索结果更贴近真实计划，避免在无关机会里反复切换。</p>
          <a class="marketing-text-link" href="/docs#job-search">
            了解筛选方式
            <Icon icon="mdi:arrow-right" aria-hidden="true" />
          </a>
        </div>
        <div class="marketing-city-visual" aria-hidden="true">
          <div class="marketing-city-orbit marketing-city-orbit-wide"></div>
          <div class="marketing-city-orbit marketing-city-orbit-narrow"></div>
          <Icon icon="mdi:map-marker-path" />
          <span>岗位方向</span>
          <strong>目标城市</strong>
        </div>
      </section>

      <section class="marketing-section marketing-workflow" aria-labelledby="workflow-title">
        <div class="marketing-section-heading">
          <h2 id="workflow-title">一条可以持续推进的求职路径</h2>
          <p>每个环节都有明确输入和下一步，不必在平台、文档与聊天记录之间来回寻找信息。</p>
        </div>
        <ol class="marketing-workflow-list">
          <li v-for="item in workflow" :key="item.title">
            <Icon :icon="item.icon" aria-hidden="true" />
            <div>
              <h3>{{ item.title }}</h3>
              <p>{{ item.text }}</p>
            </div>
          </li>
        </ol>
      </section>

      <section class="marketing-section marketing-cta" aria-labelledby="cta-title">
        <div>
          <h2 id="cta-title">准备好开始更有条理地找工作了吗？</h2>
          <p>创建账户后再连接招聘平台，并从你的岗位与城市目标开始。</p>
        </div>
        <a class="marketing-button" href="/register">注册</a>
      </section>
    </main>

    <footer class="marketing-footer">
      <a class="marketing-brand" href="/" aria-label="MyJob 首页">
        <BrandLogo />
      </a>
      <p>把求职过程整理成可以持续推进的工作流。</p>
      <nav aria-label="页脚导航">
        <a href="#capabilities">产品能力</a>
        <a href="/docs">产品文档</a>
        <a href="/changelog">更新日志</a>
      </nav>
    </footer>
  </div>
</template>
