@echo off
setlocal

cd /d D:\notion-cli

echo ============================================================
echo Notion CLI - Sync to GitHub
echo ============================================================
echo.

echo [1/5] 当前 Git 状态
git status

echo.
echo ============================================================
echo [2/5] 添加修改
echo ============================================================
git add .

if errorlevel 1 (
    echo.
    echo [ERROR] git add 失败
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [3/5] 创建 Commit
echo ============================================================

for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set DATE=%%a-%%b-%%c
for /f "tokens=1-2 delims=: " %%a in ("%time%") do set TIME=%%a%%b

git diff --cached --quiet

if %errorlevel%==0 (
    echo 没有新的修改需要提交。
) else (
    git commit -m "sync: local code %DATE% %TIME%"

    if errorlevel 1 (
        echo.
        echo [ERROR] git commit 失败
        pause
        exit /b 1
    )
)

echo.
echo ============================================================
echo [4/5] 推送到 GitHub
echo ============================================================

git push origin master

if errorlevel 1 (
    echo.
    echo [ERROR] git push 失败
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [5/5] 同步完成
echo ============================================================
echo.

git status

echo.
echo GitHub 已同步。
echo 可以继续让小柴读取最新代码。
echo.

pause