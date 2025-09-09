@ECHO OFF
REM This script runs the Automated Trading Portal application on Windows.
REM It assumes you have already run setup.bat to create the environment.

SET VENV_DIR=venv

REM Check if the virtual environment exists
IF NOT EXIST "%VENV_DIR%" (
    ECHO ERROR: Virtual environment not found at '.\%VENV_DIR%'.
    ECHO Please run the setup.bat script first.
    PAUSE
    GOTO:EOF
)

REM Run the Uvicorn server from the root directory using the venv's python
ECHO Starting FastAPI server with Uvicorn...
ECHO Access the dashboard at http://localhost:8000
.\%VENV_DIR%\Scripts\uvicorn.exe backend.app.main:app --host 0.0.0.0 --port 8000 --app-dir .

REM The server will run until you stop it with Ctrl+C
ECHO Server stopped.

:EOF
PAUSE
