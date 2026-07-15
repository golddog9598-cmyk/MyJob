import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

import boss_app
import boss_state
from boss_app import SearchRequest
from job_platforms import (
    PlatformManager,
    build_search_url,
    normalize_job_url,
    normalize_platform,
)


def test_platform_aliases_and_unknown_value():
    assert normalize_platform(None) == "boss"
    assert normalize_platform("51job") == "job51"
    assert normalize_platform("智联招聘") == "zhilian"
    assert normalize_platform("猎聘") == "liepin"
    with pytest.raises(ValueError, match="不支持的招聘平台"):
        normalize_platform("unknown")


def test_zhilian_search_url_maps_city_and_filters():
    url = build_search_url(
        "zhilian",
        "Python",
        "北京",
        salary="405",
        experience=104,
        degree=203,
        job_type="1",
    )
    assert url.startswith("https://www.zhaopin.com/sou/jl530/p1?")
    query = parse_qs(urlparse(url).query)
    assert query == {"sl": ["10001,25000"], "we": ["0103"], "el": ["4"], "et": ["2"]}


def test_liepin_search_url_maps_keyword_city_and_filters():
    url = build_search_url("liepin", "AI Agent", "深圳", experience=105, degree=203)
    query = parse_qs(urlparse(url).query)
    assert query["city"] == ["050090"]
    assert query["dq"] == ["050090"]
    assert query["key"] == ["AI Agent"]
    assert query["workYearCode"] == ["3$5"]
    assert query["eduLevel"] == ["040"]


def test_job51_search_url_and_relative_url_normalization():
    url = build_search_url("51job", "后端工程师", "上海", experience=106, degree=204, job_type="1")
    query = parse_qs(urlparse(url).query)
    assert query["jobArea"] == ["020000"]
    assert query["keyword"] == ["后端工程师"]
    assert query["workYear"] == ["04"]
    assert query["degree"] == ["05"]
    assert query["jobType"] == ["01"]
    assert normalize_job_url("job51", "/pc/jobdetail?jobId=42") == "https://we.51job.com/pc/jobdetail?jobId=42"


class _FakePage:
    def __init__(self, evidence=None, url="https://www.zhaopin.com/"):
        self.evidence = evidence or {}
        self.url = url

    def evaluate(self, script, *_args):
        if "negative" in script and "positive" in script:
            return self.evidence
        return None

    def goto(self, url, **_kwargs):
        self.url = url

    def bring_to_front(self):
        return None

    def is_closed(self):
        return False


class _FakeContext:
    def __init__(self):
        self._cookies = [
            {"name": "boss", "value": "1", "domain": ".zhipin.com", "path": "/"},
            {"name": "zl", "value": "1", "domain": ".zhaopin.com", "path": "/"},
        ]

    def cookies(self):
        return list(self._cookies)

    def clear_cookies(self):
        self._cookies = []

    def add_cookies(self, cookies):
        self._cookies.extend(cookies)


class _FakeAutomation:
    def __init__(self, page, context):
        self.page = page
        self._ctx = context
        self.saved = 0

    def _save_state(self):
        self.saved += 1


def test_login_detection_requires_positive_identity_evidence():
    page = _FakePage({"negative": False, "positive": False, "path": False, "text": False})
    manager = PlatformManager(_FakeAutomation(page, _FakeContext()))
    manager.pages["zhilian"] = page
    assert manager.is_logged_in("zhilian") is False

    page.evidence = {"negative": False, "positive": True, "path": False, "text": False}
    assert manager.is_logged_in("zhilian") is True

    page.evidence = {"negative": True, "positive": True, "path": True, "text": True}
    assert manager.is_logged_in("zhilian") is False

    page.evidence = {"negative": False, "positive": False, "path": False, "text": True}
    assert manager.is_logged_in("zhilian") is False

    page.url = "https://example.com/"
    page.evidence = {"negative": False, "positive": True, "path": False, "text": False}
    assert manager.is_logged_in("zhilian") is False


def test_logout_removes_only_target_platform_cookies():
    context = _FakeContext()
    page = _FakePage()
    automation = _FakeAutomation(page, context)
    manager = PlatformManager(automation)
    manager.pages["zhilian"] = page

    result = manager.logout("zhilian")

    assert result["status"] == "ok"
    assert [cookie["domain"] for cookie in context.cookies()] == [".zhipin.com"]
    assert page.url == "https://passport.zhaopin.com/login"
    assert automation.saved == 1


def test_platform_heartbeat_checks_only_open_pages():
    context = _FakeContext()
    boss_page = _FakePage(url="https://www.zhipin.com/web/user/")
    zhilian_page = _FakePage(
        {"negative": False, "positive": True, "path": False, "text": False},
        url="https://www.zhaopin.com/",
    )
    manager = PlatformManager(_FakeAutomation(boss_page, context))
    manager.pages["zhilian"] = zhilian_page

    result = manager.login_heartbeat()

    assert result["platforms"]["zhilian"] == {
        "label": "智联招聘",
        "page_open": True,
        "logged_in": True,
    }
    assert result["platforms"]["liepin"]["page_open"] is False
    assert result["platforms"]["liepin"]["logged_in"] is False
    assert "liepin" not in manager.pages


def test_start_login_opens_platform_login_page_when_logged_out():
    context = _FakeContext()
    boss_page = _FakePage(url="https://www.zhipin.com/web/user/")
    zhilian_page = _FakePage(url="about:blank")
    manager = PlatformManager(_FakeAutomation(boss_page, context))
    manager.pages["zhilian"] = zhilian_page

    result = manager.open_platform("zhilian", force_login=True)

    assert result["logged_in"] is False
    assert zhilian_page.url == "https://passport.zhaopin.com/login"


def test_application_platform_migration_and_filter(tmp_path: Path):
    old_path = boss_state.DB_PATH
    old_conn = getattr(boss_state._local, "conn", None)
    test_path = tmp_path / "platform.db"
    try:
        boss_state.DB_PATH = test_path
        boss_state._local.conn = None
        boss_state.init_db()
        zhilian_id = boss_state.add_application(
            {"platform": "zhilian", "title": "Python 工程师", "url": "https://www.zhaopin.com/jobdetail/1"}
        )
        boss_state.add_application(
            {"platform": "boss", "title": "Go 工程师", "url": "https://www.zhipin.com/job_detail/2"}
        )
        assert boss_state.get_application(zhilian_id)["platform"] == "zhilian"
        assert boss_state.count_applications(platform="zhilian") == 1
        assert [item["platform"] for item in boss_state.list_applications(platform="zhilian")] == ["zhilian"]
    finally:
        current = getattr(boss_state._local, "conn", None)
        if current is not None:
            current.close()
        boss_state.DB_PATH = old_path
        boss_state._local.conn = old_conn


def test_old_search_clients_still_default_to_boss():
    assert SearchRequest(keyword="Python").platform == "boss"


def test_workspace_uses_platform_cards_and_automatic_heartbeat():
    workspace = Path("resume_ui/src/Workspace.vue").read_text(encoding="utf-8")
    component = Path("resume_ui/src/components/PlatformLoginStatus.vue").read_text(encoding="utf-8")

    assert "PlatformLoginStatus" in workspace
    assert "启动登录" in workspace
    assert "检查登录" not in workspace
    assert "/api/system/heartbeat" in workspace
    assert "已登录" in component
    assert "未登录" in component


def test_platform_heartbeat_returns_four_logged_out_states_without_browser(monkeypatch):
    monkeypatch.setattr(boss_app, "automation", None)

    result = asyncio.run(boss_app.platform_login_heartbeat())

    assert result["browser_running"] is False
    assert set(result["platforms"]) == {"boss", "zhilian", "liepin", "job51"}
    assert all(not item["logged_in"] for item in result["platforms"].values())
