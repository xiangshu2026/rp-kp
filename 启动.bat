@echo off
chcp 65001 >nul
title 跑团 KP
cd /d "%~dp0"

echo 正在启动跑团 KP...
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没找到 python，请先安装 Python 3.10+
  pause
  exit /b 1
)

REM ── 先拉起 WorkBuddy 国内版反代（若已在监听则跳过）──
netstat -ano | findstr /R /C:"127.0.0.1:8795 .*LISTENING" >nul
if errorlevel 1 (
  echo 正在启动 WorkBuddy 国内版反代 127.0.0.1:8795 ...
  start "wb-proxy" /min python "%~dp0wb-proxy.py" --port 8795
  timeout /t 3 /nobreak >nul
) else (
  echo WorkBuddy 反代已在运行。
)

start "" http://127.0.0.1:8760
python server.py

pause
