"""HTTPS client for the MyJob FastAPI backend."""

import os
from typing import Optional
from urllib.parse import urlparse

import httpx

BASE_URL = os.environ.get("MYJOB_API") or os.environ.get("LAKEJOB_API", "https://127.0.0.1:8010")
_verify_env = os.environ.get("MYJOB_TLS_VERIFY", "").strip().lower()
_local_https = urlparse(BASE_URL).hostname in {"127.0.0.1", "localhost", "::1"}
_verify_tls = _verify_env not in {"false", "0", "no"} if _verify_env else not _local_https
_client = httpx.Client(base_url=BASE_URL, verify=_verify_tls)


def _request(method: str, path: str, *, json=None, data=None, files=None, timeout=120):
    try:
        response = _client.request(method, path, json=json, data=data, files=files, timeout=timeout)
        if response.status_code == 401 and not path.startswith("/api/auth/"):
            username = os.environ.get("MYJOB_USERNAME") or os.environ.get("LAKEJOB_USERNAME", "")
            password = os.environ.get("MYJOB_PASSWORD") or os.environ.get("LAKEJOB_PASSWORD", "")
            if username and password:
                login = _client.post(
                    "/api/auth/login",
                    json={"username": username, "password": password},
                    timeout=30,
                )
                if login.is_success:
                    response = _client.request(method, path, json=json, data=data, files=files, timeout=timeout)
        return response
    except httpx.ConnectError:
        return httpx.Response(503, text="Cannot connect to MyJob server. Run `lakejob server --start` first.")


def _post(path: str, json=None, timeout=120):
    return _request("POST", path, json=json, timeout=timeout)


def _get(path: str, timeout=30):
    return _request("GET", path, timeout=timeout)


def _put(path: str, json=None, timeout=120):
    return _request("PUT", path, json=json, timeout=timeout)


def search(keyword: str, city: str = "", limit: int = 60):
    return _post("/api/jobs/search", {"keyword": keyword, "city": city or "", "limit": limit})


def status():
    return _get("/api/status")


def stats():
    return _get("/api/stats")


def jobs(status_filter=None, limit=50):
    q = f"?limit={limit}"
    if status_filter:
        q += f"&status={status_filter}"
    return _get(f"/api/jobs{q}")


def apply_one(job_url: str):
    return _post("/api/jobs/apply", {"job_url": job_url})


def apply_batch(job_urls: list):
    return _post("/api/jobs/apply-batch", {"job_urls": job_urls})


def scan():
    return _post("/api/jobs/scan", timeout=120)


def scan_and_apply():
    return _post("/api/jobs/scan-and-apply", timeout=300)


def conversations():
    return _get("/api/conversations")


def chat_messages(conv_id: int):
    return _get(f"/api/conversations/{conv_id}/messages")


def send_message(conv_id: int, content: str):
    return _post(f"/api/conversations/{conv_id}/send", {"content": content})


def doctor():
    return _get("/api/doctor")


def relogin():
    return _post("/api/system/relogin")


def analyze(job_url: str, title: str = "", company: str = "", desc: str = ""):
    return _post("/api/jobs/analyze", {"job_url": job_url, "job_title": title, "company": company, "description": desc})


def get_master_resume():
    return _get("/api/resumes/master")


def get_resume_templates():
    return _get("/api/resume-templates")


def save_master_resume(content: str, name: str = "主简历", source_format: str = "markdown"):
    return _put(
        "/api/resumes/master",
        {"name": name, "content": content, "source_format": source_format},
    )


def upload_master_resume(file_path: str, template_id: str = "ats_classic"):
    from pathlib import Path

    path = Path(file_path)
    try:
        with path.open("rb") as handle:
            return _request(
                "POST",
                "/api/resumes/upload",
                files={"file": (path.name, handle)},
                data={"template_id": template_id},
                timeout=180,
            )
    except OSError as exc:
        return httpx.Response(400, text=str(exc))


def set_master_resume_template(template_id: str):
    return _put("/api/resumes/master/template", {"template_id": template_id})


def export_master_resume(output_format: str = "docx", template_id: str = ""):
    from urllib.parse import urlencode

    query = urlencode({"format": output_format, "template_id": template_id})
    return _get(f"/api/resumes/master/export?{query}", timeout=180)


def tailor_resume(job_url: str, title: str = "", company: str = "", city: str = "", desc: str = ""):
    return _post(
        "/api/jobs/tailor-resume",
        {"job_url": job_url, "job_title": title, "company": company, "city": city, "description": desc},
        timeout=180,
    )


def get_tailored_resumes(job_url: str = ""):
    from urllib.parse import urlencode

    query = "?" + urlencode({"job_url": job_url}) if job_url else ""
    return _get(f"/api/resumes/tailored{query}")


def set_tailored_resume_status(resume_id: int, status: str):
    return _put(f"/api/resumes/tailored/{resume_id}/status", {"status": status})


def create_campaign(payload: dict):
    return _post("/api/campaigns", payload)


def get_campaigns():
    return _get("/api/campaigns")


def get_campaign(campaign_id: int):
    return _get(f"/api/campaigns/{campaign_id}")


def run_campaign(campaign_id: int):
    return _post(f"/api/campaigns/{campaign_id}/run", timeout=1800)


def set_campaign_status(campaign_id: int, status: str):
    return _put(f"/api/campaigns/{campaign_id}/status", {"status": status})


def get_shortlists():
    return _get("/api/shortlists")


def add_shortlist(job_url: str, title: str = "", company: str = "", salary: str = "", city: str = ""):
    return _post(
        "/api/shortlists", {"job_url": job_url, "title": title, "company": company, "salary": salary, "city": city}
    )


def remove_shortlist(sid: int):
    return _request("DELETE", f"/api/shortlists/{sid}", timeout=30)


def company_preview(
    keyword: str = "",
    city: str = "",
    company: str = "",
    company_id: str = "",
    districts: Optional[list] = None,
    company_size: Optional[list] = None,
    timeout: int = 180,
):
    """调用 GET /api/companies/preview。
    keyword 非空 → 跨公司聚合选最热；否则按 company/company_id 走单公司模式。

    新增：
      - districts: 区 code 列表（["440118", "440113"]），逗号拼接后透传到 URL
      - company_size: scale code 列表（["302", "303"]），同上
    """
    from urllib.parse import urlencode

    params = {}
    if keyword:
        params["keyword"] = keyword
    if city:
        params["city"] = city
    if company:
        params["company"] = company
    if company_id:
        params["company_id"] = company_id
    if districts:
        params["districts"] = ",".join(str(x) for x in districts if x)
    if company_size:
        params["company_size"] = ",".join(str(x) for x in company_size if x)
    qs = ("?" + urlencode(params)) if params else ""
    return _get(f"/api/companies/preview{qs}", timeout=timeout)


def smart_send(
    company: str = "",
    company_id: str = "",
    job_url: str = "",
    top_hr: Optional[dict] = None,
    hr_name: str = "",
    greeting: str = "",
    confirm: bool = False,
    targets: Optional[list] = None,
    timeout: int = 180,
):
    """调用 POST /api/companies/smart-send。"""
    payload: dict = {
        "company": company,
        "company_id": company_id,
        "job_url": job_url,
        "top_hr": top_hr or {},
        "hr_name": hr_name,
        "greeting": greeting,
        "confirm": confirm,
    }
    if targets is not None:
        payload["targets"] = targets
    return _post("/api/companies/smart-send", json=payload, timeout=timeout)
