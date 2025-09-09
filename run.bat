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

REM Activate the virtual environment
ECHO Activating virtual environment...
CALL .\%VENV_DIR%\Scripts\activate.bat

REM Change to the backend directory
ECHO Changing to backend directory...
cd backend

REM Run the Uvicorn server
ECHO Starting FastAPI server with Uvicorn...
ECHO Access the dashboard at http://localhost:8000
uvicorn app.main:app --host 0.0.0.0 --port 8000

REM Deactivate on exit (e.g., Ctrl+C)
ECHO Server stopped.
CALL ..\%VENV_DIR%\Scripts\deactivate.bat

:EOF
PAUSE
