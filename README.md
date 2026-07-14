<div align="center">

# MyJob

### AI 驱动的 BOSS 直聘智能求职助手 · Web 控制台 + CLI

> 60+ 城市搜索 · 翻页扫描批量投递 · AI 接管聊天 · 自动交换微信/简历  
> 简历优化 · 沟通建议 · HR 真实姓名/法人识别 · LLM 智能联动  
> Web 端日常操作 · CLI 端供 AI Agent 调用

<br>

[![Python](https://img.shields.io/badge/Python-≥3.10-3776AB?logo=python&logoColor=white&style=for-the-badge)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![CLI](https://img.shields.io/badge/CLI-18_Commands-ec4899?style=for-the-badge)](#-cli-命令)
[![Web](https://img.shields.io/badge/Web-Dark_UI-8b5cf6?style=for-the-badge)](#-web-控制台)
[![AI](https://img.shields.io/badge/AI-DeepSeek%20%7C%20OpenRouter%20%7C%20MiMo-3b82f6?style=for-the-badge)](#-ai-模型配置)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen?style=for-the-badge)](https://github.com/lake121380-source/lakejobai-job-radar/pulls)

<br>

[**快速开始**](#-快速开始) · [**Web 控制台**](#-web-控制台) · [**CLI 命令**](#-cli-命令) · [**核心能力**](#-核心能力) · [**AI 配置**](#-ai-模型配置) · [**API**](#-api-端点参考) · [**排障**](#-诊断与排障) · [**架构**](#-技术架构)

<br>

```
$ lakejob search "AI Agent" --city 广州 --welfare "双休,五险一金"
$ lakejob scan-apply --max-pages 5
$ lakejob conversations
```

</div>

---

## ⚠️ 合规边界

| | 边界 |
|---|------|
| ✅ | 仅用于**个人账号**求职辅助 |
| ✅ | 每日投递有**上限**（默认 15 条，可调） |
| ✅ | 风控触发时**自动冷却退避** |
| ❌ | 不得批量注册、商业采集、规避风控 |
| ❌ | 触发风控时立即停止自动化，回平台手动操作 |

---

## 为什么用 MyJob

| 传统流程 | MyJob |
|----------|---------------------|
| 打开网页逐个搜索 | `lakejob search` 一行搜全国 |
| 手动翻页看薪资 | 福利筛选一键过滤双休五险一金 |
| 翻 5 页找 1 个合适的 | 「翻 5 页一键投递」自动扫描多页 |
| 看到重复公司还投递 | 公司去重 + 中缀/后缀变体模糊匹配 |
| 不活跃 HR 的邀请浪费每日上限 | HR 活跃度抓取 + 自动跳过长期不活跃 |
| 逐一点「立即沟通」 | 一键批量投递 + 进度条 + 取消按钮 |
| 时刻盯手机回复 HR | AI 自动接管聊天（2-4 句/人格化） |
| HR 要微信/简历手动发 | 触发自动识别 + 走 BOSS 安全通道 |
| 忘了跟谁聊过什么 | Web 控制台全记录 + 投递漏斗 |
| 不会写招呼语 | 智能模式：AI 读 JD + 简历优化 → 3 痛点 + 效果付费话术 |
| 不知道 HR 要聊啥 | AI 沟通建议：冰破话题 / 避雷 / 跟进 / 引导面试 |
| 简历海投没回应 | AI 简历优化：JD 匹配差距 + 项目改写示例 |

**Web 控制台** 适合日常操作，**CLI** 适合 AI Agent / 脚本调用。两套界面共用同一套后端、同一份数据。

---

## 📦 安装

```bash
git clone https://github.com/lake121380-source/lakejobai-job-radar.git
cd lakejobai-job-radar
pip install -e .              # 含 CLI 入口 lakejob
playwright install firefox    # 浏览器自动化
```

> Windows 平台若 `playwright install` 失败，参阅[诊断与排障](#-诊断与排障)。

---

## 🚀 快速开始

```bash
# 1. 构建独立 Vue 前端
cd resume_ui
npm install
npm run build
cd ..

# 2. 启动后台服务
python boss_app.py --port 8010
# 或 CLI 启动
lakejob server --start --port 8010

# 3. 用户首页打开 https://127.0.0.1:8010
#    普通用户注册或登录后，才能启动 BOSS 浏览器并使用求职功能
#    管理员后台打开 https://127.0.0.1:8010/MyJobaAdmin
#    默认超级管理员 Admin / 123456*，首次登录后必须修改密码

# 4. 配置 AI
#    设置页 → AI 模型配置 → 选平台 → 填 Key → 保存

# 5. 搜索并投递
#    岗位中心 → 选城市 → 输关键词 → 搜索 → 检查后投递
```

前后端职责、认证模型和轻量部署说明见 [`docs/frontend-backend-architecture.md`](docs/frontend-backend-architecture.md)。

首次本地启动会在 `.boss_profile/tls/` 生成自签名证书，浏览器可能显示一次安全提醒。正式部署请通过 `MYJOB_TLS_CERT` 和 `MYJOB_TLS_KEY` 指定受信任证书，或在 Caddy/Nginx 终止 TLS。仅在明确的本地调试场景下可使用 `--http` 关闭 HTTPS。

CLI 极简流程：

```bash
# API 已启用工作台认证时，为当前终端提供已注册用户凭据
set MYJOB_USERNAME=你的用户名
set MYJOB_PASSWORD=你的密码

$ lakejob search "AI Agent" --city 广州 --welfare "双休,五险一金"
$ lakejob scan-apply --max-pages 5     # 翻 5 页扫描投递 + 公司去重 + HR 过滤
$ lakejob apply-batch                  # 投递所有待投递
$ lakejob status                       # 看浏览器+今日统计
```

## 🎯 JD 定制简历与自动求职计划

### 1. 保存主简历

在 Web「简历模板」上传或创建主简历。支持 `DOCX / PDF / TXT / Markdown / HTML / RTF / JSON / ODT`，解析成功后会转换为统一结构并套用用户选择的模板：

```bash
lakejob resume set --file ./resume.md
lakejob resume templates
lakejob resume upload --file ./我的简历.docx --template modern_blue
lakejob resume template ats_classic
lakejob resume export --format docx --output ./主简历.docx
lakejob resume export --format pdf --output ./主简历.pdf
```

主简历是 AI 唯一允许使用的事实来源。系统不会把 JD 中出现、但主简历里没有的技能或经历写进定制稿；生成后还会检查是否出现主简历之外的新数字。

模板库内置 18 套风格，覆盖 ATS 单栏、现代横幅、时间线、双栏、侧栏、管理、技术、产品、运营、数据、学术、校招和一页紧凑等场景。Web 端使用 Vue 3 可视化编辑器，支持个人资料、个人简介、工作经历、教育经历、项目经历、专业技能、自我评价 7 个模块；模块可启用/隐藏、拖拽或按钮排序，工作/教育/项目条目也可拖拽排序。个人资料支持上传 JPG、PNG 或 WebP 照片并填写年龄，所有模板都会显示居中的个人资料和 3:4 照片框，未上传照片时使用占位头像。经历时间通过年份和月份下拉框填写，结束时间可选“至今”，且前后端都会阻止结束时间早于开始时间；工作与项目成果支持无序/有序分点。除手机、邮箱、所在城市、个人主页、微信和年龄外，每个简历文本字段都可单独调整字号与行距；字体、主题色、页边距和模块间距仍按整份简历统一设置。模板库支持按名称或场景搜索、仅看 ATS 友好模板，并使用当前简历生成真实 A4 缩略图和实时预览。切换模板不会改写简历内容，主简历及每份 JD 定制稿都可按当前模板导出为真正的 A4 DOCX、PDF、HTML 或 Markdown。

### 2. 根据 JD 生成可下载的定制简历

Web 岗位卡片点击「定制简历」，或运行：

```bash
lakejob resume tailor --job-url "https://www.zhipin.com/job_detail/..." --output ./定制简历.md
lakejob resume list
```

每个岗位的版本都会保存到 SQLite，并按当前所选模板导出为 DOCX、PDF、Markdown 或可打印 HTML。`needs_review` 表示检测到主简历中没有的新数字，必须核实；建议所有版本投递前人工通读并点击「确认可用」。

### BOSS 登录状态

控制台右上角依次提供「启动浏览器」「检查登录」「登出」「停止」：

- 启动浏览器后会自动验证 BOSS 登录状态，也可随时手动点击「检查登录」。
- 检查结果和登出结果均通过页面中央弹窗提示。
- 「登出」会清除 cookies、站点存储和本地登录状态，但不会停止浏览器或后台服务。
- 未登录时可直接在独立浏览器窗口中扫码，完成后点击「检查登录」。

### 3. 按岗位和城市建立持续求职计划

```bash
# 默认：自动搜索、评分、定制简历，但投递前人工确认
lakejob campaign create \
  --name "AI 工程师-大湾区" \
  --keyword "AI Agent" --keyword "大模型应用开发" \
  --city "深圳" --city "广州" \
  --min-score 65 --max-jobs 10 --start

lakejob campaign list
lakejob campaign run 1
lakejob campaign show 1
lakejob campaign pause 1

# 确实需要全自动投递时，必须同时给出两项显式参数
lakejob campaign create --keyword "Python 后端" --city "深圳" \
  --auto-apply --confirm-auto-apply --start
```

计划运行链路：

```text
岗位 + 城市搜索 → 公司/HR 风控过滤 → 本地简历匹配评分 → JD 定制稿
→ 待确认或自动投递 → AI 接管入站沟通 → HR 回复 → 面试意向
```

- 定时计划只在服务运行、BOSS 浏览器已登录时执行，默认每 24 小时一轮。
- 自动投递仍受每日上限、公司去重、HR 活跃度和平台风控冷却约束。
- 系统会把高意向 HR 标记到「面试意向」，但不会替用户承诺具体面试时间。
- BOSS 的「发简历」按钮发送的是账号当前在线/附件简历。系统生成的 JD 定制文件需要用户确认后自行上传到对应平台，这是为了避免未经核实的内容被自动发送。

---

## 💻 Web 控制台

> 深色科技感（Vercel / Raycast 风格）单文件 SPA，无构建步骤、无外部 CDN。

### 主要功能

- **🔍 岗位搜索** — 60+ 城市分组、薪资/经验/学历/规模/融资阶段多维筛选、福利关键词过滤、批量关键词一行一个
- **🃏 两列卡片视图** — 标题/薪资/公司/城市/状态/HR 活跃度一目了然
  - 🏛 **法人识别**：HR 姓名 == 法人时自动标 `法人直聘`
  - 🏢 公司信息：@公司名 · 规模 · 行业
  - 📍 区域细化：城市 · 区 · 商圈
  - 📝 JD 摘要：前 120 字
  - ⏱ HR 活跃度三色标签（绿/橙/红）
- **🚀 一键投递 / 翻 5 页** — 进度条带 shimmer 扫光动画，可中途取消
- **📊 投递漏斗** — 待投递 → 已投递 → HR 回复 → 面试 4 步可视化
- **💬 微信风格聊天** — 头像气泡布局、AI 代发小角标、未读小红点、顶部「我·AI代发」标签右对齐
- **🧠 AI 三大智能体**：
  - **岗位分析** — 匹配度百分比 + 关键技能 + 差距建议 + 决策（值得投/谨慎/放弃）+ 风险点 + 建议问题
  - **简历优化** — 核心结论 + JD 核心要求 + 匹配差距 + 关键词 + 项目改写示例 + 立即行动清单
  - **沟通建议** — 冰破话题 + 避雷点 + 跟进话术 + 引导面试 + 沟通风格
- **🔄 24h 智能缓存** — 三个 AI 端点均带 24h 持久化缓存，避免重复消耗 token
- **📋 一键复制** — 两个 AI 弹窗均支持「📋 复制」按钮，一键导出为 Markdown 纯文本
- **⚙️ 设置面板** — AI 多平台（DeepSeek/OpenRouter/小米 MiMo/自定义）、招呼语模板/智能模式、HR 不活跃阈值、公司去重开关

### 键盘可访问 & 移动端适配

`:focus-visible` 焦点环、响应式布局（窄屏侧栏自动收起为图标列、岗位卡片单列、统计/漏斗 2 列）。

---

## 🛠️ CLI 命令

安装后即获 `lakejob` 命令，stdout 仅输出 JSON，AI Agent 友好。

### 18 条命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `lakejob search` | 搜索岗位 | `lakejob search "AI Agent" --city 广州 --welfare "双休,五险一金"` |
| `lakejob scan` | 翻页扫描（不投递） | `lakejob scan --max-pages 3` |
| `lakejob scan-apply` | 翻页扫描投递（公司去重 + HR 过滤） | `lakejob scan-apply --max-pages 5` |
| `lakejob status` | 浏览器状态 + 今日统计 | `lakejob status` |
| `lakejob stats` | 投递转化漏斗 | `lakejob stats` |
| `lakejob jobs` | 岗位列表 | `lakejob jobs --status pending --limit 10` |
| `lakejob apply` | 投递单个 | `lakejob apply <job_url>` |
| `lakejob apply-batch` | 批量投递待投递 | `lakejob apply-batch` |
| `lakejob conversations` | HR 会话列表 | `lakejob conversations` |
| `lakejob chat` | 查看聊天记录 | `lakejob chat 1` |
| `lakejob send` | 手动发消息 | `lakejob send 1 --msg "你好"` |
| `lakejob analyze` | AI 分析岗位匹配度 | `lakejob analyze <job_url> --title "AI开发"` |
| `lakejob shortlist` | 候选池增删查 | `lakejob shortlist list` |
| `lakejob login` | 触发扫码登录 | `lakejob login` |
| `lakejob schema` | 输出工具描述 JSON | `lakejob schema` |
| `lakejob doctor` | 环境诊断 | `lakejob doctor` |
| `lakejob version` | 版本号 | `lakejob version` |
| `lakejob server` | 管理后台服务 | `lakejob server --start` |

### 输出格式

```json
{
  "ok": true,
  "command": "search",
  "data": [{ "title": "AI开发", "company": "XX科技", "salary": "20-30K" }],
  "pagination": { "page": 1, "has_more": true, "total": 15 },
  "error": null
}
```

- `stdout` — 仅 JSON
- `stderr` — 日志/进度
- exit `0` 成功，exit `1` 失败

### AI Agent 集成

```bash
# 1. 获取工具清单
$ lakejob schema

# 2. 检查登录
$ lakejob status
# → {"ok": true, "data": {"browser_running": true}}

# 3. 搜索岗位
$ lakejob search "Golang" --city 北京
# → {"ok": true, "data": [...], "total": 23}

# 4. 翻页扫描投递
$ lakejob scan-apply --max-pages 5
```

> 详细集成指南见 [SKILL.md](SKILL.md)

---

## 🌟 核心能力

| 功能 | Web | CLI |
|------|:--:|:--:|
| 🔍 60+ 城市搜索 + 福利筛选 | ✅ | ✅ |
| 🚀 一键批量投递 + 进度条 + 取消 | ✅ | ✅ |
| 📄 翻页扫描投递（默认 5 页） | ✅ | ✅ |
| 🏢 公司去重（中缀/后缀变体模糊匹配） | ✅ | ✅ |
| ⏱ HR 活跃度抓取 + 跳过长期不活跃 | ✅ | ✅ |
| 👤 HR 真实姓名/头衔/活跃度 | ✅ | — |
| 🏛 法人识别 + 法人直聘标签 | ✅ | — |
| 🧠 AI JD 分析（匹配度+技能+差距+决策+风险） | ✅ | ✅ |
| 📋 AI 简历优化（24h 缓存 + 项目改写） | ✅ | — |
| 💬 AI 沟通建议（24h 缓存 + 话题方向） | ✅ | — |
| 🤖 AI 自动回复（多平台模型） | ✅ | — |
| 🔄 LLM 联动（招呼语参考简历优化） | ✅ | — |
| 📱 自动交换微信/简历/电话 | ✅ | — |
| 💬 微信风格聊天界面 | ✅ | — |
| 📊 投递转化漏斗 | ✅ | ✅ |
| 📌 本地候选池 | ✅ | ✅ |
| 🩺 环境诊断 | — | ✅ |
| 🧩 AI Agent 集成 | — | ✅ |

---

## 🤖 AI 模型配置

设置页选平台 → 自动填 Base URL 和模型列表 → 填 Key 即可。

| 平台 | 自动填充 |
|------|:--:|
| DeepSeek | ✅ |
| OpenRouter | ✅ |
| 小米 MiMo | ✅ |
| 自定义（任意 OpenAI 兼容 API） | — |

### 🧠 三个 AI 智能体

#### 1️⃣ AI 岗位分析 — `/api/jobs/analyze`

基于 JD + 简历摘要 + 公司信息，输出：

```json
{
  "match_score": 75,
  "summary": "匹配度高",
  "decision": "worth_apply",
  "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
  "missing_skills": ["Kubernetes"],
  "reasons": ["技能栈高度吻合", "公司处于上升期"],
  "risks": ["薪资可能低于预期", "加班强度需确认"],
  "suggested_questions": ["团队规模？", "晋升机制？"]
}
```

#### 2️⃣ AI 简历优化 — `/api/jobs/optimize-resume`

针对 JD 给出 6 大维度优化建议，**24h 缓存 + DB 持久化**：

- 💡 一句话核心结论
- 🎯 JD 核心要求
- ⚠ 匹配差距（最需要补的方向）
- ✏️ 优化建议（按模块分卡片，含 当前/建议/原因）
- 🔑 建议加入的关键词
- 📝 项目改写示例
- ✅ 立即行动清单

#### 3️⃣ AI 沟通建议 — `/api/jobs/chat-suggestion`

针对 HR 个性化沟通策略，**24h 缓存 + DB 持久化**：

- 💬 冰破话题（5 个不同角度 + 怎么聊 + 具体话术）
- ⚠ 踩雷避坑（千万别说的）
- 📌 跟进话术（对方不回复怎么优雅跟进）
- ✅ 引导面试（如何把对话推向面试）
- 💡 沟通风格（语气/态度建议）

#### 智能招呼语联动

打招呼语生成时**自动注入简历优化结果**，使首条招呼语紧扣 JD 与简历匹配点：

```
[之前] 你好，我对贵公司的 AI Agent 岗位很感兴趣...
[联动后] 你好，我方向是 AI Agent——LLM 工具调用、RAG 检索、Agent 编排...（参考简历优化结果中的关键词）
```

### 智能招呼语模式

切到「智能（AI 读 JD）」后，AI 会根据岗位描述自动生成 3 个痛点 + 效果付费话术，例如：

> 老板，我的方向是【AI 运营】方向——【智能客服搭建】、【私域 SOP 沉淀】、【数据看板搭建】，按效果付费，做不到不拿底薪，聊聊？

提示词可在设置页「智能跟进 Prompt」自定义。

---

## 📁 项目结构

```
├── boss_app.py              # FastAPI Web 后端
├── boss_automation.py       # 自动化投递 + 聊天 + 发简历/微信
├── boss_company.py          # 公司画像聚合
├── boss_firefox.py          # BOSS 搜索 + 详情 XHR + 福利筛选
├── boss_geo.py              # 城市/区/规模 BOSS 编码映射
├── boss_replier.py          # AI 回复 + 招呼语 + 简历优化上下文
├── boss_state.py            # SQLite 数据持久化
├── pyproject.toml           # 打包 + CLI 入口
├── lakejob_cli/             # CLI (18 命令)
│   ├── cli.py / client.py / output.py / schema.json
├── static/dashboard.html    # Web 前端 (单文件 SPA)
├── interview/               # 面试问答子模块
├── SKILL.md                 # Agent 集成指南
├── CHANGELOG.md             # 版本变更
├── CHANGES.md               # 优化变更说明
└── LICENSE
```

---

## 🔌 API 端点参考

<details>
<summary>点击展开完整 API 列表</summary>

### 岗位

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/jobs/search` | 搜索岗位 |
| `GET` | `/api/jobs` | 岗位列表（支持 `?status=&limit=`） |
| `POST` | `/api/jobs/apply` | 投递单个 |
| `POST` | `/api/jobs/apply-batch` | 批量投递待投递 |
| `POST` | `/api/jobs/scan-and-apply` | 翻页扫描投递 |
| `POST` | `/api/jobs/{id}/skip` | 跳过 |
| `POST` | `/api/jobs/analyze` | AI JD 分析（带 decision/risks） |
| `POST` | `/api/jobs/optimize-resume` | AI 简历优化（24h 缓存） |
| `POST` | `/api/jobs/chat-suggestion` | AI 沟通建议（24h 缓存） |

### 候选池

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/shortlists` | 候选池 |
| `POST` | `/api/shortlists` | 添加 |
| `DELETE` | `/api/shortlists/{id}` | 取消 |

### 聊天

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/conversations` | 会话列表 |
| `GET` | `/api/conversations/{id}/messages` | 消息记录 |
| `POST` | `/api/conversations/{id}/send` | 手动发消息 |
| `POST` | `/api/conversations/{id}/sync` | 同步会话 |
| `POST` | `/api/conversations/{id}/pause` | 暂停 AI 自动回复 |
| `POST` | `/api/conversations/{id}/resume` | 开启 AI 自动回复 |
| `GET` | `/api/wechat-exchanges` | 已交换的微信记录 |

### 系统

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/status` | 浏览器状态 |
| `GET` | `/api/stats` | 投递漏斗 |
| `GET` | `/api/doctor` | 环境诊断 |
| `GET` | `/api/settings` | 读取设置 |
| `PUT` | `/api/settings` | 更新设置 |
| `POST` | `/api/system/start` | 启动浏览器 |
| `POST` | `/api/system/check-login` | 验证 BOSS 登录状态 |
| `POST` | `/api/system/logout` | 清除 BOSS 会话（保留浏览器运行） |
| `POST` | `/api/system/stop` | 停止 |
| `POST` | `/api/system/relogin` | 重新扫码 |
| `POST` | `/api/system/heartbeat` | 心跳检测 |
| `POST` | `/api/system/navigate-chat` | 导航到聊天页 |
| `WS` | `/ws` | 实时推送 |

</details>

---

## 🏗️ 技术架构

```
Web 浏览器                  FastAPI                     BOSS 直聘
┌──────────┐  WebSocket   ┌──────────────┐  Playwright  ┌──────────────┐
│dashboard │◄────────────►│  boss_app.py  │◄────────────►│  zhipin.com   │
│  .html   │  HTTP/REST   │               │  Firefox     │               │
└──────────┘              │  automation   │              └──────────────┘
                          │  replier ─────────────────►│  AI API       │
                          │  state ─────► SQLite       └──────────────┘
                          └──────────────┘
                  lakejob CLI ──► HTTPS 客户端 ──► FastAPI
```

| 层级 | 选型 |
|------|------|
| 后端 | Python ≥ 3.10 + FastAPI |
| 浏览器 | Playwright + Firefox 持久化 Profile |
| 数据库 | SQLite (WAL) |
| 前端 | 单文件 HTML + Vanilla JS + WebSocket（无构建无 CDN） |
| CLI | Click + httpx + JSON 信封 |
| AI | OpenAI Chat Completions 兼容 API |
| 风控绕开 | `page.evaluate(fetch)` 浏览器内调用，自动带 cookie/referer |

---

## 🔧 诊断与排障

```bash
lakejob doctor             # 一键诊断（环境/浏览器/DB/网络）
lakejob status             # 浏览器运行状态
```

<details>
<summary>常见问题</summary>

| 问题 | 解决 |
|------|------|
| 端口被占用 | `lakejob server --port 8015` |
| 浏览器启动失败 | `playwright install firefox --force` |
| 登录过期 | Web 设置页点「重新扫码登录」 |
| 搜索返回 500 | 浏览器未启动，先去设置页启动 |
| 搜索触发风控（code 37） | 浏览器内 fetch 已自动带 cookie；如仍触发，浏览器手动完成安全验证 |
| 卡片不显示法人 | 搜索后批量补抓逻辑已加；详情 API 中无 `legalPerson` 时会尝试公司页抓取 |
| AI 不回复 | 检查设置页 AI Key 是否保存 / Base URL 是否可访问 |
| HR 要简历无法自动点击 | `send_resume` 已改用 `innerText` 精确匹配 + 多重兜底 |
| 投递全部被跳过 | 检查公司去重/HR 不活跃过滤是否过严 |
| 重复发同一家公司 | 自动去重已开启，仍出现请检查公司名是否被规范化 |

</details>

---

## ⚙️ 配置

### Web 设置项

| 设置 | 说明 |
|------|------|
| 招呼语模板 | 投递时自动发送（`{job_title}` 占位） |
| 招呼语模式 | 固定模板 / 智能（AI 读 JD） |
| AI 回复风格 | professional / casual / enthusiastic |
| 每日投递上限 | 1-30，默认 15 |
| 回复间隔 | 30-120 秒随机延迟 |
| 会话冷却 | 同一会话回复最小间隔（秒） |
| 搜索关键词 | 一行一个，批量搜索按序遍历 |
| 简历摘要 | AI 生成回复素材 + 简历优化依据 |
| HR 不活跃阈值 | 超过 N 天未活跃自动跳过（默认 7） |
| 公司去重 | 同一公司只投递一次（默认开启） |
| AI 配置 | 平台 / Key / Base URL / 模型 |

### 数据库表

启动时自动建表（`ALTER TABLE` 兼容旧库）：

- `applications` — 投递记录（含 `hr_active` / `hr_active_label` / `hr_active_days` / `company_id` / `company_size` / `industry` / `legal_rep` / `is_boss` / `area_district` / `business_district` / `optimize_result` / `optimize_at` / `chat_suggestion_result` / `chat_suggestion_at`）
- `conversations` — HR 会话（含 `hr_wechat` / `wechat_shared_at` / `interest_level`）
- `messages` — 聊天消息
- `companies` — 公司信息缓存（24h 复用）
- `shortlists` — 候选池
- `daily_stats` — 每日统计
- `settings` — KV 配置

---

## 🔒 隐私与数据

- 所有数据存储在本地 `.boss_profile/boss_state.db`，**不上传任何服务器**
- `.boss_profile/` 已在 `.gitignore` 中，请勿提交
- AI Key 仅存储在本地 `settings` 表，**请勿在 issue / 截图里贴出**

---

## ⚠️ 免责声明

本项目仅供学习交流和个人求职辅助。使用请遵守 BOSS 直聘用户协议。因不当使用产生的后果由使用者自行承担。

---

## 📋 版本与已知限制

当前版本（v4.1）：
- 后端：完整支持 3 个 AI 端点（`/api/jobs/analyze`、`/api/jobs/optimize-resume`、`/api/jobs/chat-suggestion`），均带 24h DB 缓存
- 前端 dashboard.html：合并 PR #3 后整体重写，**「简历优化」「沟通建议」弹窗 UI 暂未对接**，需自行调用 API 或后续补回
- `boss_geo.py`（中文区名→BOSS code 映射）保留但未被搜索流程引用（PR 端用前端直接传 code 的新方式）
- 详见 [CHANGELOG.md](CHANGELOG.md) 的 v4.1 节

---

## 📑 许可证

[MIT](LICENSE)

## 🙏 致谢

- [can4hou6joeng4/boss-agent-cli](https://github.com/can4hou6joeng4/boss-agent-cli) — 设计灵感来源
- [Playwright](https://playwright.dev/) · [FastAPI](https://fastapi.tiangolo.com/) · [Click](https://click.palletsprojects.com/)
