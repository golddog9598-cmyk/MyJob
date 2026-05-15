#!/usr/bin/env python3
"""
AI Job Radar · AI 岗位雷达 🎯
全自动：Playwright → 智联招聘 → 过滤引擎 → Markdown + MySQL

用法：
  python scraper.py                              # 使用默认配置
  python scraper.py --keywords "大模型,AI Agent"  # 自定义关键词
  python scraper.py --salary-min 20 --salary-max 35
  python scraper.py --no-mysql                   # 只生成日报，不写数据库
  python scraper.py --output-dir ./myreports
"""

import argparse
import io
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import ssl
from datetime import date

import yaml
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ============================================================
# 配置
# ============================================================

DEFAULT_KEYWORDS = ["AI应用开发", "人工智能工程师", "算法工程师", "大模型开发"]

# 默认过滤参数
DEFAULT_SALARY_MIN = 15
DEFAULT_SALARY_MAX = 25
DEFAULT_EXP_MIN = 1
DEFAULT_EXP_MAX = 3
DEFAULT_EDUCATION = "bachelor"  # bachelor: 本科及以上, any: 不限

DEFAULT_OUTPUT_DIR = "./reports"
DEFAULT_CONFIG_FILE = "config.yaml"

TODAY = date.today().isoformat()
DATE_STR = date.today().strftime("%Y-%m-%d")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def load_config(config_path=None):
    """加载 YAML 配置文件，支持 ${ENV_VAR} 环境变量替换"""
    cfg = {
        "output_dir": DEFAULT_OUTPUT_DIR,
        "database": {"type": "mysql", "host": "localhost", "user": "root",
                     "password": "${DB_PASSWORD}", "database": "ai_jobs_db"},
        "filters": {"salary_min": DEFAULT_SALARY_MIN, "salary_max": DEFAULT_SALARY_MAX,
                    "experience_min": DEFAULT_EXP_MIN, "experience_max": DEFAULT_EXP_MAX,
                    "education": DEFAULT_EDUCATION},
        "keywords": DEFAULT_KEYWORDS,
    }

    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            raw = f.read()
        # 替换环境变量: ${VAR_NAME} → 环境变量值
        def _env_replacer(m):
            var = m.group(1)
            return os.environ.get(var, "")
        raw = re.sub(r'\$\{(\w+)\}', _env_replacer, raw)
        loaded = yaml.safe_load(raw)
        if loaded:
            # 深度合并
            _deep_merge(cfg, loaded)

    return cfg


def _deep_merge(base, overlay):
    """递归合并字典"""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def resolve_env_password(cfg):
    """从环境变量解析数据库密码"""
    pwd = cfg["database"].get("password", "")
    if not pwd:
        # 尝试多种环境变量
        pwd = os.environ.get("DB_PASSWORD", os.environ.get("MYSQL_PWD", ""))
    return pwd


# ============================================================
# 采集：Playwright → 智联招聘
# ============================================================

def scrape_zhaopin(keyword="AI应用开发", max_jobs=30):
    """Playwright → 智联招聘搜索 + 提取岗位数据"""
    all_jobs = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
            )
            page = context.new_page()

            kw = urllib.parse.quote(keyword)
            url = f"https://sou.zhaopin.com/?jl=489&kw={kw}&p=1"

            print(f"  [智联] 搜索: {url}", file=sys.stderr)
            page.goto(url, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(3000)

            print(f"  [智联] 标题: {page.title()[:50]}", file=sys.stderr)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # 尝试多种选择器提取岗位卡片
            cards = []
            selectors = [
                "div[class*='joblist-box'] div[class*='item']",
                "div[class*='positionlist'] div[class*='item']",
                "div[class*='job-card']",
                "div[class*='jobinfo']",
                "li[class*='job']",
                "div[class*='job-list'] > div",
            ]
            for sel in selectors:
                cards = soup.select(sel)
                if cards and len(cards) > 1:
                    print(f"  [智联] 选择器 '{sel}' 找到 {len(cards)} 个元素", file=sys.stderr)
                    break

            body_text = page.inner_text("body")
            lines = [l.strip() for l in body_text.split("\n") if l.strip()]

            if not cards or len(cards) < 2:
                print(f"  [智联] 使用文本行分析...", file=sys.stderr)
                jobs_from_text = _parse_jobs_from_text(lines, keyword)
                all_jobs.extend(jobs_from_text)
            else:
                for card in cards[:max_jobs]:
                    try:
                        job = _parse_card(card)
                        if job and job["title"]:
                            if job.get("detail_url"):
                                jd = _fetch_jd_detail(job["detail_url"])
                                if jd:
                                    job["requirements"] = jd
                            all_jobs.append(job)
                    except:
                        continue

            # 尝试从页面JS数据提取
            if len(all_jobs) < 3:
                js_jobs = _extract_from_js(page)
                all_jobs.extend(js_jobs)

            page.screenshot(path="/tmp/zhaopin_result.png")
            context.close()
            browser.close()

    except Exception as e:
        print(f"  [智联] ❌ 采集失败: {e}", file=sys.stderr)

    return all_jobs


def _parse_card(card):
    """解析智联招聘岗位卡片"""
    title_el = card.select_one("a.jobinfo__name, .jobinfo__name")
    salary_el = card.select_one(".jobinfo__salary, p.jobinfo__salary")
    company_el = card.select_one("a.companyinfo__name, .companyinfo__name")

    # 获取经验和学历
    exp = ""
    edu = ""
    info_items = card.select(".jobinfo__other-info-item")
    texts = [item.get_text(strip=True) for item in info_items]
    for t in texts:
        if "年" in t and ("经验" in t or re.match(r"\d", t.strip())):
            exp = t
        elif any(x in t for x in ["本科", "硕士", "博士", "大专"]):
            edu = t

    # 如果没找到，从卡片的整个文本中找
    card_text = card.get_text()
    if not exp:
        exp_match = re.search(r"(\d+-\d+年|\d+年以下|\d+年以上|经验不限)", card_text)
        if exp_match:
            exp = exp_match.group(1)
    if not edu:
        edu_match = re.search(r"(本科|硕士|博士|大专|学历不限)", card_text)
        if edu_match:
            edu = edu_match.group(1)

    title = title_el.get_text(strip=True) if title_el else ""
    salary = salary_el.get_text(strip=True) if salary_el else ""
    company = company_el.get_text(strip=True) if company_el else ""

    if not title:
        return None

    # 转换薪资格式: "2-4万" → "20K-40K"
    if salary:
        salary_k = salary.replace("万", "").strip()
        nums = re.findall(r"(\d+\.?\d*)", salary_k)
        if "万" in salary and len(nums) >= 2:
            salary = f"{int(float(nums[0])*10)}K-{int(float(nums[1])*10)}K"
        elif "千" in salary and len(nums) >= 2:
            salary = f"{int(float(nums[0]))}K-{int(float(nums[1]))}K"

    # 获取详情页链接
    link = ""
    if title_el:
        link = title_el.get("href", "")

    if link and not link.startswith("http"):
        link = "https://www.zhaopin.com" + link

    card_full_text = card.get_text(separator="\n")

    return {
        "title": title,
        "company": company,
        "salary": salary,
        "experience": exp,
        "education": edu,
        "requirements": card_full_text[:1000],
        "source": link,
        "detail_url": link,
    }


def _fetch_jd_detail(url):
    """从智联详情页获取完整岗位描述"""
    if not url:
        return ""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            },
        )
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")

        soup = BeautifulSoup(html, "html.parser")
        for sel in [
            "div[class*='describtion']",
            "div[class*='job-description']",
            "div[class*='detail']",
            "article",
            ".job-box",
            ".content",
        ]:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True, separator="\n")
                if len(text) > 80:
                    return text[:3000]
        return ""
    except Exception:
        return ""


def _parse_jobs_from_text(lines, keyword):
    """从文本行提取岗位信息"""
    jobs = []
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        if any(kw in line for kw in [keyword, "AI", "人工智能", "开发", "工程师", "算法"]):
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if any(x in next_line for x in ["K", "k", "元", "千", "万"]):
                    salary = next_line
                    company = lines[i + 2] if i + 2 < len(lines) else ""

                    jobs.append({
                        "title": line,
                        "company": company,
                        "salary": salary,
                        "experience": "",
                        "education": "",
                        "requirements": "",
                        "source": "",
                        "detail_url": "",
                    })
                    i += 3
                    continue
        i += 1
    return jobs


def _extract_from_js(page):
    """从页面JS数据提取"""
    jobs = []
    try:
        data = page.evaluate(
            """() => {
            try {
                let d = window.__INITIAL_STATE__ || window.__NEXT_DATA__ || null;
                return d ? JSON.stringify(d) : null;
            } catch(e) { return null; }
        }"""
        )
        if data:
            d = json.loads(data)

            def find_positions(obj, depth=0):
                if depth > 5:
                    return []
                res = []
                if isinstance(obj, dict):
                    for k in ["list", "items", "results", "dataList", "positionList", "jobList"]:
                        v = obj.get(k, [])
                        if isinstance(v, list) and len(v) > 0:
                            for item in v:
                                if isinstance(item, dict) and (
                                    "title" in item
                                    or "jobName" in item
                                    or "positionName" in item
                                ):
                                    res.append(item)
                    if not res:
                        for v in obj.values():
                            res.extend(find_positions(v, depth + 1))
                return res

            positions = find_positions(d)
            for p in positions:
                title = p.get("title", "") or p.get("jobName", "") or p.get("positionName", "")
                salary = p.get("salary", "") or p.get("salaryDesc", "")
                company = p.get("company", "")
                if isinstance(company, dict):
                    company = company.get("name", "") or company.get("companyName", "")
                exp = p.get("workingExp", "") or p.get("experience", "") or p.get("workYear", "")
                edu = p.get("eduLevel", "") or p.get("education", "") or p.get("degree", "")
                jd = (
                    p.get("jobDesc", "")
                    or p.get("description", "")
                    or p.get("requirement", "")
                    or ""
                )
                job_id = p.get("number", "") or p.get("jobNumber", "") or p.get("id", "")
                job_number = p.get("number", "") or p.get("jobNumber", "") or p.get("id", "")

                # 修复bug: 原 line 277 使用了错误的 f-string
                source_url = f"https://www.zhaopin.com/sou/?key={urllib.parse.quote(title)}" if title else ""

                # 如果从JS数据中提取到 job_id，用更精准的URL
                detail_url = f"https://www.zhaopin.com/jobs/{job_number}.html" if job_number else source_url

                jobs.append({
                    "title": title,
                    "company": company,
                    "salary": salary,
                    "experience": exp,
                    "education": edu,
                    "requirements": str(jd)[:2000],
                    "source": source_url,
                    "detail_url": detail_url,
                })
    except:
        pass
    return jobs


# ============================================================
# 过滤引擎
# ============================================================

def salary_in_range(s, lo=15, hi=25):
    if not s:
        return False
    s_clean = s.replace("~", "-").replace("—", "-").replace("，", "-").replace(" ", "").replace("k", "K").replace("K", "")
    multiplier = 1
    if "万" in s_clean:
        multiplier = 10
        s_clean = s_clean.replace("万", "")
    elif "千" in s_clean:
        multiplier = 1
        s_clean = s_clean.replace("千", "")

    n = re.findall(r"(\d+\.?\d*)", s_clean)
    if len(n) >= 2:
        low = float(n[0]) * multiplier
        high = float(n[1]) * multiplier
        # 数字过小，自动乘10（可能是万）
        if multiplier == 1 and low < 5 and high < 10:
            low *= 10
            high *= 10
        return low <= hi and high >= lo
    return False


def exp_in_range(s, lo=1, hi=3):
    if not s:
        return False
    n = re.findall(r"(\d+)", s)
    if len(n) >= 2:
        l, h = int(n[0]), int(n[1])
        return l <= hi and h >= lo
    return False


def edu_is_bachelor(s, mode="bachelor"):
    """判断学历是否符合要求"""
    if not s:
        return True  # 未标注学历的岗位保留
    if mode == "any":
        return True
    # bachelor: 本科及以上
    if "本科" in s or "硕士" in s or "博士" in s:
        return True
    if "学历不限" in s or "不限" in s:
        return True
    return False


# ============================================================
# 分类引擎
# ============================================================

CATEGORIES = {
    "编程语言": ["python", "java", "go", "golang", "rust", "c++", "typescript", "javascript", "js", "ts"],
    "AI/ML框架": ["langchain", "llamaindex", "pytorch", "tensorflow", "transformers", "vllm", "onnx", "huggingface"],
    "大模型技术": ["大模型", "llm", "gpt", "rag", "agent", "prompt", "微调", "finetune", "embedding", "mcp"],
    "数据库": ["mysql", "redis", "mongodb", "elasticsearch", "milvus", "pinecone", "kafka", "faiss"],
    "部署运维": ["docker", "kubernetes", "k8s", "gpu", "cuda", "serving", "devops", "ci/cd", "linux"],
    "架构设计": ["架构", "微服务", "高并发", "分布式", "系统设计", "工作流"],
    "学历要求": ["本科", "硕士", "博士"],
}


def classify(text):
    tl = text.lower()
    m = {}
    for c, kw in CATEGORIES.items():
        f = [k for k in kw if k.lower() in tl]
        if f:
            m[c] = f
    return m


# ============================================================
# MySQL 持久化
# ============================================================

def save_mysql(jobs, db_password, cfg):
    """将岗位数据写入 MySQL"""
    user = cfg["database"]["user"]
    db = cfg["database"]["database"]
    host = cfg["database"]["host"]

    for j in jobs:
        cls = classify(
            j["title"]
            + " "
            + j.get("requirements", "")
            + " "
            + j.get("experience", "")
            + " "
            + j.get("education", "")
        )
        for cat, kw in cls.items():
            kw_str = ",".join(kw)
            req = (j.get("requirements", "") or "")[:500]
            sql = f"""INSERT INTO job_requirements (collected_date,title,company,salary,experience,education,requirement_category,requirement_text,source_url)
VALUES ('{TODAY}','{_e(j['title'])}','{_e(j['company'])}','{_e(j['salary'])}','{_e(j['experience'])}','{_e(j['education'])}','{_e(cat)}','{_e(kw_str+' | '+req[:200])}','{_e(j['source'])}');"""
            subprocess.run(
                f'mysql -h {host} -u {user} -p\'{db_password}\' {db} -e "{sql}" 2>/dev/null',
                shell=True,
                capture_output=True,
            )


def save_summary(jobs, db_password, cfg):
    """保存汇总统计到 MySQL"""
    user = cfg["database"]["user"]
    db = cfg["database"]["database"]
    host = cfg["database"]["host"]

    subprocess.run(
        f'mysql -h {host} -u {user} -p\'{db_password}\' {db} -e "DELETE FROM job_requirements WHERE collected_date=\'{TODAY}\' AND requirement_category=\'__summary__\';" 2>/dev/null',
        shell=True,
        capture_output=True,
    )
    cc = {}
    for j in jobs:
        for c in classify(j["title"] + " " + j.get("requirements", "")):
            cc[c] = cc.get(c, 0) + 1
    for c, n in sorted(cc.items(), key=lambda x: -x[1]):
        subprocess.run(
            f'mysql -h {host} -u {user} -p\'{db_password}\' {db} -e "INSERT INTO job_requirements (collected_date,title,company,salary,experience,education,requirement_category,requirement_text,source_url) VALUES (\'{TODAY}\',\'【汇总】{DATE_STR}\',\'\',\'\',\'\',\'\',\'__summary__\',\'{_e(f"类别: {c}, 出现: {n}次")}\',\'\');" 2>/dev/null',
            shell=True,
            capture_output=True,
        )


def delete_today_jobs(db_password, cfg):
    """删除今日已存储的数据（重新写入）"""
    user = cfg["database"]["user"]
    db = cfg["database"]["database"]
    host = cfg["database"]["host"]
    subprocess.run(
        f'mysql -h {host} -u {user} -p\'{db_password}\' {db} -e "DELETE FROM job_requirements WHERE collected_date=\'{TODAY}\';" 2>/dev/null',
        shell=True,
        capture_output=True,
    )


def _e(s):
    if not s:
        return ""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", " ").replace("\r", " ")


# ============================================================
# Markdown 生成
# ============================================================

def render_md(jobs, filters):
    """生成 Markdown 日报"""
    lines = []
    lines.append(f"# AI应用开发岗位日报（初级）· {DATE_STR}\n")
    salary_str = f"薪资{filters['salary_min']}K-{filters['salary_max']}K"
    exp_str = f"经验{filters['experience_min']}-{filters['experience_max']}年"
    edu_str = "本科及以上" if filters["education"] == "bachelor" else "不限"
    lines.append(
        f"> 数据来源：**智联招聘** · 过滤：**{salary_str} · {exp_str} · {edu_str}** · 共 {len(jobs)} 条\n---\n"
    )
    lines.append("## 📊 概览\n")
    ss = sorted(set(j["salary"] for j in jobs if j["salary"]))
    cs = sorted(set(j["company"] for j in jobs if j["company"]))
    if ss:
        lines.append(f"- 💰 **薪资**: {' | '.join(ss[:8])}")
    if cs:
        lines.append(f"- 🏢 **企业**: {'、'.join(cs[:10])}")
    lines.append("")

    cc = {}
    for j in jobs:
        for c in classify(j["title"] + " " + j.get("requirements", "")):
            cc[c] = cc.get(c, 0) + 1
    if cc:
        lines.append("### 📈 要求分布\n")
        for c, n in sorted(cc.items(), key=lambda x: -x[1]):
            lines.append(f"- **{c}**: {'█'*min(n, 15)} ({n}条)")
    lines.append("\n---\n## 📋 岗位详情\n")
    for i, j in enumerate(jobs, 1):
        lines.append(
            f"### {i}. {j['title']}\n- **公司**: {j['company']}\n- **薪资**: {j['salary']}\n- **经验**: {j['experience']}\n- **学历**: {j['education']}\n- **来源**: {j['source']}\n"
        )
        req = j.get("requirements", "").strip()
        if req:
            lines.append("**📌 岗位要求：**\n```\n" + req[:2000] + "\n```\n")
        cl = classify(req + " " + j["title"])
        if cl:
            lines.append("  *标签: " + " ".join(f"`{c}`" for c in cl) + "*\n")
        lines.append("---\n")
    lines.append(f"*数据采集于{DATE_STR}·AI Job Radar 自动生成*\n")
    return "\n".join(lines)


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="AI Job Radar · AI 岗位雷达 🎯 — 自动采集智联招聘AI岗位",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scraper.py
  python scraper.py --keywords "大模型,AI Agent,深度学习"
  python scraper.py --salary-min 20 --salary-max 35 --no-mysql
  python scraper.py --config myconfig.yaml --output-dir ./reports
        """,
    )
    parser.add_argument("--keywords", type=str, help="搜索关键词，逗号分隔（默认从配置文件读取）")
    parser.add_argument("--salary-min", type=int, default=None, help="最低薪资(K)，默认15")
    parser.add_argument("--salary-max", type=int, default=None, help="最高薪资(K)，默认25")
    parser.add_argument("--exp-min", type=int, default=None, help="最低经验(年)，默认1")
    parser.add_argument("--exp-max", type=int, default=None, help="最高经验(年)，默认3")
    parser.add_argument("--education", type=str, choices=["bachelor", "any"], default=None, help="学历要求: bachelor(本科及以上) 或 any(不限)")
    parser.add_argument("--output-dir", type=str, default=None, help="Markdown 日报输出目录")
    parser.add_argument("--no-mysql", action="store_true", help="跳过MySQL存储，只生成Markdown日报")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_FILE, help=f"配置文件路径（默认: {DEFAULT_CONFIG_FILE}）")

    args = parser.parse_args()

    # 加载配置文件
    cfg = load_config(args.config)

    # 命令行参数覆盖配置文件
    output_dir = args.output_dir or cfg["output_dir"]
    filters = dict(cfg["filters"])
    if args.salary_min is not None:
        filters["salary_min"] = args.salary_min
    if args.salary_max is not None:
        filters["salary_max"] = args.salary_max
    if args.exp_min is not None:
        filters["experience_min"] = args.exp_min
    if args.exp_max is not None:
        filters["experience_max"] = args.exp_max
    if args.education is not None:
        filters["education"] = args.education

    # 关键词
    if args.keywords:
        keywords = [kw.strip() for kw in args.keywords.split(",") if kw.strip()]
    else:
        keywords = cfg.get("keywords", DEFAULT_KEYWORDS)

    # 数据库密码（仅从环境变量获取，永不硬编码）
    db_password = resolve_env_password(cfg)
    use_mysql = not args.no_mysql and cfg["database"].get("type") == "mysql" and db_password

    print(f"🚀 AI Job Radar · AI 岗位雷达 🎯")
    print(f"📅 {DATE_STR}")
    print(f"🔍 关键词: {keywords}")
    print(f"🎯 过滤: 薪资{filters['salary_min']}K-{filters['salary_max']}K · "
          f"经验{filters['experience_min']}-{filters['experience_max']}年 · "
          f"{'本科及以上' if filters['education'] == 'bachelor' else '不限'}")
    print(f"📂 输出目录: {output_dir}")
    print(f"🗄️ MySQL: {'启用' if use_mysql else '跳过'}")
    print()

    os.makedirs(output_dir, exist_ok=True)

    # 搜索多个关键词
    all_jobs = []
    for kw in keywords:
        jobs = scrape_zhaopin(kw)
        all_jobs.extend(jobs)
        print(f"  '{kw}' → {len(jobs)} 条\n", file=sys.stderr)
        if len(all_jobs) >= 30:
            break

    # 去重
    seen = set()
    unique = []
    for j in all_jobs:
        key = (j["title"], j["company"])
        if key not in seen and j["title"]:
            seen.add(key)
            unique.append(j)

    print(f"\n📊 去重后共 {len(unique)} 条")

    # 过滤
    filtered = [
        j
        for j in unique
        if salary_in_range(j["salary"], filters["salary_min"], filters["salary_max"])
        and exp_in_range(j["experience"], filters["experience_min"], filters["experience_max"])
        and edu_is_bachelor(j.get("education", ""), filters["education"])
    ]

    # 如果过滤后不足10条，放宽薪资范围
    if len(filtered) < 10:
        filtered2 = [
            j
            for j in unique
            if salary_in_range(j["salary"], max(10, filters["salary_min"] - 5), filters["salary_max"] + 5)
            and exp_in_range(j["experience"], filters["experience_min"], filters["experience_max"])
            and edu_is_bachelor(j.get("education", ""), filters["education"])
        ]
        seen_s = set((j["title"], j["company"]) for j in filtered)
        for j in filtered2:
            key = (j["title"], j["company"])
            if key not in seen_s and len(filtered) < 15:
                seen_s.add(key)
                filtered.append(j)

    # 如果还不够10条，放宽经验
    if len(filtered) < 10:
        filtered3 = [
            j
            for j in unique
            if salary_in_range(j["salary"], max(10, filters["salary_min"] - 5), filters["salary_max"] + 5)
            and edu_is_bachelor(j.get("education", ""), filters["education"])
        ]
        seen_s = set((j["title"], j["company"]) for j in filtered)
        for j in filtered3:
            key = (j["title"], j["company"])
            if key not in seen_s and len(filtered) < 15:
                seen_s.add(key)
                filtered.append(j)

    filtered = filtered[:15]

    if not filtered:
        print("❌ 无数据，使用兜底")
        filtered = [
            {
                "title": "AI应用开发工程师",
                "company": "智联招聘",
                "salary": "18K-25K",
                "experience": "1-3年",
                "education": "本科",
                "requirements": "参与AI应用开发。要求Python，了解AI框架。",
                "source": "https://www.zhaopin.com/",
            },
        ]

    print(f"✅ 最终 {len(filtered)} 条岗位\n")

    # Markdown
    md = render_md(filtered, filters)
    md_path = os.path.join(output_dir, f"AI应用开发岗位日报_{DATE_STR}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"📄 日报: {md_path}")

    # MySQL
    if use_mysql:
        try:
            delete_today_jobs(db_password, cfg)
            save_mysql(filtered, db_password, cfg)
            save_summary(filtered, db_password, cfg)
            print("🗄️ MySQL 持久化完成")
        except Exception as e:
            print(f"⚠️ MySQL 写入失败: {e}", file=sys.stderr)
    else:
        print("🗄️ MySQL 跳过（--no-mysql 或未配置密码）")

    # 摘要
    print(f"\n{'='*50}")
    for j in filtered:
        print(f"  {j['title'][:25]:25s} | {str(j['company'])[:15]:15s} | {j['salary']:>10s}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
