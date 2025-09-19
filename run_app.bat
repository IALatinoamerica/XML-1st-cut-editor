@echo off
REM Activate the virtual environment and run the XML first cut editor.

if not exist .venv (
    echo Virtual environment not found. Run setup_env.bat first.
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m xml_first_cut.cli %*
