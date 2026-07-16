import json
from pathlib import Path

from fastapi.routing import APIRoute

import myjob_server
from resume_store import ResumeStore


ROOT = Path(__file__).parents[1]


def test_backend_has_no_recruitment_platform_routes():
    forbidden_prefixes = (
        "/api/system",
        "/api/jobs",
        "/api/applications",
        "/api/conversations",
        "/api/campaigns",
        "/api/monitor",
        "/api/companies",
        "/api/wechat-exchanges",
        "/api/settings",
        "/api/dashboard",
    )
    paths = [route.path for route in myjob_server.app.routes if isinstance(route, APIRoute)]
    assert not [path for path in paths if path.startswith(forbidden_prefixes)]
    assert myjob_server.health()["platform_backend"] is False


def test_vue_platform_views_do_not_call_platform_backend_apis():
    files = [
        ROOT / "resume_ui/src/Workspace.vue",
        ROOT / "resume_ui/src/views/OverviewView.vue",
        ROOT / "resume_ui/src/views/JobCenterView.vue",
        ROOT / "resume_ui/src/views/CampaignsView.vue",
        ROOT / "resume_ui/src/views/CommunicationView.vue",
        ROOT / "resume_ui/src/views/SettingsView.vue",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in files)
    for prefix in (
        "/api/system",
        "/api/jobs",
        "/api/applications",
        "/api/conversations",
        "/api/campaigns",
        "/api/dashboard",
        "/api/settings",
        "/api/doctor",
    ):
        assert prefix not in source
    assert "platformStore" in source
    assert "platformBridge" in source


def test_extension_declares_only_user_side_platform_hosts():
    manifest = json.loads((ROOT / "browser_extension/manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    assert manifest["version"] == "0.0.12"
    hosts = manifest["host_permissions"]
    assert any("zhipin.com" in item for item in hosts)
    assert any("zhaopin.com" in item for item in hosts)
    assert any("liepin.com" in item for item in hosts)
    assert any("51job.com" in item for item in hosts)
    assert (ROOT / "browser_extension/background.js").is_file()
    assert (ROOT / "browser_extension/platformContent.js").is_file()


def test_workspace_login_logout_stop_contracts():
    workspace = (ROOT / "resume_ui/src/Workspace.vue").read_text(encoding="utf-8")
    assert "无需重复登录" in workspace
    assert "全部登出" in workspace
    assert "所有招聘平台浏览器窗口已停止运行" in workspace
    assert "登录心跳运行中" not in workspace


def test_logged_in_platform_short_circuits_before_login_request():
    bridge = (ROOT / "resume_ui/src/platformBridge.js").read_text(encoding="utf-8")
    start = bridge.index("async function startLogin(platform)")
    end = bridge.index("export const platformBridge", start)
    contract = bridge[start:end]
    already_logged_in = contract.index("current.platforms?.[platform]?.logged_in")
    login_request = contract.index("requireExtension('login'")
    assert already_logged_in < login_request
    assert "already_logged_in: true" in contract


def test_extension_logout_and_stop_cover_all_platforms():
    background = (ROOT / "browser_extension/background.js").read_text(encoding="utf-8")
    assert "Object.values(PLATFORMS).flatMap(item => item.origins)" in background
    assert "chrome.browsingData.remove({ origins }" in background
    assert "cookies: true" in background
    assert "localStorage: true" in background
    assert "indexedDB: true" in background
    assert "async function stopAll()" in background
    assert "chrome.tabs.remove(ids)" in background


def test_interview_service_has_no_platform_job_store_or_route():
    files = [
        ROOT / "interview/db.py",
        ROOT / "interview/engine.py",
        ROOT / "interview/main.py",
        ROOT / "interview/llm_client.py",
        ROOT / "interview/fast_qa.py",
        ROOT / "interview/batch_seed.py",
        ROOT / "interview/benchmark.py",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in files)
    for forbidden in (
        "boss_state",
        "job_requirements",
        "search_jobs_by_semantic",
        "get_all_job_categories",
        '"/api/jobs/search"',
    ):
        assert forbidden not in source
    assert "MYJOB_AI_API_KEY" in (ROOT / "interview/ai_config.py").read_text(encoding="utf-8")


def test_server_does_not_open_legacy_platform_database():
    server = (ROOT / "myjob_server.py").read_text(encoding="utf-8")
    store = (ROOT / "resume_store.py").read_text(encoding="utf-8")
    assert "boss_state.db" not in server
    assert "legacy_path" not in store


def test_setup_does_not_install_server_side_browser_automation():
    setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
    assert "Playwright" not in setup
    assert "playwright" not in setup
    assert "boss_firefox" not in setup
    assert "browser_extension" in setup


def test_resume_header_removes_new_resume_status_badge():
    source = (ROOT / "resume_ui/src/App.vue").read_text(encoding="utf-8")
    assert "vre-save-state" not in source
    assert "saveStateText" not in source


def test_each_platform_has_a_client_enforced_daily_limit_of_at_most_50():
    limits = (ROOT / "resume_ui/src/applicationLimits.js").read_text(encoding="utf-8")
    store = (ROOT / "resume_ui/src/platformStore.js").read_text(encoding="utf-8")
    settings = (ROOT / "resume_ui/src/views/SettingsView.vue").read_text(encoding="utf-8")
    jobs = (ROOT / "resume_ui/src/views/JobCenterView.vue").read_text(encoding="utf-8")
    campaigns = (ROOT / "resume_ui/src/views/CampaignsView.vue").read_text(encoding="utf-8")
    assert "MAX_DAILY_APPLY_LIMIT = 50" in limits
    assert "daily_apply_limits" in store
    assert 'max="50"' in settings
    assert "getApplicationAllowance" in jobs
    assert "getApplicationAllowance" in campaigns


def test_jd_tailoring_stays_client_side_and_whitelists_resume_modules():
    optimizer = (ROOT / "resume_ui/src/resumeTailor.js").read_text(encoding="utf-8")
    editor = (ROOT / "resume_ui/src/App.vue").read_text(encoding="utf-8")
    bridge = (ROOT / "resume_ui/src/platformBridge.js").read_text(encoding="utf-8")
    extension = (ROOT / "browser_extension/background.js").read_text(encoding="utf-8")
    assert "FACT_CONSTRAINT_LEVELS" in optimizer
    assert "summary" in optimizer and "experience" in optimizer and "projects" in optimizer
    assert "skills" in optimizer and "evaluation" in optimizer
    assert "education: new Set" not in optimizer
    assert "不得修改个人资料和教育经历" in optimizer
    assert "needs_confirmation" in optimizer
    assert "optimizeResumeForJd" in editor
    assert "getJobDetail" in bridge
    assert "getJobDetail" in extension
    assert "/api/" not in optimizer


def test_resume_store_is_user_scoped(tmp_path: Path):
    store = ResumeStore(tmp_path / "resumes.db")
    first = store.save(1, content="# A", name="A", structured={"basics": {"name": "A"}})
    second = store.save(2, content="# B", name="B", structured={"basics": {"name": "B"}})
    assert first["user_id"] == 1
    assert second["user_id"] == 2
    assert store.get(1)["name"] == "A"
    assert store.get(2)["name"] == "B"
