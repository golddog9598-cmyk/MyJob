<script setup>
import { Icon } from '@iconify/vue'
import BrandLogo from '../components/BrandLogo.vue'
import ThemeToggle from '../components/ThemeToggle.vue'

defineProps({ theme: { type: String, required: true } })
defineEmits(['toggle-theme'])

const releases = [
  {
    version: 'V0.0.2',
    date: '2026-07-14',
    summary: '修复首页认证入口和登录状态下的路由行为。',
    groups: [
      {
        title: '账户入口',
        items: [
          '首页、产品文档和更新日志统一使用一个“登录 / 注册”按钮。',
          '点击认证入口后始终进入登录注册页面，不再因已有会话直接跳走。',
          '已有会话会显示当前账号，可直接进入工作台或退出后切换账号。',
        ],
      },
    ],
  },
  {
    version: 'V0.0.1',
    date: '首个版本',
    summary: '建立 MyJob 的账户、求职工作台与基础管理能力。',
    groups: [
      {
        title: '账户与访问',
        items: [
          '新增用户注册与登录，未登录用户无法使用业务功能。',
          '新增独立管理员入口和用户状态管理能力。',
          '增加登录会话、在线状态与基础活跃数据记录。',
        ],
      },
      {
        title: '求职工作流',
        items: [
          '整合岗位中心、求职计划、沟通中心和设置入口。',
          '支持启动浏览器、检查 BOSS 直聘登录状态与退出。',
          '围绕岗位和目标城市组织自动化筛选流程。',
        ],
      },
      {
        title: '简历能力',
        items: [
          '新增可编辑简历模板与模块排序。',
          '支持经历条目、时间范围、字体与排版设置。',
          '支持面向职位描述准备定向简历。',
        ],
      },
      {
        title: '体验与性能',
        items: [
          '完成 Vue 前端工作台的第一阶段重构。',
          '采用缓存、低频心跳与事件刷新减少服务端压力。',
          '增加日间与夜间界面模式。',
        ],
      },
    ],
  },
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
        <a href="/docs">产品文档</a>
        <a class="is-current" href="/changelog" aria-current="page">更新日志</a>
      </nav>
      <div class="marketing-actions">
        <ThemeToggle :theme="theme" @toggle="$emit('toggle-theme')" />
        <a class="marketing-button marketing-button-small" href="/login">登录 / 注册</a>
      </div>
    </header>

    <main id="main-content" class="marketing-changelog">
      <header class="marketing-changelog-intro">
        <p class="marketing-eyebrow">更新日志</p>
        <h1>MyJob 的每次变化，都有记录</h1>
        <p>这里汇总功能新增、体验调整和重要修复，帮助你了解当前版本。</p>
      </header>

      <article v-for="release in releases" :key="release.version" class="marketing-release">
        <header class="marketing-release-header">
          <div>
            <h2>{{ release.version }}</h2>
            <span>{{ release.date }}</span>
          </div>
          <p>{{ release.summary }}</p>
        </header>

        <div class="marketing-release-groups">
          <section v-for="group in release.groups" :key="group.title">
            <h3>{{ group.title }}</h3>
            <ul>
              <li v-for="item in group.items" :key="item">
                <Icon icon="mdi:check-circle-outline" aria-hidden="true" />
                <span>{{ item }}</span>
              </li>
            </ul>
          </section>
        </div>
      </article>
    </main>

    <footer class="marketing-footer">
      <a class="marketing-brand" href="/" aria-label="MyJob 首页">
        <BrandLogo />
      </a>
      <p>查看每个版本带来的变化。</p>
      <nav aria-label="页脚导航">
        <a href="/">首页</a>
        <a href="/docs">产品文档</a>
        <a href="/changelog">更新日志</a>
      </nav>
    </footer>
  </div>
</template>
