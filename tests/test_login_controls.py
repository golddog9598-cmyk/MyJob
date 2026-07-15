import asyncio
from pathlib import Path

import boss_app
from boss_automation import BossAutomation


class _FakeAutomation:
    def __init__(self, logged_in=False, logout_ok=True):
        self.page = object()
        self._logged_in = logged_in
        self._logout_ok = logout_ok
        self.saved = False
        self.logged_out = False

    def check_login_verified(self):
        return self._logged_in

    def _save_state(self):
        self.saved = True

    def logout_session(self):
        self.logged_out = True
        return self._logout_ok



class _FakeTask:
    def __init__(self, done=False):
        self._done = done
        self.cancelled = False

    def done(self):
        return self._done

    def cancel(self):
        self.cancelled = True


async def _direct_run(fn, *args, **kwargs):
    return fn(*args, **kwargs)


def test_check_login_without_browser(monkeypatch):
    monkeypatch.setattr(boss_app, "automation", None)

    result = asyncio.run(boss_app.check_login_status())

    assert result["browser_running"] is False
    assert result["logged_in"] is False
    assert "启动登录" in result["message"]


def test_check_login_starts_monitor_only_after_verified(monkeypatch):
    automation = _FakeAutomation(logged_in=True)
    created = []

    def fake_create_task(coro):
        coro.close()
        task = _FakeTask()
        created.append(task)
        return task

    monkeypatch.setattr(boss_app, "automation", automation)
    monkeypatch.setattr(boss_app, "monitor_task", None)
    monkeypatch.setattr(boss_app, "monitor_paused", True)
    monkeypatch.setattr(boss_app, "_run_pw", _direct_run)
    monkeypatch.setattr(boss_app.asyncio, "create_task", fake_create_task)

    result = asyncio.run(boss_app.check_login_status())

    assert result["logged_in"] is True
    assert automation.saved is True
    assert boss_app.monitor_paused is False
    assert len(created) == 1


def test_check_login_logged_out_message_is_neutral(monkeypatch):
    automation = _FakeAutomation(logged_in=False)
    monkeypatch.setattr(boss_app, "automation", automation)
    monkeypatch.setattr(boss_app, "monitor_task", None)
    monkeypatch.setattr(boss_app, "_run_pw", _direct_run)

    result = asyncio.run(boss_app.check_login_status())

    assert result["logged_in"] is False
    assert result["message"] == "请登录"


def test_login_check_uses_current_page_without_opening_probe():
    class FakePage:
        def __init__(self):
            self.url = "about:blank"
            self.visited = []

        def goto(self, url, **_kwargs):
            self.url = url
            self.visited.append(url)

        def wait_for_timeout(self, _milliseconds):
            return None

    automation = BossAutomation.__new__(BossAutomation)
    automation._ctx = object()  # 故意不提供 new_page，确保不会再创建第二个探针页面。
    automation.page = FakePage()
    automation.is_logged_in_page = lambda: False
    automation.check_page_safety = lambda: False

    assert automation.check_login_verified() is False
    assert automation.page.visited == ["https://www.zhipin.com/web/user/"]


def test_logout_clears_session_and_keeps_browser(monkeypatch):
    automation = _FakeAutomation(logout_ok=True)
    monitor = _FakeTask()
    monkeypatch.setattr(boss_app, "automation", automation)
    monkeypatch.setattr(boss_app, "monitor_task", monitor)
    monkeypatch.setattr(boss_app, "monitor_paused", False)
    monkeypatch.setattr(boss_app, "_run_pw", _direct_run)

    result = asyncio.run(boss_app.logout_boss())

    assert result["status"] == "ok"
    assert result["browser_running"] is True
    assert result["logged_in"] is False
    assert automation.logged_out is True
    assert boss_app.automation is automation
    assert monitor.cancelled is True
    assert boss_app.monitor_task is None
    assert boss_app.monitor_paused is True


def test_legacy_dashboard_uses_login_heartbeat_without_manual_check():
    html = (Path(__file__).parents[1] / "static" / "dashboard.html").read_text(encoding="utf-8")

    assert 'id="btnStart"' in html
    assert "启动登录" in html
    assert 'id="btnCheckLogin"' not in html
    assert "checkLoginStatus" not in html
    assert "/api/system/heartbeat" in html
    assert "/api/system/logout" in html
    assert "showStatusModal" in html
    assert "overlay.querySelector('[data-action=\"close\"]').focus()" not in html
    assert ".status-result-modal .confirm-actions .btn" in html
    assert "justify-content:center" in html
    assert "bossLoginDock" not in html
    assert "/api/system/login-panel" not in html
