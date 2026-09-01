@echo off
set /p CONFIRM=[WARN] This will reset your local branch to match remote. Continue? [y/N]: 
if /i not "%CONFIRM%"=="y" (
    echo [ABORTED] No changes made.
    pause
    exit /b 0
)

echo [INFO] Fetching remote...
git fetch origin

echo [INFO] Resetting local branch to match remote...
for /f "tokens=*" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
git reset --hard origin/%BRANCH%

echo [INFO] Cleaning untracked files and directories...
git clean -fd

echo [DONE] Local repo is now in sync with origin/%BRANCH%
pause
