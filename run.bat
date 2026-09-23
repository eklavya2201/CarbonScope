@echo off
cd /d "%~dp0"
if not exist .venv (
  echo First run: setting up Python packages. This takes a minute or two...
  python -m venv .venv
  .venv\Scripts\python -m pip install -r requirements.txt
)
echo.
echo  CarbonScope is running at http://127.0.0.1:5000
echo  Close this window to stop it.
echo.
start "" http://127.0.0.1:5000
.venv\Scripts\python run.py
