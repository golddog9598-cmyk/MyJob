"""求职计划的本地筛选与状态聚合逻辑。"""

from __future__ import annotations

from resume_tailor import score_resume_match

VALID_APPLY_MODES = {"review", "automatic"}


def validate_campaign_config(config: dict) -> dict:
    keywords = [str(x).strip() for x in config.get("keywords", []) if str(x).strip()]
    cities = [str(x).strip() for x in config.get("cities", []) if str(x).strip()]
    if not keywords:
        raise ValueError("至少填写一个目标岗位关键词")
    if not cities:
        raise ValueError("至少填写一个目标城市")
    apply_mode = str(config.get("apply_mode") or "review")
    if apply_mode not in VALID_APPLY_MODES:
        raise ValueError("apply_mode 只能是 review 或 automatic")
    if apply_mode == "automatic" and not config.get("auto_apply_confirmed"):
        raise ValueError("开启自动投递必须显式确认 auto_apply_confirmed=true")
    threshold = max(0, min(100, int(config.get("min_match_score", 60))))
    max_jobs = max(1, min(50, int(config.get("max_jobs_per_run", 10))))
    return {
        **config,
        "keywords": keywords,
        "cities": cities,
        "apply_mode": apply_mode,
        "min_match_score": threshold,
        "max_jobs_per_run": max_jobs,
        "auto_tailor": bool(config.get("auto_tailor", True)),
        "auto_apply_confirmed": bool(config.get("auto_apply_confirmed", False)),
    }


def rank_jobs(master_resume: str, jobs: list[dict], keywords: list[str], cities: list[str]) -> list[dict]:
    """按简历/JD 匹配度排序，并严格校验城市。"""
    city_set = {city.strip().lower() for city in cities if city.strip() and city.strip() != "全国"}
    ranked = []
    seen = set()
    for job in jobs:
        url = str(job.get("job_url") or job.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)
        city = str(job.get("city") or "").lower()
        if city_set and city and not any(target in city for target in city_set):
            continue
        match = score_resume_match(master_resume, job, keywords)
        ranked.append({**job, "match_score": match["score"], "match_detail": match})
    return sorted(ranked, key=lambda item: (item["match_score"], bool(item.get("description"))), reverse=True)


def pipeline_status(application: dict, conversation: dict | None = None) -> str:
    """把现有 application/conversation 状态映射到求职闭环。"""
    conversation = conversation or {}
    if conversation.get("interest_level") == "high":
        return "interview"
    if conversation.get("last_message_from") == "hr":
        return "replied"
    app_status = application.get("status") or "pending"
    if app_status in {"applied", "replied", "interview"}:
        return app_status
    if app_status in {"failed", "skipped", "filtered"}:
        return app_status
    return "review"
