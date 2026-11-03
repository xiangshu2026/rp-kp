@echo off
chcp 65001 >nul
title 环境自检
echo ===== 跑团 KP 环境自检 =====
echo.
echo [1/3] Python
python --version 2>&1
echo.
echo [2/3] Ollama 服务
curl -s -m 3 http://127.0.0.1:11434/api/tags >nul 2>nul
if errorlevel 1 (
  echo   [X] Ollama 没在运行，请先打开 Ollama
) else (
  echo   [OK] Ollama 在线
)
echo.
echo [3/3] KP 模型
ollama list 2>nul | findstr /C:"kp-qwen3" >nul
if errorlevel 1 (
  echo   [X] 没有 kp-qwen3，执行：ollama create kp-qwen3 -f Modelfile
) else (
  echo   [OK] kp-qwen3 已安装
)
echo.
pause