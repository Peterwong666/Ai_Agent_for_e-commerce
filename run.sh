#!/bin/bash
# 跨境电商选品 AI Agent — 一键启动 (macOS / Linux)
set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  跨境电商选品 AI Agent"
echo "========================================"

if ! command -v uv &> /dev/null; then
    echo "❌ 未安装 uv，请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "📦 检查依赖..."
uv sync

if [ ! -f ".env" ]; then
    echo "ℹ️  未检测到 .env，将使用本地模板报告"
    echo "   如需 AI 增强: cp .env.example .env 并填入 API Key"
fi

echo "🚀 启动中..."
uv run streamlit run app.py
