@echo off
chcp 65001 >nul
setlocal

set "PROJECT_DIR=%~dp0"
if not defined BOSS_PORT set "BOSS_PORT=8010"
if not defined BOSS_HOST set "BOSS_HOST=127.0.0.1"

where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=py -3"
) else (
  set "PYTHON_CMD=python"
)

cd /d "%PROJECT_DIR%" || (echo [ERROR] 无法进入项目目录 & pause & exit /b 1)

echo ============================================
echo  MyJob V0.0.4
echo ============================================
echo.

echo [1/3] 检查 Python 依赖...
%PYTHON_CMD% -c "import fastapi, uvicorn, yaml, bs4, lxml, websockets, playwright, cryptography" 2>nul
if errorlevel 1 (
  echo [WARN] 正在安装缺少的依赖...
  %PYTHON_CMD% -m pip install -r "%PROJECT_DIR%requirements.txt"
  if errorlevel 1 (echo [ERROR] Python 依赖安装失败 & pause & exit /b 1)
)

echo [2/3] 检查 Vue 前端...
if not exist "%PROJECT_DIR%static\app\index.html" (
  if not exist "%PROJECT_DIR%resume_ui\node_modules" (
    echo [ERROR] 前端尚未构建，请先在 resume_ui 目录运行 npm install 和 npm run build
    pause
    exit /b 1
  )
  pushd "%PROJECT_DIR%resume_ui"
  call npm.cmd run build
  if errorlevel 1 (popd & echo [ERROR] Vue 前端构建失败 & pause & exit /b 1)
  popd
)

echo [3/3] 启动 HTTPS 服务 https://%BOSS_HOST%:%BOSS_PORT%/
start "" "https://%BOSS_HOST%:%BOSS_PORT%/"
%PYTHON_CMD% "%PROJECT_DIR%boss_app.py" --host "%BOSS_HOST%" --port "%BOSS_PORT%"

pause
