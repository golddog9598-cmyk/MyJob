from urllib.parse import parse_qs, urlparse

from boss_firefox import BossScraper


def test_search_accepts_area_business_and_forwards_boss_parameter():
    class FakePage:
        url = ""

        def goto(self, url, **_kwargs):
            self.url = url

    scraper = BossScraper.__new__(BossScraper)
    scraper.page = FakePage()
    scraper._wait_for_jobs_loaded = lambda **_kwargs: 1
    scraper._scroll_all = lambda: None
    scraper._extract_job_cards = lambda: [
        {
            "title": "AI Agent 工程师",
            "salary": "20-30K",
            "company": "示例公司",
            "city": "深圳",
            "url": "https://example.com/job",
        }
    ]

    jobs = scraper.search("AI Agent", "101280600", area_business="440305")
    query = parse_qs(urlparse(scraper.page.url).query)
    assert query["query"] == ["AI Agent"]
    assert query["city"] == ["101280600"]
    assert query["areaBusiness"] == ["440305"]
    assert jobs[0]["city"] == "深圳"


def test_authenticated_page_content_wins_over_stale_login_url():
    class FakePage:
        url = "https://www.zhipin.com/web/user/?ka=header-login"

        def inner_text(self, _selector):
            return "首页 职位 消息 简历 已沟通 发简历"

    scraper = BossScraper.__new__(BossScraper)
    scraper.page = FakePage()
    assert scraper._login_prompt_visible() is False


def test_visible_login_ui_wins_over_chat_page_text():
    class FakePage:
        url = "https://www.zhipin.com/web/geek/chat"

        def inner_text(self, _selector):
            return "聊天 消息 沟通中"

        def evaluate(self, _script):
            return True

    scraper = BossScraper.__new__(BossScraper)
    scraper.page = FakePage()
    assert scraper._login_prompt_visible() is True


def test_login_prompt_wins_over_authenticated_keywords():
    class FakePage:
        url = "https://www.zhipin.com/web/geek/chat"

        def inner_text(self, _selector):
            return "聊天 消息 请登录 扫码登录"

        def evaluate(self, _script):
            return False

    scraper = BossScraper.__new__(BossScraper)
    scraper.page = FakePage()
    assert scraper._login_prompt_visible() is True


def test_absence_of_login_prompt_is_not_enough_to_claim_login():
    class FakePage:
        url = "https://www.zhipin.com/web/geek/chat"

        def inner_text(self, _selector):
            return "聊天 消息 沟通中"

        def evaluate(self, _script):
            return False

    scraper = BossScraper.__new__(BossScraper)
    scraper.page = FakePage()
    assert scraper.is_logged_in_page() is False


def test_positive_identity_evidence_confirms_login():
    class FakePage:
        url = "https://www.zhipin.com/web/geek/chat"

        def __init__(self):
            self.calls = 0

        def inner_text(self, _selector):
            return "聊天 消息 我的简历 个人中心"

        def evaluate(self, _script):
            self.calls += 1
            return self.calls > 1

    scraper = BossScraper.__new__(BossScraper)
    scraper.page = FakePage()
    assert scraper.is_logged_in_page() is True
