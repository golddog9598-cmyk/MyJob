# Contributing

## Development setup

```powershell
git clone https://github.com/golddog9598-cmyk/MyJob.git
cd MyJob
git checkout MyJob
python -m pip install -e ".[dev]"
cd resume_ui
npm install
```

Load `browser_extension/` as an unpacked extension in Chrome or Edge for platform testing.

## Versioning

MyJob uses three numeric segments: `major.minor.patch`. Each segment must be between 0 and 99, so the highest valid version is `99.99.99`. Every release updates the backend, Vue app, browser extension, CLI, documentation, tests and generated frontend assets together.

## Architecture rule

Recruitment-platform operations and data must stay in the Vue application, Chromium extension and browser IndexedDB. The FastAPI backend is limited to MyJob accounts, administrators, main resumes, templates and static files.

Pull requests that add server-side recruitment-platform routes, storage or browser automation will not be accepted.

## Code style

- Python follows PEP 8 with a 120 character line limit.
- Frontend uses Vue 3 single-file components and shared theme tokens.
- Extension code uses Manifest V3 and no remote executable code.
- Comments should explain boundaries, compliance or non-obvious behavior.

## Testing

```powershell
cd resume_ui
npm run build
cd ..
python -m pytest tests -q
python -m py_compile myjob_server.py resume_store.py boss_app.py MyJob_cli\client.py MyJob_cli\cli.py
python -m json.tool MyJob_cli\schema.json
git diff --check
```

Manual testing starts with:

```powershell
python myjob_server.py --port 8010
```
