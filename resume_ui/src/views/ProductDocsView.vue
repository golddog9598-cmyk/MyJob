<script setup>
import { Icon } from '@iconify/vue'
import BrandLogo from '../components/BrandLogo.vue'
import ThemeToggle from '../components/ThemeToggle.vue'

defineProps({ theme: { type: String, required: true } })
defineEmits(['toggle-theme'])

const documentSections = [
  { id: 'quick-start', label: '快速开始' },
  { id: 'account', label: '账户与安全' },
  { id: 'platforms', label: '连接招聘平台' },
  { id: 'job-search', label: '岗位与城市筛选' },
  { id: 'resume', label: '简历与投递' },
  { id: 'communication', label: '沟通与邀约' },
]
</script>

<template>
  <div class="marketing-shell marketing-subpage">
    <header class="marketing-header">
      <a class="marketing-brand" href="/" aria-label="MyJob 首页">
        <BrandLogo />
      </a>
      <nav class="marketing-nav" aria-label="主导航">
        <a href="/#capabilities">产品能力</a>
        <a class="is-current" href="/docs" aria-current="page">产品文档</a>
        <a href="/changelog">更新日志</a>
      </nav>
      <div class="marketing-actions">
        <ThemeToggle :theme="theme" @toggle="$emit('toggle-theme')" />
        <a class="marketing-button marketing-button-small" href="/login">登录 / 注册</a>
      </div>
    </header>

    <main id="main-content" class="marketing-docs">
      <header class="marketing-docs-intro">
        <p class="marketing-eyebrow">产品文档</p>
        <h1>了解 MyJob 的工作方式</h1>
        <p>从创建账户到连接招聘平台，按顺序完成设置并开始管理求职流程。</p>
        <span class="marketing-version">当前版本 V0.0.4</span>
      </header>

      <div class="marketing-docs-layout">
        <aside class="marketing-docs-sidebar" aria-label="文档目录">
          <nav>
            <a v-for="section in documentSections" :key="section.id" :href="`#${section.id}`">{{ section.label }}</a>
          </nav>
        </aside>

        <article class="marketing-docs-content">
          <section id="quick-start">
            <h2>快速开始</h2>
            <p>访问首页右上角的注册入口，完成账户创建并登录。进入工作台后，先检查招聘平台登录状态，再配置岗位和城市条件。</p>
            <ol class="marketing-docs-steps">
              <li><strong>注册并登录 MyJob</strong><span>业务功能只对已登录用户开放。</span></li>
              <li><strong>连接 BOSS 直聘</strong><span>启动浏览器并在 BOSS 直聘完成登录。</span></li>
              <li><strong>设置求职目标</strong><span>选择岗位方向、目标城市和筛选条件。</span></li>
              <li><strong>检查后再执行</strong><span>确认岗位、沟通内容和简历版本符合预期。</span></li>
            </ol>
          </section>

          <section id="account">
            <h2>账户与安全</h2>
            <p>MyJob 账户用于保护工作台和业务接口。请使用符合页面规则的独立密码，不要与招聘平台共用密码。</p>
            <div class="marketing-docs-note">
              <Icon icon="mdi:shield-key-outline" aria-hidden="true" />
              <p><strong>安全建议</strong>退出公共设备前，请同时退出招聘平台和 MyJob 账户。</p>
            </div>
          </section>

          <section id="platforms">
            <h2>连接招聘平台</h2>
            <p>当前已接入 BOSS 直聘。智联招聘、前程无忧和猎聘处于规划阶段，将在后续版本逐步接入。</p>
            <p>使用 BOSS 直聘时，点击工作台的启动浏览器按钮，等待页面打开并完成登录。随后使用检查登录确认状态，再开始岗位操作。</p>
          </section>

          <section id="job-search">
            <h2>岗位与城市筛选</h2>
            <p>先填写目标城市，再补充岗位关键词、经验要求和其他偏好。更具体的条件有助于减少无关结果，但条件过多也可能缩小可选范围。</p>
            <div class="marketing-docs-checklist">
              <span><Icon icon="mdi:check-circle-outline" aria-hidden="true" />目标城市</span>
              <span><Icon icon="mdi:check-circle-outline" aria-hidden="true" />岗位关键词</span>
              <span><Icon icon="mdi:check-circle-outline" aria-hidden="true" />经验与方向</span>
              <span><Icon icon="mdi:check-circle-outline" aria-hidden="true" />结果复核</span>
            </div>
          </section>

          <section id="resume">
            <h2>简历与投递</h2>
            <p>在简历中心维护基础信息、经历和技能，选择适合的模板。面向具体岗位时，先根据职位描述检查关键词与经历表达，再导出和投递。</p>
            <p>自动生成内容应由用户确认。请确保时间、项目成果、联系方式和个人信息真实准确。</p>
          </section>

          <section id="communication">
            <h2>沟通与邀约</h2>
            <p>与 HR 沟通前确认岗位上下文和简历版本。收到面试邀约后，及时核对时间、方式、联系人和岗位名称，并在计划中继续跟进。</p>
            <p>招聘平台界面和规则可能变化，具体操作以平台当前页面与服务条款为准。</p>
          </section>
        </article>
      </div>
    </main>

    <footer class="marketing-footer">
      <a class="marketing-brand" href="/" aria-label="MyJob 首页">
        <BrandLogo />
      </a>
      <p>文档会随产品能力持续更新。</p>
      <nav aria-label="页脚导航">
        <a href="/">首页</a>
        <a href="/docs">产品文档</a>
        <a href="/changelog">更新日志</a>
      </nav>
    </footer>
  </div>
</template>
