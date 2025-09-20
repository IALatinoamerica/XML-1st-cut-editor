@echo off
PUSHD "%~dp0"

SET "EXIT_CODE=0"
SET "APP_PUSHED="

IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo Virtual environment not found. Please run setup_env.bat first.
    SET "EXIT_CODE=1"
    GOTO error
)

call .venv\Scripts\activate
IF ERRORLEVEL 1 (
    SET "EXIT_CODE=%ERRORLEVEL%"
    GOTO error
)

IF EXIST app (
    PUSHD app
    SET "APP_PUSHED=1"
)

python main.py
SET "EXIT_CODE=%ERRORLEVEL%"
IF NOT "%EXIT_CODE%"=="0" GOTO error

IF DEFINED APP_PUSHED POPD
POPD
EXIT /B 0

:error
echo.
echo Failed to launch the application.
IF DEFINED APP_PUSHED POPD
POPD
PAUSE
EXIT /B %EXIT_CODE%
