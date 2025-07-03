@echo off
REM Batch file to run the video sync cronjob
REM This file can be used with Windows Task Scheduler

cd /d "%~dp0"

REM Run the PowerShell script
powershell.exe -ExecutionPolicy Bypass -File "run_video_sync.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo Video sync cronjob failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo Video sync cronjob completed successfully
