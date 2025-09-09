@ECHO OFF
REM This script runs the test suite for the Automated Trading Portal on Windows.
REM It assumes you have already run setup.bat to create the environment.

SET VENV_DIR=venv

REM Check if the virtual environment exists
IF NOT EXIST "%VENV_DIR%" (
    ECHO ERROR: Virtual environment not found at '.\%VENV_DIR%'.
    ECHO Please run the setup.bat script first.
    PAUSE
    GOTO:EOF
)

# Run pytest using the venv's python
ECHO Running pytest...
.\%VENV_DIR%\Scripts\pytest

ECHO Tests finished.

:EOF
PAUSE
