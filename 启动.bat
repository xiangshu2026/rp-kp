@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动跑团 KP（浏览器会自动打开）...
python server.py
if errorlevel 1 (
  echo.
  echo 启动失败。请确认：Python 已安装、Ollama 正在运行、kp-qwen3 模型已拉取。
  pause
)
