import json
from pathlib import Path

import pytest

from job_campaign import pipeline_status, rank_jobs, validate_campaign_config
from resume_tailor import audit_tailored_resume, resume_to_html, tailor_resume

MASTER = """# 张三
Python 后端工程师

## 技能
- Python、FastAPI、PostgreSQL

## 项目
- 使用 FastAPI 开发招聘系统，接口响应时间降低 30%。
"""


def test_tailor_resume_parses_fenced_json_and_audits_numbers():
    payload = {
        "resume_markdown": MASTER + "\n- 更突出 FastAPI 与 PostgreSQL。",
        "professional_summary": "Python 后端工程师",
        "matched_keywords": ["Python", "FastAPI"],
        "missing_keywords": ["Kubernetes"],
        "changes": [],
        "truthfulness_notes": [],
    }
    result = tailor_resume(
        MASTER,
        {"job_title": "Python 后端", "description": "Python FastAPI Kubernetes"},
        lambda _: "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```",
    )
    assert result["audit"]["passed"] is True
    assert result["status"] == "draft"


def test_tailor_resume_flags_fabricated_metric():
    audit = audit_tailored_resume(MASTER, MASTER + "\n- 转化率提升 99%")
    assert audit["passed"] is False
    assert "99%" in audit["unsupported_numbers"]


def test_rank_jobs_respects_city_and_orders_by_match():
    jobs = [
        {
            "job_url": "https://example.com/1",
            "job_title": "Python 后端工程师",
            "description": "Python FastAPI PostgreSQL",
            "city": "深圳",
        },
        {
            "job_url": "https://example.com/2",
            "job_title": "Java 工程师",
            "description": "Java Spring",
            "city": "深圳",
        },
        {
            "job_url": "https://example.com/3",
            "job_title": "Python 后端工程师",
            "description": "Python FastAPI",
            "city": "北京",
        },
    ]
    ranked = rank_jobs(MASTER, jobs, ["Python 后端"], ["深圳"])
    assert [item["job_url"] for item in ranked] == ["https://example.com/1", "https://example.com/2"]
    assert ranked[0]["match_score"] > ranked[1]["match_score"]


def test_automatic_campaign_requires_explicit_confirmation():
    with pytest.raises(ValueError, match="显式确认"):
        validate_campaign_config(
            {"keywords": ["Python"], "cities": ["深圳"], "apply_mode": "automatic"}
        )
    config = validate_campaign_config(
        {
            "keywords": ["Python"],
            "cities": ["深圳"],
            "apply_mode": "automatic",
            "auto_apply_confirmed": True,
        }
    )
    assert config["auto_apply_confirmed"] is True


def test_pipeline_status_promotes_high_interest_to_interview():
    assert pipeline_status({"status": "applied"}, {"interest_level": "high"}) == "interview"
    assert pipeline_status({"status": "applied"}, {"last_message_from": "hr"}) == "replied"


def test_html_export_escapes_resume_content():
    result = resume_to_html("# 张三\n- FastAPI <script>alert(1)</script>")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_resume_and_campaign_state_round_trip(tmp_path: Path):
    import boss_state as state

    old_path = state.DB_PATH
    if getattr(state._local, "conn", None) is not None:
        state._local.conn.close()
    state._local.conn = None
    state.DB_PATH = tmp_path / "campaign.db"
    try:
        state.init_db()
        master = state.save_master_resume(MASTER)
        assert state.get_master_resume()["id"] == master["id"]

        application_id = state.add_application(
            {
                "title": "Python 后端",
                "company": "示例公司",
                "city": "深圳",
                "url": "https://example.com/state-job",
                "description": "Python FastAPI",
            }
        )
        tailored = state.save_tailored_resume(
            state.get_application(application_id),
            master["id"],
            {"resume_markdown": MASTER, "status": "draft", "audit": {"passed": True}},
        )
        assert state.get_tailored_resume(tailored["id"])["content"] == MASTER.strip()

        campaign = state.create_job_campaign(
            validate_campaign_config(
                {
                    "name": "测试计划",
                    "keywords": ["Python"],
                    "cities": ["深圳"],
                    "apply_mode": "review",
                }
            )
        )
        run_id = state.start_campaign_run(campaign["id"])
        state.upsert_campaign_job(
            campaign["id"], run_id, application_id, {"score": 88, "matched_keywords": ["python"]}, tailored["id"]
        )
        jobs = state.list_campaign_jobs(campaign["id"])
        assert jobs[0]["match_score"] == 88
        assert jobs[0]["tailored_resume_id"] == tailored["id"]
    finally:
        if getattr(state._local, "conn", None) is not None:
            state._local.conn.close()
        state._local.conn = None
        state.DB_PATH = old_path


def test_structured_resume_update_round_trip(tmp_path: Path):
    import boss_app
    import boss_state as state

    old_path = state.DB_PATH
    if getattr(state._local, "conn", None) is not None:
        state._local.conn.close()
    state._local.conn = None
    state.DB_PATH = tmp_path / "structured-resume.db"
    try:
        state.init_db()
        result = boss_app.update_structured_master_resume(boss_app.StructuredResumeUpdate(
            name="产品简历",
            template_id="vivi_sidebar",
            structured={
                "basics": {"name": "林微", "title": "AI 产品设计师"},
                "section_order": ["basic", "projects", "experience", "education", "skills", "summary", "evaluation"],
                "hidden_sections": ["evaluation"],
                "sections": [
                    {"key": "projects", "title": "项目经历", "entries": [{"id": "p1", "name": "智能招聘工作台", "role": "产品负责人", "description": "完成体验闭环。"}]},
                    {"key": "summary", "title": "个人简介", "content": "五年产品经验。"},
                ],
            },
        ))
        saved = result["resume"]
        assert saved["source_format"] == "structured-v2"
        assert saved["template_id"] == "vivi_sidebar"
        assert saved["structured"]["section_order"][1] == "projects"
        assert saved["structured"]["hidden_sections"] == ["evaluation"]
        assert saved["structured"]["sections"][0]["entries"][0]["name"] == "智能招聘工作台"
        assert "智能招聘工作台" in saved["content"]
    finally:
        if getattr(state._local, "conn", None) is not None:
            state._local.conn.close()
        state._local.conn = None
        state.DB_PATH = old_path
