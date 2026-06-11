"""BOSS 直聘地区/城市/区数据本地代理。

数据来源：BOSS 公开 API（参考 https://www.zhipin.com/wapi/zpCommon/data/city.json）。
结果在内存中按需缓存，进程重启不持久化；如需持久化可在 SQLite 加 geo_cache 表。
调用失败时返回空 dict / 空 list，调用方需做兜底。
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

CITY_URL = "https://www.zhipin.com/wapi/zpCommon/data/city.json"
DISTRICT_URL = "https://www.zhipin.com/wapi/zpCommon/data/businessDistrict.json"

_cache: Dict[str, Any] = {
    "cities_ts": 0.0,  # 上次拉城市列表时间
    "cities": [],  # List[{name, code}]
    "city_by_name": {},  # name -> code
    "city_by_code": {},  # code -> name
    "districts_ts": {},  # city_code -> 上次拉取时间
    "districts": {},  # city_code -> List[{name, code}]
    "district_by_name": {},  # city_code -> {name: code}
    "district_by_code": {},  # city_code -> {code: name}
    "ttl_sec": 6 * 3600,  # 缓存 6 小时
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.zhipin.com/web/geek/job",
}


def _http_json(url: str, params: Optional[dict] = None, timeout: float = 12.0) -> Optional[dict]:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as cli:
            r = cli.get(url, params=params or {}, headers=_HEADERS)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _parse_cities(data: dict) -> Tuple[List[dict], Dict[str, str], Dict[str, str]]:
    cities: List[dict] = []
    by_name: Dict[str, str] = {}
    by_code: Dict[str, str] = {}

    def walk(node: Any):
        if not isinstance(node, dict):
            return
        code = str(node.get("code") or "")
        name = node.get("name")
        if code and name:
            cities.append({"name": name, "code": code})
            # 后取同名覆盖（保留首个出现）
            by_name.setdefault(name, code)
            by_code.setdefault(code, name)
        sub = node.get("subLevelModelList")
        if isinstance(sub, list):
            for x in sub:
                walk(x)

    for top in (data.get("data") or {}).get("cityList") or []:
        walk(top)
    return cities, by_name, by_code


def get_cities(force: bool = False) -> List[dict]:
    now = time.time()
    if not force and _cache["cities"] and (now - _cache["cities_ts"]) < _cache["ttl_sec"]:
        return _cache["cities"]

    raw = _http_json(CITY_URL)
    if not raw or raw.get("code") != 0:
        return _cache["cities"]  # 失败时返回旧缓存（可能为空）

    cities, by_name, by_code = _parse_cities(raw)
    _cache["cities"] = cities
    _cache["city_by_name"] = by_name
    _cache["city_by_code"] = by_code
    _cache["cities_ts"] = now
    return cities


def resolve_city_code(name_or_code: str) -> Optional[str]:
    """把城市名（如"广州"）或 city code（"101280100"）解析为 code。"""
    if not name_or_code:
        return None
    s = str(name_or_code).strip()
    if not s:
        return None
    if s.isdigit() and s in _cache["city_by_code"]:
        return s
    if not _cache["city_by_name"]:
        get_cities()
    if s in _cache["city_by_name"]:
        return _cache["city_by_name"][s]
    # 宽松匹配：去掉"市"后查
    if s.endswith("市") and s[:-1] in _cache["city_by_name"]:
        return _cache["city_by_name"][s[:-1]]
    # 兼容旧 city_code 直传
    if s in _cache["city_by_code"]:
        return s
    return None


def _parse_districts(data: dict) -> Tuple[List[dict], Dict[str, str], Dict[str, str]]:
    """解析 BOSS 区域接口返回。

    返回结构里只保留「区/县级」第一层（subLevelModelList 里有更细的商圈，
    不作为区匹配目标），每个区对应 BOSS 多区过滤参数 multiBusinessDistrict
    实际接收的 code。
    """
    districts: List[dict] = []
    by_name: Dict[str, str] = {}
    by_code: Dict[str, str] = {}

    bd = (data.get("zpData") or {}).get("businessDistrict") or {}
    for sub in bd.get("subLevelModelList") or []:
        if not isinstance(sub, dict):
            continue
        code = str(sub.get("code") or "")
        name = sub.get("name")
        if code and name:
            districts.append({"name": name, "code": code})
            by_name.setdefault(name, code)
            by_code.setdefault(code, name)

    return districts, by_name, by_code


def get_districts(city_code_or_name: str, force: bool = False) -> List[dict]:
    """取某城市下的区/商圈列表。传城市名或 city code 都行。"""
    city_code = resolve_city_code(city_code_or_name)
    if not city_code:
        return []

    now = time.time()
    cached = _cache["districts"].get(city_code)
    ts = _cache["districts_ts"].get(city_code, 0)
    if not force and cached and (now - ts) < _cache["ttl_sec"]:
        return cached

    raw = _http_json(DISTRICT_URL, params={"city": city_code})
    if not raw or raw.get("code") != 0:
        return cached or []

    districts, by_name, by_code = _parse_districts(raw)
    _cache["districts"][city_code] = districts
    _cache["districts_ts"][city_code] = now
    _cache["district_by_name"][city_code] = by_name
    _cache["district_by_code"][city_code] = by_code
    return districts


def resolve_district_code(city_code_or_name: str, district_name_or_code: str) -> Optional[str]:
    """把区/商圈名（如"张店区"）或区 code（"440118"）解析为 code。"""
    if not district_name_or_code:
        return None
    s = str(district_name_or_code).strip()
    if not s:
        return None
    # 已是 code
    if s.isdigit() and len(s) >= 6:
        return s
    city_code = resolve_city_code(city_code_or_name)
    if not city_code:
        return None
    if not _cache["district_by_name"].get(city_code):
        get_districts(city_code)
    by_name = _cache["district_by_name"].get(city_code, {})
    if s in by_name:
        return by_name[s]
    # 去掉"区"字后查
    for suffix in ("区", "县", "市"):
        if s.endswith(suffix) and s[: -len(suffix)] in by_name:
            return by_name[s[: -len(suffix)]]
    # 模糊匹配
    for name, code in by_name.items():
        if name in s or s in name:
            return code
    return None
