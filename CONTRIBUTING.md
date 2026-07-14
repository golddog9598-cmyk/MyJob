# Contributing

## Development Setup

```bash
git clone https://github.com/golddog9598-cmyk/MyJob.git
cd MyJob
git checkout MyJob
pip install -e ".[dev]"
playwright install firefox
```

## Code Style

- Python: follow PEP 8, max line length 120
- Frontend: Vue 3 single-file components with shared theme tokens
- Use `ruff` for linting: `ruff check .`
- No comments unless necessary

## Pull Request Flow

1. Clone the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make changes and test locally
4. Push and open a pull request against `main`

## Project Conventions

- All Python code is flat (no src-layout for the main modules)
- CLI module lives in `MyJob_cli/`
- Database migrations are manual ALTER TABLE in `init_db()`
- Frontend source lives in `resume_ui/`; production assets are built into `static/app/`
- API returns JSON, CLI outputs JSON envelope

## Testing

```bash
# Manual testing: start server and use web console
python boss_app.py --port 8010

# CLI testing
myjob status
myjob search "AI Agent" --city 北京
```
