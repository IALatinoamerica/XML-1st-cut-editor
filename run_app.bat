@echo off
PUSHD "%~dp0"

SET "EXIT_CODE=0"
SET "TARGET_SCRIPT="

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

IF EXIST app\main.py (
    SET "TARGET_SCRIPT=app\main.py"
) ELSE (
    IF EXIST main.py (
        SET "TARGET_SCRIPT=main.py"
    ) ELSE (
        echo Could not find the application entry point (main.py).
        SET "EXIT_CODE=1"
        GOTO error
    )
)

python "%TARGET_SCRIPT%"
SET "EXIT_CODE=%ERRORLEVEL%"
IF NOT "%EXIT_CODE%"=="0" GOTO error

POPD
EXIT /B 0

:error
echo.
echo Failed to launch the application.
POPD
PAUSE
EXIT /B %EXIT_CODE%
