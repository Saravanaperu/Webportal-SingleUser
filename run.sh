#!/bin/bash
#
# This script runs the Automated Trading Portal application.
# It assumes you have already run setup.sh to create the environment.

VENV_DIR="venv"

# Check if the virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: Virtual environment not found at './${VENV_DIR}'."
    echo "Please run the setup.sh script first."
    exit 1
fi

# Run the Uvicorn server from the root directory using the venv's python
echo "Starting FastAPI server with Uvicorn..."
echo "Access the dashboard at http://localhost:8000"
$VENV_DIR/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --app-dir .

# The server will run until you stop it with Ctrl+C
echo "Server stopped."
