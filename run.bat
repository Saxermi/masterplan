@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 server.py
) else (
  where python >nul 2>nul
  if %ERRORLEVEL%==0 (python server.py) else (echo Python 3.10+ required. Please install Python from python.org & pause)
)
