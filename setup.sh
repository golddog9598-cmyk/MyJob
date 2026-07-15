#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "================================"
echo " MyJob V0.0.10 安装"
echo "================================"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] 未找到 python3，请先安装 Python 3.10 或更高版本"
    exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
    echo "[ERROR] 未找到 npm，请先安装 Node.js 20 或更高版本"
    exit 1
fi

echo "[1/3] 安装 Python 依赖"
python3 -m pip install -r requirements.txt

echo "[2/3] 构建 Vue 前端"
npm --prefix resume_ui install
npm --prefix resume_ui run build

echo "[3/3] 准备用户侧招聘平台扩展"
echo "请在 Chrome 或 Edge 的扩展管理页启用开发者模式，加载 browser_extension 目录。"
echo "招聘平台登录、搜索、沟通和投递只在该扩展与浏览器 IndexedDB 中运行。"

echo ""
echo "安装完成。启动 HTTPS 服务："
echo "  python3 myjob_server.py --host 127.0.0.1 --port 8010"
echo "访问地址："
echo "  https://127.0.0.1:8010/"
