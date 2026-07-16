#!/usr/bin/env python3
"""MyJob account, administration, resume and static-file backend.

Recruitment-platform cookies, operations and data are intentionally excluded.
Those capabilities run in the user's browser through the MyJob extension and
IndexedDB client cache.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app_auth import AUTH_COOKIE_NAME, AuthManager, LoginRateLimiter
from myjob_tls import ensure_local_certificate
from resume_documents import (
    SUPPORTED_EXTENSIONS,
    build_resume_bytes,
    extract_resume_text,
    get_template,
    list_templates,
    normalize_resume_structure,
    parse_resume_structure,
    structured_to_markdown,
    template_preview_html,
)
from resume_store import ResumeStore


VERSION = "V0.0.12"
ROOT = Path(__file__).parent
PROFILE_DIR = ROOT / ".boss_profile"
STATIC_DIR = ROOT / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="MyJob",
    version=VERSION,
    docs_url="/api/docs" if os.getenv("MYJOB_ENABLE_DOCS", "false").lower() == "true" else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if os.getenv("MYJOB_ENABLE_DOCS", "false").lower() == "true" else None,
)

allowed_origins = [
    value.strip()
    for value in (
        os.getenv("MYJOB_CORS_ORIGINS")
        or "https://127.0.0.1:5173,https://localhost:5173"
    ).split(",")
    if value.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=False), name="static")

auth_manager = AuthManager(
    Path(os.getenv("MYJOB_AUTH_FILE") or PROFILE_DIR / "auth.db"),
    session_hours=int(os.getenv("MYJOB_SESSION_HOURS", "12")),
    legacy_path=PROFILE_DIR / "auth.json",
)
resume_store = ResumeStore(Path(os.getenv("MYJOB_RESUME_FILE") or PROFILE_DIR / "resumes.db"))
login_limiter = LoginRateLimiter()

PUBLIC_API_PATHS = {
    "/api/auth/status",
    "/api/auth/register",
    "/api/auth/login",
    "/api/admin/login",
    "/api/auth/logout",
    "/api/health",
}


@app.middleware("http")
async def authenticated_api(request: Request, call_next):
    path = request.url.path.rstrip("/") or "/"
    if request.method != "OPTIONS" and path.startswith("/api/") and path not in PUBLIC_API_PATHS:
        session = auth_manager.verify_token(request.cookies.get(AUTH_COOKIE_NAME, ""))
        if not session:
            return JSONResponse(
                status_code=401,
                content={"detail": "登录已失效，请重新登录", "code": "AUTH_REQUIRED"},
            )
        request.state.user = session
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


class AuthCredentials(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class AdminCreateRequest(BaseModel):
    username: str
    password: str


class RegistrationToggleRequest(BaseModel):
    enabled: bool


class UserStatusRequest(BaseModel):
    active: bool


class MasterResumeUpdate(BaseModel):
    content: str
    name: str = "主简历"
    source_format: str = "markdown"


class StructuredResumeUpdate(BaseModel):
    name: str = "主简历"
    template_id: str = "ats_classic"
    structured: dict


class ResumeCreateRequest(BaseModel):
    template_id: str = "ats_classic"
    name: str = "主简历"
    content: str = ""


class ResumeTemplateUpdate(BaseModel):
    template_id: str


def session_response(request: Request, payload: dict, token: str, status_code: int = 200) -> JSONResponse:
    response = JSONResponse(status_code=status_code, content=payload)
    secure_env = os.getenv("MYJOB_SECURE_COOKIE", "").strip().lower()
    secure_cookie = secure_env == "true" if secure_env else request.url.scheme == "https"
    response.set_cookie(
        AUTH_COOKIE_NAME,
        token,
        max_age=auth_manager.session_seconds,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def public_user(user: Optional[dict]) -> Optional[dict]:
    if not user:
        return None
    user_id = user.get("user_id", user.get("id"))
    return {
        "id": user_id,
        "user_id": user_id,
        "username": user.get("username", user.get("sub")),
        "role": user.get("role", "user"),
        "is_active": bool(user.get("is_active", True)),
        "must_change_password": bool(user.get("must_change_password", False)),
    }


def client_key(request: Request, username: str, portal: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{portal}:{host}:{str(username or '').strip().casefold()}"


def login(credentials: AuthCredentials, request: Request, admin_portal: bool = False):
    key = client_key(request, credentials.username, "admin" if admin_portal else "user")
    retry_after = login_limiter.retry_after(key)
    if retry_after:
        response = JSONResponse(status_code=429, content={"detail": f"登录尝试过多，请在 {retry_after} 秒后重试"})
        response.headers["Retry-After"] = str(retry_after)
        return response
    user = auth_manager.authenticate(credentials.username, credentials.password)
    allowed_roles = {"admin", "superadmin"} if admin_portal else {"user"}
    if not user or user["role"] not in allowed_roles:
        login_limiter.failure(key)
        raise HTTPException(status_code=401, detail="用户名或密码不正确")
    login_limiter.success(key)
    token = auth_manager.issue_token(
        user,
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    return session_response(request, {"authenticated": True, "user": user}, token)


def require_admin(request: Request, superadmin: bool = False) -> dict:
    user = request.state.user
    allowed = {"superadmin"} if superadmin else {"admin", "superadmin"}
    if user.get("role") not in allowed:
        raise HTTPException(status_code=403, detail="无权访问管理员后台")
    if user.get("must_change_password"):
        raise HTTPException(status_code=403, detail="请先修改默认密码")
    return user


def current_user_id(request: Request) -> int:
    return int(request.state.user["user_id"])


@app.get("/api/health")
def health():
    return {"status": "ok", "version": VERSION, "platform_backend": False}


@app.get("/api/auth/status")
def auth_status(request: Request):
    session = auth_manager.verify_token(request.cookies.get(AUTH_COOKIE_NAME, ""))
    return {
        "configured": True,
        "registration_enabled": auth_manager.registration_enabled,
        "authenticated": bool(session),
        "user": public_user(session),
    }


@app.post("/api/auth/register")
def auth_register(credentials: AuthCredentials, request: Request):
    try:
        user = auth_manager.register(credentials.username, credentials.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    token = auth_manager.issue_token(
        user,
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    return session_response(request, {"authenticated": True, "user": user}, token, status_code=201)


@app.post("/api/auth/login")
def auth_login(credentials: AuthCredentials, request: Request):
    return login(credentials, request)


@app.post("/api/admin/login")
def admin_login(credentials: AuthCredentials, request: Request):
    return login(credentials, request, admin_portal=True)


@app.get("/api/auth/session")
def auth_session(request: Request):
    return {"authenticated": True, "user": public_user(request.state.user)}


@app.post("/api/auth/heartbeat")
def auth_heartbeat(request: Request):
    try:
        return auth_manager.heartbeat(request.state.user["sid"])
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/api/auth/change-password")
def auth_change_password(payload: PasswordChangeRequest, request: Request):
    try:
        user = auth_manager.change_password(
            request.state.user["user_id"], payload.current_password, payload.new_password
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    token = auth_manager.issue_token(
        user,
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    return session_response(request, {"status": "ok", "user": user}, token)


@app.post("/api/auth/logout")
def auth_logout(request: Request):
    session = auth_manager.verify_token(request.cookies.get(AUTH_COOKIE_NAME, ""))
    if session:
        auth_manager.end_session(session["sid"])
    response = JSONResponse(content={"authenticated": False})
    response.delete_cookie(AUTH_COOKIE_NAME, path="/", samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/admin/overview")
def admin_overview(request: Request, days: int = 7):
    require_admin(request)
    return auth_manager.admin_overview(days)


@app.get("/api/admin/users")
def admin_users(request: Request, limit: int = 100):
    require_admin(request)
    return {"users": auth_manager.list_users(limit)}


@app.post("/api/admin/accounts")
def admin_create_account(payload: AdminCreateRequest, request: Request):
    require_admin(request, superadmin=True)
    try:
        user = auth_manager.create_admin(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "ok", "user": user}


@app.put("/api/admin/registration")
def admin_registration(payload: RegistrationToggleRequest, request: Request):
    require_admin(request)
    auth_manager.set_registration_enabled(payload.enabled)
    return {"registration_enabled": auth_manager.registration_enabled}


@app.put("/api/admin/users/{user_id}/status")
def admin_user_status(user_id: int, payload: UserStatusRequest, request: Request):
    actor = require_admin(request)
    target = auth_manager.get_user(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target["role"] in {"admin", "superadmin"} and actor["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="只有超级管理员可以管理管理员账号")
    try:
        user = auth_manager.set_user_active(actor["user_id"], user_id, payload.active)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "ok", "user": user}


@app.get("/api/resume-templates")
def read_resume_templates():
    templates = list_templates()
    return {
        "templates": templates,
        "total": len(templates),
        "categories": list(dict.fromkeys(item["category"] for item in templates)),
    }


@app.get("/api/resume-templates/{template_id}/preview", response_class=HTMLResponse)
def preview_resume_template(template_id: str, request: Request, sample: bool = False):
    try:
        structured = None
        if not sample:
            resume = resume_store.get(current_user_id(request))
            if resume:
                structured = resume.get("structured") or parse_resume_structure(resume.get("content") or "")
        return HTMLResponse(template_preview_html(template_id, structured))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/resumes/master")
def read_master_resume(request: Request):
    return {"resume": resume_store.get(current_user_id(request))}


@app.put("/api/resumes/master")
def update_master_resume(payload: MasterResumeUpdate, request: Request):
    user_id = current_user_id(request)
    current = resume_store.get(user_id) or {}
    structured = parse_resume_structure(payload.content)
    return {
        "resume": resume_store.save(
            user_id,
            content=payload.content,
            name=payload.name,
            source_format=payload.source_format,
            structured=structured,
            template_id=current.get("template_id") or "ats_classic",
        )
    }


@app.put("/api/resumes/master/structured")
def update_structured_master_resume(payload: StructuredResumeUpdate, request: Request):
    try:
        get_template(payload.template_id)
        structured = normalize_resume_structure(payload.structured)
        content = structured_to_markdown(structured)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user_id = current_user_id(request)
    current = resume_store.get(user_id) or {}
    return {
        "resume": resume_store.save(
            user_id,
            content=content,
            name=payload.name.strip() or current.get("name") or "主简历",
            source_format="structured-v2",
            source_filename=current.get("source_filename") or "",
            source_mime=current.get("source_mime") or "",
            structured=structured,
            template_id=payload.template_id,
        )
    }


@app.post("/api/resumes/upload")
async def upload_master_resume(
    request: Request,
    file: UploadFile = File(...),
    template_id: str = Form("ats_classic"),
):
    try:
        get_template(template_id)
        content = await file.read()
        text, source_format = await asyncio.to_thread(
            extract_resume_text, file.filename or "resume.txt", content
        )
        structured = parse_resume_structure(text)
        markdown = structured_to_markdown(structured)
        resume = resume_store.save(
            current_user_id(request),
            content=markdown,
            name=Path(file.filename or "主简历").stem or "主简历",
            source_format=source_format,
            source_filename=file.filename or "",
            source_mime=file.content_type or "",
            structured=structured,
            template_id=template_id,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"简历解析失败: {exc}") from exc
    return {
        "resume": resume,
        "parse": {
            "status": "ready",
            "source_format": source_format,
            "characters": len(text),
            "sections": len(structured.get("sections") or []),
            "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        },
    }


@app.post("/api/resumes/create-from-template")
def create_resume_from_template(payload: ResumeCreateRequest, request: Request):
    try:
        get_template(payload.template_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    content = payload.content.strip() or f"""# {payload.name or '姓名'}
目标岗位 | 手机 | 邮箱 | 城市

## 个人简介
- 请填写与目标岗位相关的真实优势。

## 专业技能
- 请填写技能。

## 工作经历
- 公司 | 职位 | 时间
- 请填写职责与可核实成果。

## 项目经历
- 项目名称 | 角色 | 时间
- 请填写动作、产物和结果。

## 教育经历
- 学校 | 专业 | 学历 | 时间"""
    structured = parse_resume_structure(content)
    resume = resume_store.save(
        current_user_id(request),
        content=structured_to_markdown(structured),
        name=payload.name or "主简历",
        source_format="markdown",
        structured=structured,
        template_id=payload.template_id,
    )
    return {"resume": resume}


@app.put("/api/resumes/master/template")
def update_master_resume_template(payload: ResumeTemplateUpdate, request: Request):
    try:
        get_template(payload.template_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    resume = resume_store.set_template(current_user_id(request), payload.template_id)
    if not resume:
        raise HTTPException(status_code=404, detail="请先上传或创建主简历")
    return {"resume": resume}


@app.get("/api/resumes/master/export")
def export_master_resume(request: Request, format: str = "docx", template_id: str = ""):
    resume = resume_store.get(current_user_id(request))
    if not resume:
        raise HTTPException(status_code=404, detail="请先上传或创建主简历")
    chosen = template_id or resume.get("template_id") or "ats_classic"
    try:
        get_template(chosen)
        structured = resume.get("structured") or parse_resume_structure(resume["content"])
        content, media_type, suffix = build_resume_bytes(structured, chosen, format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="master-resume-{chosen}.{suffix}"'},
    )


@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
def legacy_admin_redirect():
    return RedirectResponse(url="/MyJobaAdmin", status_code=307)


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
@app.get("/login/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
@app.get("/register/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
@app.get("/app/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
@app.get("/docs/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/changelog", response_class=HTMLResponse, include_in_schema=False)
@app.get("/changelog/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/MyJobaAdmin", response_class=HTMLResponse, include_in_schema=False)
@app.get("/MyJobaAdmin/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/", response_class=HTMLResponse)
def index():
    html_path = STATIC_DIR / "app" / "index.html"
    if not html_path.exists():
        return HTMLResponse(content="<h1>MyJob</h1><p>请先构建 Vue 前端</p>")
    response = HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def main():
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--ssl-certfile", "--cert", dest="ssl_certfile", default=os.getenv("MYJOB_TLS_CERT"))
    parser.add_argument("--ssl-keyfile", "--key", dest="ssl_keyfile", default=os.getenv("MYJOB_TLS_KEY"))
    parser.add_argument("--http", action="store_true", help="仅限本地调试：禁用 HTTPS")
    args = parser.parse_args()

    options = {}
    scheme = "http"
    if not args.http:
        cert_file, key_file = ensure_local_certificate(args.ssl_certfile, args.ssl_keyfile)
        options.update(ssl_certfile=str(cert_file), ssl_keyfile=str(key_file))
        scheme = "https"
    print(f"MyJob {VERSION}: {scheme}://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, **options)


if __name__ == "__main__":
    main()
