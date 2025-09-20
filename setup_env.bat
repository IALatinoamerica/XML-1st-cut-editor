@echo off
SETLOCAL
IF NOT EXIST .venv (
    python -m venv .venv
)
CALL .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
ENDLOCAL
