@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py readmerocket_web.py %* & exit /b)
where python >nul 2>nul && (python readmerocket_web.py %* & exit /b)
echo Python not found. Install Python 3 from python.org and tick "Add to PATH".
pause
