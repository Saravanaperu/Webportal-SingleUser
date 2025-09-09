@ECHO OFF
REM This script sets up the environment for the Automated Trading Portal on Windows.

ECHO --- Automated Trading Portal Setup (Windows) ---
ECHO.

REM --- 1. Check for Prerequisites ---
ECHO Step 1: Checking for Python...
python --version >NUL 2>NUL
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: python could not be found. Please install Python and add it to your PATH.
    GOTO:EOF
)
ECHO Prerequisites found.
ECHO.

REM --- 2. Create Virtual Environment ---
SET VENV_DIR=venv
ECHO Step 2: Creating Python virtual environment in '.\%VENV_DIR%'...
IF EXIST "%VENV_DIR%" (
    ECHO Virtual environment '.\%VENV_DIR%' already exists. Skipping creation.
) ELSE (
    python -m venv %VENV_DIR%
    IF %ERRORLEVEL% NEQ 0 (
        ECHO ERROR: Failed to create virtual environment.
        GOTO:EOF
    )
)
ECHO Virtual environment created.
ECHO.

REM --- 3. Install Dependencies ---
ECHO Step 3: Installing required Python packages into the virtual environment...
.\%VENV_DIR%\Scripts\pip.exe install -r backend/requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: Failed to install dependencies from backend/requirements.txt.
    GOTO:EOF
)
ECHO Dependencies installed successfully.
ECHO.

REM --- 4. Check for Environment File ---
SET ENV_FILE=.env
ECHO Step 4: Checking for environment file...
IF EXIST "%ENV_FILE%" (
    ECHO Environment file '.env' found.
) ELSE (
    ECHO WARNING: Environment file '.env' not found.
    ECHO Please copy '.env.example' to '.env' and fill in your Angel One API credentials.
    ECHO copy .env.example .env
)
ECHO.

REM --- 5. Create Data and Logs Directories ---
ECHO Step 5: Creating 'data' and 'logs' directories...
IF NOT EXIST "data" mkdir data
IF NOT EXIST "logs" mkdir logs
ECHO Directories created.
ECHO.

ECHO --- Setup Complete! ---
ECHO To run the application, use the provided 'run.bat' script.
ECHO run.bat

:EOF
PAUSE
