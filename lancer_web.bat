@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m streamlit run web/app.py
) else if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" -m streamlit run web/app.py
) else (
  echo Creez un environnement Python et installez requirements-web.txt.
  echo Consultez docs/INTERFACE_WEB.md.
  pause
)
