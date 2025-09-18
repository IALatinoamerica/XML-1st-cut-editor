@echo off
REM Create a virtual environment called "venv"
python -m venv venv

REM Activate the virtual environment (Windows)
call venv\Scripts\activate

REM Install dependencies
pip install -r requirements.txt

echo.
echo Virtual environment created and dependencies installed.
echo To run the script, use "run_script.bat"
pause
