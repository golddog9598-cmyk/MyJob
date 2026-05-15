# 招聘网站爬虫

每天自动扫智联招聘，按条件筛岗位，生成日报。

默认搜 AI 相关岗（薪资15-25K、经验1-3年、本科以上），你也可以改成搜别的。

## 它能干啥

- 每天定时跑，不用管它
- 搜出来的岗位会按技能自动分类（编程语言、框架、数据库……）
- 生成 Markdown 日报，一眼看清今天有啥合适的
- 可以存 MySQL，方便以后翻历史数据
- 所有条件都能调：搜什么、多少钱、干几年、要不要本科

## 怎么用

```bash
# 装依赖
pip install -r requirements.txt
playwright install chromium

# 跑一次
python scraper.py

# 搜别的岗位
python scraper.py --keywords "Java,Go,Python"

# 改薪资范围
python scraper.py --salary-min 20 --salary-max 35

# 不存数据库
python scraper.py --no-db
```

想每天自动跑，加条 crontab：

```bash
crontab -e
# 每天早上 9:30 跑
30 9 * * * cd /home/yourname/ai-job-radar && python scraper.py
```

## 配置

除了命令行参数，也可以写 `config.yaml`：

```yaml
output_dir: ./reports
keywords:
  - AI应用开发
  - 人工智能工程师
filters:
  salary_min: 15
  salary_max: 25
  experience_min: 1
  experience_max: 3
  education: bachelor
database:
  password: ${DB_PASSWORD}
```

数据库密码用环境变量，别写死在文件里。

## 输出长啥样

跑完会在 `reports/` 目录下生成一个 Markdown 文件，比如 `招聘日报_2026-05-15.md`，里面列了今天的岗位、薪资、公司、技能标签。

## 原理

```
Playwright 打开浏览器 → 访问智联招聘 → 解析页面 → 按条件过滤 → 生成日报
```

Playwright 是个浏览器自动化工具，用它打开招聘网站就跟真人访问一样，不用处理验证码。

## 注意事项

- 别爬太狠，智联也不容易
- 只供个人求职参考，别拿来干别的
- 网站改版可能导致解析失效，到时提 issue 就行
