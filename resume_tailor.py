"""JD 定制简历的纯函数。

这个模块不直接访问数据库或网络，便于在 API、CLI 和测试中复用。
生成阶段要求模型只重排、改写主简历里已有的事实；审计阶段会额外标记
主简历中没有出现的数字，避免把模型生成内容直接当成真实经历投递。
"""

from __future__ import annotations

import html
import json
import re
from collections import Counter
from typing import Any, Callable

_STOPWORDS = {
    "负责", "相关", "工作", "岗位", "要求", "优先", "能力", "经验", "熟悉",
    "掌握", "具备", "以及", "进行", "能够", "公司", "团队", "以上", "以下",
}


def extract_keywords(text: str, limit: int = 40) -> list[str]:
    """从中英文 JD/简历中提取可解释的关键词。"""
    text = (text or "").strip()
    if not text:
        return []
    tokens: list[str] = []
    tokens.extend(re.findall(r"[A-Za-z][A-Za-z0-9+#._/-]{1,30}", text))
    for block in re.findall(r"[\u4e00-\u9fff]{2,12}", text):
        if len(block) <= 6:
            tokens.append(block)
        else:
            tokens.extend(block[i : i + 4] for i in range(0, len(block) - 3, 2))
    normalized = [t.strip("._/-").lower() for t in tokens]
    counts = Counter(t for t in normalized if len(t) >= 2 and t not in _STOPWORDS)
    return [token for token, _ in counts.most_common(limit)]


def score_resume_match(master_resume: str, job: dict, target_keywords: list[str] | None = None) -> dict:
    """用本地、零 token 的方式给岗位做初筛评分。"""
    jd = " ".join(
        str(job.get(key) or "")
        for key in ("job_title", "title", "description", "experience", "education")
    )
    resume_terms = set(extract_keywords(master_resume, 120))
    jd_terms = extract_keywords(jd, 60)
    matched = [term for term in jd_terms if term in resume_terms]
    missing = [term for term in jd_terms if term not in resume_terms]
    overlap = len(matched) / max(1, min(len(jd_terms), 25))

    title = str(job.get("job_title") or job.get("title") or "").lower()
    targets = [str(x).strip().lower() for x in (target_keywords or []) if str(x).strip()]
    title_hit = any(target in title or title in target for target in targets) if targets and title else False

    score = round(min(100, overlap * 75 + (20 if title_hit else 0) + (5 if job.get("description") else 0)))
    return {
        "score": score,
        "matched_keywords": matched[:15],
        "missing_keywords": missing[:15],
        "title_matched": title_hit,
    }


def build_tailor_prompt(master_resume: str, job: dict) -> str:
    """构造严格遵守事实边界的简历改写提示词。"""
    return f"""你是严谨的中文简历编辑。请针对岗位 JD 重排和改写主简历，输出严格 JSON。

## 绝对规则
1. 只能使用主简历中明确存在的经历、技能、项目、数字和结果。
2. 不得新增公司、职位、项目、学历、证书、技术栈、年限、业绩数字。
3. JD 提到但主简历没有的能力，只能放进 missing_keywords，不能写进简历正文。
4. 保留姓名和联系方式（如果原文存在）；使用简体中文和 Markdown。
5. 优先调整摘要、技能顺序和项目表述，使真实经历更贴近 JD。

## 主简历（唯一事实来源）
{master_resume[:12000]}

## 目标岗位
- 职位：{job.get('job_title') or job.get('title') or ''}
- 公司：{job.get('company') or ''}
- 城市：{job.get('city') or ''}
- JD：{str(job.get('description') or '')[:6000]}

## 输出格式
{{
  "resume_markdown": "完整的定制简历 Markdown",
  "professional_summary": "针对该岗位的真实职业摘要",
  "matched_keywords": ["主简历中确实存在且匹配 JD 的词"],
  "missing_keywords": ["JD 要求但主简历没有的词"],
  "changes": [{{"section": "模块", "change": "做了什么调整", "reason": "与 JD 的关系"}}],
  "truthfulness_notes": ["需要用户确认的模糊表述；没有则为空数组"]
}}"""


def parse_json_object(raw: str) -> dict[str, Any]:
    """解析模型常见的 fenced JSON 输出。"""
    cleaned = (raw or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            raise ValueError("AI 未返回可解析的 JSON")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("AI 返回结果不是 JSON 对象")
    return value


def audit_tailored_resume(master_resume: str, tailored_resume: str) -> dict:
    """标记定制稿中新出现的数字；数字通常是最危险的编造信号。"""
    number_pattern = r"(?<![A-Za-z])\d+(?:\.\d+)?%?(?![A-Za-z])"
    source_numbers = set(re.findall(number_pattern, master_resume or ""))
    result_numbers = set(re.findall(number_pattern, tailored_resume or ""))
    unsupported = sorted(result_numbers - source_numbers)
    return {
        "passed": not unsupported,
        "unsupported_numbers": unsupported,
        "warning": "" if not unsupported else "定制稿出现主简历中没有的数字，请人工核实后再使用。",
    }


def tailor_resume(master_resume: str, job: dict, llm: Callable[[str], str]) -> dict:
    if not (master_resume or "").strip():
        raise ValueError("请先保存主简历")
    if not (job.get("description") or job.get("job_title") or job.get("title")):
        raise ValueError("岗位缺少标题和 JD")
    result = parse_json_object(llm(build_tailor_prompt(master_resume, job)))
    markdown = str(result.get("resume_markdown") or "").strip()
    if len(markdown) < 80:
        raise ValueError("AI 返回的定制简历内容过短")
    result["audit"] = audit_tailored_resume(master_resume, markdown)
    result["status"] = "draft" if result["audit"]["passed"] else "needs_review"
    return result


def resume_to_html(markdown_text: str, title: str = "定制简历") -> str:
    """生成可打印、可用 Word 打开的单文件 HTML，不引入额外依赖。"""
    lines = []
    for raw_line in (markdown_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("<div class=\"space\"></div>")
        elif line.startswith("### "):
            lines.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            lines.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            lines.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith(("- ", "* ")):
            lines.append(f"<div class=\"bullet\">• {html.escape(line[2:])}</div>")
        else:
            lines.append(f"<p>{html.escape(line)}</p>")
    body = "\n".join(lines)
    return f"""<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title>
<style>@page{{size:A4;margin:16mm}}body{{font:14px/1.65 -apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;color:#202124;max-width:780px;margin:32px auto}}h1{{font-size:28px;border-bottom:2px solid #222;padding-bottom:8px}}h2{{font-size:18px;border-bottom:1px solid #ddd;padding-bottom:4px;margin-top:22px}}h3{{font-size:15px;margin-bottom:4px}}p{{margin:4px 0}}.bullet{{padding-left:18px;margin:3px 0}}.space{{height:6px}}@media print{{body{{margin:0}}}}</style></head><body>{body}</body></html>"""
