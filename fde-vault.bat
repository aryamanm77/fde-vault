@echo off
setlocal
set "G=%~dp0.claude\skills\fde-vault\scripts\vault_guard.py"
if not exist "%G%" set "G=%USERPROFILE%\.claude\skills\fde-vault\scripts\vault_guard.py"
if not exist "%G%" (
  echo fde-vault: vault_guard.py not found 1>&2
  exit /b 1
)
set "ARGS=%*"
if "%~1"=="" set "ARGS=open"
where py >nul 2>nul
if %errorlevel%==0 goto usepy
python "%G%" %ARGS%
exit /b %errorlevel%
:usepy
py -3 "%G%" %ARGS%
exit /b %errorlevel%
