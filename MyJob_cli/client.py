"""HTTPS client for MyJob account and resume APIs.

Recruitment-platform operations are intentionally unavailable in the CLI.
They run in the authenticated Vue workspace and browser extension so platform
data never passes through the backend.
"""

import os
from pathlib import Path
from urllib.parse import urlencode, urlparse

import httpx


BASE_URL = os.environ.get("MYJOB_API", "https://127.0.0.1:8010")
verify_env = os.environ.get("MYJOB_TLS_VERIFY", "").strip().lower()
local_https = urlparse(BASE_URL).hostname in {"127.0.0.1", "localhost", "::1"}
verify_tls = verify_env not in {"false", "0", "no"} if verify_env else not local_https
client = httpx.Client(base_url=BASE_URL, verify=verify_tls)


def request(method: str, path: str, *, json=None, data=None, files=None, timeout=120):
    try:
        return client.request(method, path, json=json, data=data, files=files, timeout=timeout)
    except httpx.ConnectError:
        return httpx.Response(503, text="Cannot connect to MyJob server. Run start.bat first.")


def health():
    return request("GET", "/api/health", timeout=15)


def auth_status():
    return request("GET", "/api/auth/status", timeout=15)


def get_master_resume():
    return request("GET", "/api/resumes/master")


def get_resume_templates():
    return request("GET", "/api/resume-templates")


def upload_master_resume(file_path: str, template_id: str = "ats_classic"):
    path = Path(file_path)
    try:
        with path.open("rb") as handle:
            return request(
                "POST",
                "/api/resumes/upload",
                files={"file": (path.name, handle)},
                data={"template_id": template_id},
                timeout=180,
            )
    except OSError as exc:
        return httpx.Response(400, text=str(exc))


def set_master_resume_template(template_id: str):
    return request("PUT", "/api/resumes/master/template", json={"template_id": template_id})


def export_master_resume(output_format: str = "docx", template_id: str = ""):
    query = urlencode({"format": output_format, "template_id": template_id})
    return request("GET", f"/api/resumes/master/export?{query}", timeout=180)
