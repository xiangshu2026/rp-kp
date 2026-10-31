@echo off
chcp 65001 >nul
echo === 跑团 KP 环境自检 ===
echo.
echo [1/3] 检查 Python...
python --version 2>nul || (echo   ✗ 未安装 Python & goto :fail)
echo   ✓ Python 正常
echo.
echo [2/3] 检查 Ollama...
ollama --version 2>nul || (echo   ✗ 未安装 Ollama 或未启动 & goto :fail)
echo   ✓ Ollama 正常
echo.
echo [3/3] 检查 kp-qwen3 模型...
ollama list 2>nul | findstr /i "kp-qwen3" >nul || (echo   ✗ 缺少 kp-qwen3 模型，请先执行：ollama create kp-qwen3 -f Modelfile & goto :fail)
echo   ✓ kp-qwen3 已就绪
echo.
echo === 自检通过，可以双击 启动.bat ===
pause
exit /b 0

:fail
echo.
echo === 自检未通过，请按上面提示处理后重试 ===
pause
exit /b 1
