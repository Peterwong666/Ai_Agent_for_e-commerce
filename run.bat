@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   跨境电商选品 AI Agent
echo ========================================

where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 未安装 uv，请先安装:
    echo    PowerShell: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo    或访问: https://docs.astral.sh/uv/
    pause
    exit /b 1
)

echo 📦 检查依赖...
uv sync

if not exist ".env" (
    echo ℹ️  未检测到 .env 文件（将使用本地模板报告）
    echo    如需 AI 增强报告，请复制 .env.example 为 .env 并填入 DeepSeek API Key
)

echo 🚀 启动中...
uv run streamlit run app.py
pause
