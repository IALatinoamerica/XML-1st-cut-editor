@echo off
PUSHD "%~dp0"

REM Create a virtual environment called ".venv"
python -m venv .venv
IF ERRORLEVEL 1 GOTO error

REM Activate the virtual environment (Windows)
call .venv\Scripts\activate
IF ERRORLEVEL 1 GOTO error

REM Install dependencies
pip install -r requirements.txt
IF ERRORLEVEL 1 GOTO error

echo.
echo Virtual environment created and dependencies installed.
echo To run the script, use "run_app.bat"
POPD
GOTO end

:error
echo.
echo Failed to set up the environment. Please review the messages above.
POPD
PAUSE
EXIT /B 1

:end
EXIT /B 0
