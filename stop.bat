@echo off
echo 正在停止 NotionCLI...

taskkill /F /IM pythonw.exe >nul 2>&1

if errorlevel 1 (
    echo 未找到正在运行的 NotionCLI。
) else (
    echo NotionCLI 已停止。
)

pause
