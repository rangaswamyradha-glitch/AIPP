@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
python -m streamlit run app.py --server.port 8502 --browser.gatherUsageStats false
pause