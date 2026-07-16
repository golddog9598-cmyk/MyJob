from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_boss_search_uses_source_route_and_nanning_city_code():
    background = (ROOT / "browser_extension/background.js").read_text(encoding="utf-8")
    assert "'南宁': '101300100'" in background
    assert "https://www.zhipin.com/web/geek/job?" in background
    assert "https://www.zhipin.com/web/geek/jobs?" not in background


def test_boss_search_waits_for_dynamic_job_results():
    background = (ROOT / "browser_extension/background.js").read_text(encoding="utf-8")
    assert "const deadline = Date.now() + 15000" in background
    assert "if (result?.jobs?.length) break" in background


def test_boss_parser_ignores_empty_job_detail_navigation_link():
    content = (ROOT / "browser_extension/platformContent.js").read_text(encoding="utf-8")
    assert r"/\/job_detail\/[^/?#]+/" in content


def test_boss_parser_preserves_real_salary_and_negotiable_value():
    content = (ROOT / "browser_extension/platformContent.js").read_text(encoding="utf-8")
    assert "function decodeBossText(value)" in content
    assert "code >= 0xE031 && code <= 0xE03A" in content
    assert "|面议/i.test(value)" in content


def test_search_refreshes_stale_content_adapter_before_extracting_jobs():
    background = (ROOT / "browser_extension/background.js").read_text(encoding="utf-8")
    content = (ROOT / "browser_extension/platformContent.js").read_text(encoding="utf-8")
    assert "CONTENT_ADAPTER_VERSION = '0.0.12'" in background
    assert "CONTENT_ADAPTER_VERSION = '0.0.12'" in content
    assert "async function ensureCurrentContentAdapter(tabId)" in background
    assert "await chrome.tabs.reload(tabId)" in background
    assert "await ensureCurrentContentAdapter(tab.id)" in background
    assert "adapter_version: CONTENT_ADAPTER_VERSION" in content
