# AI Job Radar · AI 岗位雷达 🎯

> 每天自动扫描招聘网站，精准筛选适合你的 AI 岗位。
> 无需验证码、无需登录、开箱即用。

## ✨ 特性

- 🤖 **全自动化** — 设置一次，每天自动运行
- 🎯 **精准过滤** — 薪资15-25K · 经验1-3年 · 本科及以上
- 📊 **智能分类** — 自动分析技能要求，生成类别统计
- 📄 **Markdown日报** — 清晰展示每日新岗位
- 🗄️ **数据持久化** — MySQL/SQLite，支持按日查询和趋势分析
- 🔌 **零额外配置** — 一行命令安装，一行命令运行

## 🚀 快速开始

```bash
# 1. 安装
pip install -r requirements.txt
playwright install chromium

# 2. 运行（一次）
python scraper.py

# 3. 设置定时任务（每天9:30自动跑）
crontab -e
# 添加：30 9 * * * cd /path/to/ai-job-radar && python scraper.py
```

## 🔧 自定义过滤

```bash
# 搜索特定关键词
python scraper.py --keywords "大模型,AI Agent,深度学习"

# 调整薪资范围
python scraper.py --salary-min 20 --salary-max 35

# 不存数据库，只生成日报
python scraper.py --no-mysql
```

## 📋 输出示例

运行后会生成：
- `reports/AI应用开发岗位日报_2026-05-15.md` — 日报文件
- MySQL数据库（可选）— 历史数据可查询

## 🏗️ 技术架构

```
Playwright → 智联招聘 → DOM解析 → 过滤引擎 → Markdown + MySQL
```

- **Playwright**: 浏览器自动化，无需验证码即可获取页面
- **BeautifulSoup**: HTML解析，提取岗位卡片
- **分类引擎**: 10+类技能自动匹配（编程语言、AI框架、大模型等）
- **MySQL/SQLite**: 持久化存储，支持历史趋势分析

## ⚠️ 免责声明

本项目仅用于个人学习、研究和求职辅助。数据来源于公开可访问的招聘网站页面，请合理使用，不要对目标网站造成负担。
