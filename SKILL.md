# MyJob Development Rules

## Mandatory platform boundary

All recruitment-platform operations and data are client-side only.

- Platform login, heartbeat, logout, window control, search, apply and messaging run in `browser_extension/`.
- Jobs, applications, conversations, exchanges, campaigns, platform settings and platform statistics use `resume_ui/src/platformStore.js` and browser IndexedDB.
- FastAPI must never receive or store recruitment-platform cookies, URLs, jobs, companies, applications, recruiters, messages, campaigns or platform statistics.
- Do not add `/api/system`, `/api/jobs`, `/api/applications`, `/api/conversations`, `/api/campaigns`, `/api/monitor`, `/api/companies`, `/api/settings` or `/api/dashboard` routes.
- Do not add Playwright, Selenium or recruitment-platform SDKs to Python dependencies.
- New platform features must extend the Manifest V3 bridge and IndexedDB model.

## Allowed backend scope

- MyJob account registration, login, password and sessions.
- Administrator accounts, registration controls and online-duration analytics.
- Main resume, resume templates, import and DOCX/PDF export.
- HTTPS and built Vue static files.

## Compliance

- Never bypass CAPTCHA, sliders, security verification or rate limits.
- Stop automation when a platform safety prompt is detected.
- Automatic applications require explicit user confirmation and a client-side daily limit.
- Do not log or upload platform page content.

## Verification

```powershell
cd resume_ui
npm run build
cd ..
python -m pytest tests -q
python -m py_compile myjob_server.py resume_store.py boss_app.py MyJob_cli\client.py MyJob_cli\cli.py
python -m json.tool MyJob_cli\schema.json
git diff --check
```

The architecture boundary test in `tests/test_client_platform_boundary.py` must remain green.
