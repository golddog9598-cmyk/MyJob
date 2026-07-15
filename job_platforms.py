#!/usr/bin/env python3
"""Shared Playwright platform adapters for MyJob.

The browser context remains owned by ``BossAutomation``. Each recruitment
platform gets its own page so cookies stay isolated by domain while the user
only needs one visible browser process.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlencode, urljoin, urlparse


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlatformSpec:
    id: str
    label: str
    short_label: str
    home_url: str
    login_url: str
    domains: tuple[str, ...]


PLATFORM_SPECS: Dict[str, PlatformSpec] = {
    "boss": PlatformSpec(
        id="boss",
        label="BOSS 直聘",
        short_label="BOSS",
        home_url="https://www.zhipin.com/web/user/",
        login_url="https://www.zhipin.com/web/user/",
        domains=("zhipin.com",),
    ),
    "zhilian": PlatformSpec(
        id="zhilian",
        label="智联招聘",
        short_label="智联",
        home_url="https://www.zhaopin.com/",
        login_url="https://passport.zhaopin.com/login",
        domains=("zhaopin.com",),
    ),
    "liepin": PlatformSpec(
        id="liepin",
        label="猎聘",
        short_label="猎聘",
        home_url="https://www.liepin.com/",
        login_url="https://www.liepin.com/login",
        domains=("liepin.com",),
    ),
    "job51": PlatformSpec(
        id="job51",
        label="前程无忧",
        short_label="前程无忧",
        home_url="https://we.51job.com/pc/",
        login_url="https://login.51job.com/login.php",
        domains=("51job.com",),
    ),
}

_PLATFORM_ALIASES = {
    "51job": "job51",
    "job51": "job51",
    "前程无忧": "job51",
    "智联": "zhilian",
    "智联招聘": "zhilian",
    "猎聘": "liepin",
    "boss": "boss",
    "boss直聘": "boss",
}


def normalize_platform(value: str | None) -> str:
    raw = (value or "boss").strip()
    normalized = _PLATFORM_ALIASES.get(raw.lower(), _PLATFORM_ALIASES.get(raw, raw.lower()))
    if normalized not in PLATFORM_SPECS:
        raise ValueError(f"不支持的招聘平台: {value}")
    return normalized


def platform_label(value: str | None) -> str:
    return PLATFORM_SPECS[normalize_platform(value)].label


def platform_catalog() -> list[dict]:
    return [
        {"id": spec.id, "label": spec.label, "short_label": spec.short_label}
        for spec in PLATFORM_SPECS.values()
    ]


# The mappings cover the cities already exposed by the MyJob UI and the most
# common target cities. Unknown cities fall back to each platform's nationwide
# search instead of sending a code from another platform.
ZHILIAN_CITY_CODES = {
    "全国": "0", "北京": "530", "上海": "538", "天津": "531", "重庆": "551",
    "广州": "763", "深圳": "765", "杭州": "653", "南京": "635", "苏州": "639",
    "武汉": "736", "成都": "801", "西安": "854", "长沙": "749", "郑州": "719",
    "济南": "702", "青岛": "703", "合肥": "664", "福州": "681", "厦门": "682",
    "沈阳": "599", "大连": "600", "宁波": "654", "无锡": "636", "东莞": "766",
    "佛山": "768", "昆明": "831", "南宁": "785", "南昌": "691", "贵阳": "822",
    "石家庄": "565", "太原": "576", "哈尔滨": "622", "长春": "613", "兰州": "895",
}

LIEPIN_CITY_CODES = {
    "全国": "410", "北京": "010", "上海": "020", "广州": "050020", "深圳": "050090",
    "天津": "030", "重庆": "040", "苏州": "060080", "南京": "060020", "杭州": "070020",
    "武汉": "170020", "成都": "280020", "西安": "270020", "大连": "210040",
    "宁波": "070030", "无锡": "060100", "长沙": "180020", "青岛": "250070",
    "郑州": "150020", "合肥": "190020", "厦门": "080040", "福州": "080020",
    "济南": "250020", "沈阳": "210020", "东莞": "050100", "佛山": "050040",
    "常州": "060040", "南通": "060060", "徐州": "060070", "温州": "070040",
    "嘉兴": "070050", "绍兴": "070060", "金华": "070070", "惠州": "050110",
    "中山": "050120", "珠海": "050130", "泉州": "080050", "烟台": "250080",
    "石家庄": "140020", "哈尔滨": "160020", "长春": "230020", "南昌": "200020",
    "昆明": "310020", "贵阳": "120020", "南宁": "110020", "海口": "130020",
    "太原": "260020", "呼和浩特": "220020", "兰州": "320020", "银川": "330020",
    "西宁": "240020", "拉萨": "290020", "乌鲁木齐": "300020",
}

JOB51_CITY_CODES = {
    "北京": "010000", "上海": "020000", "广州": "030200", "深圳": "040000",
    "天津": "050000", "重庆": "060000", "南京": "070200", "苏州": "070300",
    "无锡": "070400", "杭州": "080200", "宁波": "080300", "成都": "090200",
    "福州": "110200", "厦门": "110300", "济南": "120200", "青岛": "120300",
    "南昌": "130200", "南宁": "140200", "合肥": "150200", "郑州": "170200",
    "武汉": "180200", "长沙": "190200", "西安": "200200", "沈阳": "230200",
    "大连": "230300", "贵阳": "240200", "昆明": "250200", "东莞": "030800",
    "佛山": "030600",
}

_ZHILIAN_SALARY = {"403": "4001,6000", "404": "6001,10000", "405": "10001,25000", "406": "25001,50000", "407": "50001,9999999"}
_ZHILIAN_EXPERIENCE = {102: "-1", 103: "0001", 104: "0103", 105: "0305", 106: "0510", 107: "1099", 108: "-1"}
_ZHILIAN_DEGREE = {202: "5", 203: "4", 204: "3", 205: "1", 206: "7", 208: "12", 209: "9"}
_ZHILIAN_JOB_TYPE = {"1": "2", "2": "1", "3": "4"}

_LIEPIN_SALARY = {"403": "1", "404": "1", "405": "3", "406": "5", "407": "6"}
_LIEPIN_EXPERIENCE = {102: "1", 103: "0$1", 104: "1$3", 105: "3$5", 106: "5$10", 107: "10$999", 108: "2"}
_LIEPIN_DEGREE = {202: "050", 203: "040", 204: "030", 205: "010", 206: "080", 208: "060", 209: "090"}

_JOB51_EXPERIENCE = {102: "01", 103: "02", 104: "02", 105: "03", 106: "04", 107: "05", 108: "01"}
_JOB51_DEGREE = {202: "03", 203: "04", 204: "05", 205: "06", 206: "02", 208: "02", 209: "01"}
_JOB51_JOB_TYPE = {"1": "01", "2": "02", "3": "03"}


def _mapped(mapping: dict, value: Any) -> str:
    if value is None or value == "":
        return ""
    return str(mapping.get(value, mapping.get(str(value), "")))


def build_search_url(
    platform: str,
    keyword: str,
    city: str = "全国",
    *,
    salary: str = "",
    experience: Optional[int] = None,
    degree: Optional[int] = None,
    job_type: str = "",
) -> str:
    platform = normalize_platform(platform)
    city = (city or "全国").strip()
    keyword = (keyword or "").strip()

    if platform == "zhilian":
        city_code = ZHILIAN_CITY_CODES.get(city, "0")
        params = {
            "sl": _mapped(_ZHILIAN_SALARY, salary),
            "we": _mapped(_ZHILIAN_EXPERIENCE, experience),
            "el": _mapped(_ZHILIAN_DEGREE, degree),
            "et": _mapped(_ZHILIAN_JOB_TYPE, job_type),
        }
        query = urlencode({key: value for key, value in params.items() if value})
        base = f"https://www.zhaopin.com/sou/jl{city_code}/p1"
        return f"{base}?{query}" if query else base

    if platform == "liepin":
        city_code = LIEPIN_CITY_CODES.get(city, LIEPIN_CITY_CODES["全国"])
        params = {
            "city": city_code,
            "dq": city_code,
            "salaryCode": _mapped(_LIEPIN_SALARY, salary),
            "workYearCode": _mapped(_LIEPIN_EXPERIENCE, experience),
            "eduLevel": _mapped(_LIEPIN_DEGREE, degree),
            "currentPage": "0",
            "key": keyword,
        }
        return "https://www.liepin.com/zhaopin/?" + urlencode(
            {key: value for key, value in params.items() if value != ""}
        )

    if platform == "job51":
        params = {
            "jobArea": JOB51_CITY_CODES.get(city, ""),
            "workYear": _mapped(_JOB51_EXPERIENCE, experience),
            "degree": _mapped(_JOB51_DEGREE, degree),
            "jobType": _mapped(_JOB51_JOB_TYPE, job_type),
            "keyword": keyword,
        }
        return "https://we.51job.com/pc/search?" + urlencode(
            {key: value for key, value in params.items() if value != ""}
        )

    raise ValueError("BOSS 搜索 URL 由 BossScraper 构建")


_LOGIN_RULES = {
    "zhilian": {
        "negative": [
            "a.home-header__c-no-login",
            "input[type='password']",
            "div.passport-login",
            "#J_loginWrap",
        ],
        "positive": [
            "a[href*='i.zhaopin.com']",
            "[class*='home-header__user']",
            "[class*='user-center']",
        ],
        "positive_paths": ["i.zhaopin.com"],
        "positive_text": ["我的简历", "求职中心", "投递记录"],
    },
    "liepin": {
        "negative": [
            "#header-quick-menu-login",
            "input[type='password']",
            "[class*='login-form']",
        ],
        "positive": [
            "#header-quick-menu-user-info",
            "img.header-quick-menu-user-photo",
            ".header-quick-menu-user-photo",
        ],
        "positive_paths": [],
        "positive_text": ["我的简历", "求职者中心", "应聘记录"],
    },
    "job51": {
        "negative": [
            "span.login.loginBtnClick",
            "input[type='password']",
            "[class*='login-form']",
        ],
        "positive": [
            "a.uname.e_icon.at",
            "a[href*='/pc/my/myjob']",
            ".login-info .username",
            ".user-info .username",
        ],
        "positive_paths": ["/pc/my/"],
        "positive_text": ["我的简历", "我的申请", "个人中心"],
    },
}


_EXTRACTORS = {
    "zhilian": r"""(limit) => {
        const pick = (root, selectors) => {
            for (const selector of selectors) {
                const element = root.querySelector(selector);
                const value = (element?.getAttribute('title') || element?.innerText || '').trim();
                if (value) return value;
            }
            return '';
        };
        return Array.from(document.querySelectorAll('div.joblist-box__item')).slice(0, limit).map(card => {
            const anchor = card.querySelector('a.jobinfo__name, a[href*="jobdetail"]');
            return {
                title: pick(card, ['a.jobinfo__name', '[class*="jobinfo__name"]']),
                salary: pick(card, ['p.jobinfo__salary', '[class*="salary"]']),
                company: pick(card, ['a.companyinfo__name', '.companyinfo__name', '[class*="companyinfo__name"]']),
                city: pick(card, ['div.jobinfo__other-info div.jobinfo__other-info-item > span', '[class*="job-area"]']),
                experience: pick(card, ['div.jobinfo__other-info-item:nth-child(2)', '[class*="experience"]']),
                education: pick(card, ['div.jobinfo__other-info-item:nth-child(3)', '[class*="education"]']),
                url: anchor?.href || anchor?.getAttribute('href') || '',
            };
        });
    }""",
    "liepin": r"""(limit) => {
        const pick = (root, selectors) => {
            for (const selector of selectors) {
                const element = root.querySelector(selector);
                const value = (element?.getAttribute('title') || element?.innerText || '').trim();
                if (value) return value;
            }
            return '';
        };
        return Array.from(document.querySelectorAll('div[class*="job-card-pc-container"]')).slice(0, limit).map(card => {
            const anchors = Array.from(card.querySelectorAll('a[href]'));
            const anchor = anchors.find(item => /\/job\//.test(item.href) || /job\/detail/.test(item.href)) || anchors[0];
            const labels = pick(card, ['[class*="job-labels"]', '[class*="job-card-label"]']);
            const labelParts = labels.split(/\s+|·/).filter(Boolean);
            return {
                title: pick(card, ['[class*="job-title"]', '[class*="job-name"]', 'h3']),
                salary: pick(card, ['[class*="job-salary"]', '[class*="salary"]']),
                company: pick(card, ['[class*="company-name"]', '[class*="company-title"]']),
                city: pick(card, ['[class*="job-dq"]', '[class*="job-area"]', '[class*="area"]']),
                experience: labelParts.find(value => /年|应届|经验/.test(value)) || '',
                education: labelParts.find(value => /本科|硕士|博士|大专|学历/.test(value)) || '',
                hr_name: pick(card, ['[class*="recruiter-name"]', '[class*="recruiter"] [class*="name"]']),
                url: anchor?.href || anchor?.getAttribute('href') || '',
            };
        });
    }""",
    "job51": r"""(limit) => {
        const pick = (root, selectors) => {
            for (const selector of selectors) {
                const element = root.querySelector(selector);
                const value = (element?.getAttribute('title') || element?.innerText || '').trim();
                if (value) return value;
            }
            return '';
        };
        const seen = new Set();
        const result = [];
        const anchors = document.querySelectorAll('a.jname[href], a[href*="/pc/jobdetail"], a[href*="jobs.51job.com"]');
        for (const anchor of anchors) {
            if (result.length >= limit) break;
            const href = anchor.href || anchor.getAttribute('href') || '';
            if (!href || seen.has(href)) continue;
            seen.add(href);
            const card = anchor.closest('.joblist-item, .e, [class*="joblist-item"]') || anchor.parentElement?.parentElement || anchor;
            const labels = (card.innerText || '').split('\n').map(value => value.trim()).filter(Boolean);
            result.push({
                title: (anchor.getAttribute('title') || anchor.innerText || '').trim(),
                salary: pick(card, ['.sal', '[class*="salary"]']),
                company: pick(card, ['a.cname', '.cname', '[class*="company"]']),
                city: pick(card, ['.d', '[class*="area"]', '[class*="location"]']),
                experience: labels.find(value => /年经验|应届|无需经验/.test(value)) || '',
                education: labels.find(value => /本科|硕士|博士|大专|学历/.test(value)) || '',
                url: href,
            });
        }
        return result;
    }""",
}


_RESULT_SELECTORS = {
    "zhilian": "div.joblist-box__item",
    "liepin": "div[class*='job-card-pc-container']",
    "job51": "a.jname[href], a[href*='/pc/jobdetail'], a[href*='jobs.51job.com']",
}


_APPLY_BUTTONS = {
    "zhilian": [
        "button.collect-and-apply__btn",
        "button:has-text('立即申请')",
        "button:has-text('申请职位')",
        "button:has-text('投递简历')",
    ],
    "liepin": [
        "button:has-text('聊一聊')",
        "button:has-text('立即沟通')",
        "button:has-text('应聘')",
        "button:has-text('投递简历')",
    ],
    "job51": [
        "button:has-text('申请职位')",
        "button:has-text('立即申请')",
        "button:has-text('投递简历')",
        "a:has-text('申请职位')",
    ],
}


class PlatformManager:
    """Manage platform pages inside the existing Playwright context."""

    def __init__(self, automation: Any):
        self.automation = automation
        self.pages: dict[str, Any] = {"boss": automation.page}
        self.active_platform = "boss"
        self.login_status = {platform: False for platform in PLATFORM_SPECS}
        self.page_open_status = {
            platform: platform == "boss" and automation.page is not None
            for platform in PLATFORM_SPECS
        }

    @property
    def context(self):
        return self.automation._ctx

    def _page_is_closed(self, page: Any) -> bool:
        try:
            return bool(page.is_closed())
        except Exception:
            return False

    def get_page(self, platform: str, create: bool = True):
        platform = normalize_platform(platform)
        if platform == "boss":
            self.pages["boss"] = self.automation.page
        page = self.pages.get(platform)
        if page is not None and not self._page_is_closed(page):
            self.page_open_status[platform] = True
            return page
        self.page_open_status[platform] = False
        if not create:
            return None
        if self.context is None:
            raise RuntimeError("浏览器上下文尚未启动")
        page = self.context.new_page()
        page.set_default_timeout(30000)
        self.pages[platform] = page
        self.page_open_status[platform] = True
        return page

    def _safe_goto(self, page: Any, url: str):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception:
            current = ""
            try:
                current = page.url or ""
            except Exception:
                pass
            if not current or current == "about:blank":
                raise

    def open_platform(self, platform: str, force_login: bool = False) -> dict:
        platform = normalize_platform(platform)
        spec = PLATFORM_SPECS[platform]
        page = self.get_page(platform)
        logged_in_before = self.is_logged_in(platform)
        target = spec.login_url if force_login and not logged_in_before else spec.home_url
        self._safe_goto(page, target)
        try:
            page.bring_to_front()
        except Exception:
            pass
        self.active_platform = platform
        return {
            "status": "opened",
            "platform": platform,
            "label": spec.label,
            "url": getattr(page, "url", target),
            "logged_in": self.is_logged_in(platform),
        }

    def _evaluate_login(self, platform: str, page: Any) -> bool:
        rules = _LOGIN_RULES[platform]
        try:
            hostname = (urlparse(getattr(page, "url", "") or "").hostname or "").lower()
        except Exception:
            return False
        if not any(
            hostname == domain or hostname.endswith("." + domain)
            for domain in PLATFORM_SPECS[platform].domains
        ):
            return False
        try:
            evidence = page.evaluate(
                """rules => {
                    const visible = element => {
                        if (!element) return false;
                        const style = getComputedStyle(element);
                        const rect = element.getBoundingClientRect();
                        return style.display !== 'none' && style.visibility !== 'hidden'
                            && style.opacity !== '0' && rect.width > 0 && rect.height > 0;
                    };
                    const hasVisible = selectors => selectors.some(selector =>
                        Array.from(document.querySelectorAll(selector)).some(visible)
                    );
                    const body = (document.body?.innerText || '').slice(0, 5000);
                    return {
                        negative: hasVisible(rules.negative),
                        positive: hasVisible(rules.positive),
                        path: rules.positive_paths.some(value => location.href.includes(value)),
                        text: rules.positive_text.some(value => body.includes(value)),
                    };
                }""",
                rules,
            )
        except Exception:
            return False
        if not isinstance(evidence, dict) or evidence.get("negative"):
            return False
        # Public headers can contain phrases such as “我的简历” before login.
        # Require an account-specific control or an authenticated personal path;
        # text alone is never sufficient evidence of a valid session.
        return bool(evidence.get("positive") or evidence.get("path"))

    def is_logged_in(self, platform: str) -> bool:
        platform = normalize_platform(platform)
        page = self.get_page(platform, create=False)
        if page is None:
            self.login_status[platform] = False
            return False
        if platform == "boss":
            try:
                logged_in = bool(self.automation.check_logged_in())
            except Exception:
                logged_in = False
        else:
            logged_in = self._evaluate_login(platform, page)
        self.login_status[platform] = logged_in
        return logged_in

    def check_login(self, platform: str, navigate: bool = True) -> dict:
        platform = normalize_platform(platform)
        spec = PLATFORM_SPECS[platform]
        page = self.get_page(platform)
        self.active_platform = platform

        if platform == "boss":
            logged_in = bool(
                self.automation.check_login_verified()
                if navigate
                else self.automation.check_logged_in()
            )
        else:
            logged_in = self._evaluate_login(platform, page)
            if not logged_in and navigate:
                self._safe_goto(page, spec.home_url)
                logged_in = self._evaluate_login(platform, page)
                if not logged_in:
                    self._safe_goto(page, spec.login_url)

        self.login_status[platform] = logged_in
        try:
            page.bring_to_front()
        except Exception:
            pass
        if logged_in:
            self.automation._save_state()
        return {
            "browser_running": True,
            "platform": platform,
            "label": spec.label,
            "logged_in": logged_in,
            "message": f"{spec.label} 已登录，可以开始搜索和投递" if logged_in else "请登录",
            "url": getattr(page, "url", ""),
        }

    @staticmethod
    def _cookie_matches(cookie: dict, domains: Iterable[str]) -> bool:
        domain = str(cookie.get("domain") or "").lower().lstrip(".")
        return any(domain == suffix or domain.endswith("." + suffix) for suffix in domains)

    def logout(self, platform: str) -> dict:
        platform = normalize_platform(platform)
        spec = PLATFORM_SPECS[platform]
        page = self.get_page(platform)
        try:
            if any(domain in (getattr(page, "url", "") or "") for domain in spec.domains):
                page.evaluate(
                    """async () => {
                        try { localStorage.clear(); } catch (error) {}
                        try { sessionStorage.clear(); } catch (error) {}
                        try {
                            const keys = await caches.keys();
                            await Promise.all(keys.map(key => caches.delete(key)));
                        } catch (error) {}
                    }"""
                )
        except Exception:
            pass

        all_cookies = self.context.cookies()
        keep = [cookie for cookie in all_cookies if not self._cookie_matches(cookie, spec.domains)]
        self.context.clear_cookies()
        if keep:
            self.context.add_cookies(keep)
        self._safe_goto(page, spec.login_url)
        self.login_status[platform] = False
        self.automation._save_state()
        return {
            "status": "ok",
            "browser_running": True,
            "platform": platform,
            "logged_in": False,
            "message": f"已退出 {spec.label} 登录，浏览器仍保持运行",
        }

    def status(self) -> dict:
        return {
            "active_platform": self.active_platform,
            "platforms": {
                platform: {
                    "label": spec.label,
                    # Status is read by FastAPI outside Playwright's owner thread.
                    # The heartbeat refreshes these plain booleans on the owner thread.
                    "page_open": bool(self.page_open_status.get(platform)),
                    "logged_in": bool(self.login_status.get(platform)),
                }
                for platform, spec in PLATFORM_SPECS.items()
            },
        }

    def login_heartbeat(self) -> dict:
        """Validate every open platform page without navigation or page creation."""
        platform_states = {}
        for platform, spec in PLATFORM_SPECS.items():
            page = self.get_page(platform, create=False)
            page_open = page is not None and not self._page_is_closed(page)
            self.page_open_status[platform] = page_open
            logged_in = self.is_logged_in(platform) if page_open else False
            platform_states[platform] = {
                "label": spec.label,
                "page_open": page_open,
                "logged_in": logged_in,
            }
        return {
            "active_platform": self.active_platform,
            "platforms": platform_states,
        }

    def _require_login(self, platform: str):
        if self.is_logged_in(platform):
            return
        self.check_login(platform, navigate=True)
        if not self.login_status.get(platform):
            raise RuntimeError(f"请先登录 {PLATFORM_SPECS[platform].label}")

    def _fill_zhilian_keyword(self, page: Any, keyword: str):
        selectors = [
            "input[placeholder*='职位']",
            "input[placeholder*='公司']",
            "input[name='kw']",
            "input[class*='search']",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible():
                    locator.fill(keyword)
                    locator.press("Enter")
                    return
            except Exception:
                continue
        raise RuntimeError("智联招聘搜索框未找到，页面结构可能已更新")

    def search(
        self,
        platform: str,
        keyword: str,
        city: str = "全国",
        *,
        salary: str = "",
        experience: Optional[int] = None,
        degree: Optional[int] = None,
        job_type: str = "",
        limit: int = 60,
    ) -> list[dict]:
        platform = normalize_platform(platform)
        if platform == "boss":
            raise ValueError("BOSS 搜索应继续使用 BossScraper.search")
        self._require_login(platform)
        page = self.get_page(platform)
        url = build_search_url(
            platform,
            keyword,
            city,
            salary=salary,
            experience=experience,
            degree=degree,
            job_type=job_type,
        )
        self._safe_goto(page, url)
        if platform == "zhilian":
            self._fill_zhilian_keyword(page, keyword)

        selector = _RESULT_SELECTORS[platform]
        try:
            page.wait_for_selector(selector, state="attached", timeout=18000)
        except Exception:
            if not self._evaluate_login(platform, page):
                raise RuntimeError(f"{PLATFORM_SPECS[platform].label} 登录状态已失效")
            raise RuntimeError(f"{PLATFORM_SPECS[platform].label} 未加载出岗位列表")

        for _ in range(4):
            try:
                page.evaluate("() => window.scrollBy(0, Math.max(520, window.innerHeight * 0.8))")
                page.wait_for_timeout(350)
            except Exception:
                break

        raw_jobs = page.evaluate(_EXTRACTORS[platform], max(1, min(int(limit), 300))) or []
        jobs = []
        seen = set()
        for raw in raw_jobs:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or "").strip()
            job_url = normalize_job_url(platform, raw.get("url") or "")
            if not title or not job_url or job_url in seen:
                continue
            seen.add(job_url)
            jobs.append(
                {
                    "platform": platform,
                    "title": title,
                    "salary": str(raw.get("salary") or "").strip(),
                    "company": str(raw.get("company") or "").strip(),
                    "city": str(raw.get("city") or city or "").strip(),
                    "experience": str(raw.get("experience") or "").strip(),
                    "education": str(raw.get("education") or "").strip(),
                    "url": job_url,
                    "description": "",
                    "hr_name": str(raw.get("hr_name") or "").strip(),
                    "hr_title": str(raw.get("hr_title") or "").strip(),
                }
            )
        self.active_platform = platform
        self.login_status[platform] = True
        return jobs[: max(1, min(int(limit), 300))]

    def apply_to_job(self, platform: str, job_url: str, greeting: str = "") -> dict:
        platform = normalize_platform(platform)
        if platform == "boss":
            return self.automation.apply_to_job(job_url, greeting)
        self._require_login(platform)
        page = self.get_page(platform)
        self._safe_goto(page, normalize_job_url(platform, job_url))
        try:
            body = page.inner_text("body")[:2000]
        except Exception:
            body = ""
        if any(text in body for text in ("访问验证", "安全验证", "滑块验证", "操作频繁")):
            return {"success": False, "message": "检测到平台安全验证，请在浏览器中人工处理"}
        if any(text in body for text in ("已申请", "已投递", "已沟通", "继续沟通")):
            return {"success": True, "already_applied": True, "message": "该岗位已处理过"}

        button = None
        for selector in _APPLY_BUTTONS[platform]:
            try:
                candidate = page.locator(selector).first
                if candidate.is_visible():
                    button = candidate
                    break
            except Exception:
                continue
        if button is None:
            return {
                "success": False,
                "message": f"未找到 {PLATFORM_SPECS[platform].label} 投递按钮，已保留岗位详情页供人工确认",
            }
        try:
            button.click()
            page.wait_for_timeout(900)
        except Exception as exc:
            return {"success": False, "message": f"点击投递按钮失败: {exc}"}

        greeting_sent = False
        if greeting:
            for selector in (
                "textarea[placeholder*='输入']",
                "textarea[placeholder*='沟通']",
                "div[contenteditable='true']",
            ):
                try:
                    field = page.locator(selector).first
                    if field.is_visible():
                        field.fill(greeting)
                        send = page.locator("button:has-text('发送')").first
                        if send.is_visible():
                            send.click()
                            greeting_sent = True
                        break
                except Exception:
                    continue

        try:
            confirmation_text = page.inner_text("body")[:4000]
        except Exception:
            confirmation_text = ""
        if any(text in confirmation_text for text in ("访问验证", "安全验证", "滑块验证", "操作频繁")):
            return {"success": False, "message": "检测到平台安全验证，请在浏览器中人工处理"}
        confirmed = greeting_sent or any(
            text in confirmation_text
            for text in ("投递成功", "申请成功", "已申请", "已投递", "已沟通", "继续沟通")
        )
        if not confirmed:
            return {
                "success": False,
                "message": f"已点击 {PLATFORM_SPECS[platform].label} 投递入口，但未检测到成功结果，请在浏览器中人工确认",
            }
        self.automation._save_state()
        return {
            "success": True,
            "message": f"已在 {PLATFORM_SPECS[platform].label} 提交岗位申请",
            "greeting_sent": greeting_sent,
        }


def normalize_job_url(platform: str, url: str) -> str:
    platform = normalize_platform(platform)
    value = (url or "").strip()
    if not value:
        return ""
    bases = {
        "boss": "https://www.zhipin.com",
        "zhilian": "https://www.zhaopin.com",
        "liepin": "https://www.liepin.com",
        "job51": "https://we.51job.com",
    }
    return urljoin(bases[platform], value)
