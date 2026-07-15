<script setup>
import { Icon } from '@iconify/vue'
import BrandLogo from '../components/BrandLogo.vue'
import ThemeToggle from '../components/ThemeToggle.vue'

defineProps({ theme: { type: String, required: true } })
defineEmits(['toggle-theme'])

const releases = [
  {
    version: 'V0.0.8',
    date: '2026-07-15',
    summary: '用四平台状态卡和自动心跳替代手动检查登录。',
    groups: [
      {
        title: '登录状态',
        items: [
          '顶部新增四个平台登录状态卡，已登录平台凸出高亮并显示绿色状态点。',
          '未登录平台置灰显示，点击状态卡即可切换当前招聘平台。',
          '启动浏览器调整为启动登录，并移除前端手动检查登录入口。',
          '每 15 秒执行一次轻量四平台心跳，只在登录状态变化时广播。',
          '完善日间、夜间和移动端状态卡布局。',
        ],
      },
    ],
  },
  {
    version: 'V0.0.7',
    date: '2026-07-15',
    summary: '在统一浏览器和岗位模型中接入四个招聘平台。',
    groups: [
      {
        title: '多平台求职',
        items: [
          '新增智联招聘、猎聘和前程无忧登录、搜索、筛选、岗位入库与单岗位投递。',
          '四个平台复用一个可见浏览器上下文，并按平台页面和域名隔离登录态。',
          '岗位中心、统一 API 和 MyJob CLI 增加平台选择、来源展示与平台筛选。',
          '登录检测必须出现明确账号证据，验证码和安全验证保留人工处理。',
          'BOSS 直聘继续负责消息同步和招聘者活跃度筛选。',
        ],
      },
    ],
  },
  {
    version: 'V0.0.6',
    date: '2026-07-15',
    summary: '简化登录注册页面，让认证操作保持单一焦点。',
    groups: [
      {
        title: '登录与注册',
        items: [
          '登录与注册页面调整为居中的单一认证卡片，移除额外产品介绍。',
          '保留账号规则、密码显隐、状态提示、已登录账号处理和管理员独立入口。',
          '优化日间与夜间主题、移动端布局、表单对比度和键盘焦点状态。',
        ],
      },
    ],
  },
  {
    version: 'V0.0.5',
    date: '2026-07-14',
    summary: '统一 MyJob 的 Python CLI 包目录命名。',
    groups: [
      {
        title: '项目结构',
        items: [
          'Python CLI 包目录统一命名为 MyJob_cli。',
          '同步更新项目入口点、构建配置、开发文档与验证命令。',
          'CLI 命令统一命名为 myjob，并移除旧环境变量和 Cookie 命名。',
        ],
      },
    ],
  },
  {
    version: 'V0.0.4',
    date: '2026-07-14',
    summary: '建立独立 MyJob 仓库，并按当前产品能力重写项目文档。',
    groups: [
      {
        title: '项目文档',
        items: [
          'MyJob 仓库调整为独立项目，不再保留其他仓库的关联说明。',
          'README 按当前 Vue、FastAPI、认证、管理员后台、简历中心和自动化流程完整重写。',
          '更新安装地址、开发约定和项目介绍，并移除 CLI 中失效的旧本地路径。',
        ],
      },
    ],
  },
  {
    version: 'V0.0.3',
    date: '2026-07-14',
    summary: '修复简历中心部分控件未正确切换到日间样式的问题。',
    groups: [
      {
        title: '简历中心主题',
        items: [
          '修复日间主题选择器未命中简历编辑器控件的问题。',
          '统一输入框、照片上传、字号与行距设置、经历卡片和缩放控件的日间配色。',
          '补齐简历模板与定制简历弹窗的日间主题，同时保持夜间模式不变。',
        ],
      },
    ],
  },
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
