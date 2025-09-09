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

# Activate the virtual environment
echo "Activating virtual environment..."
source $VENV_DIR/bin/activate

# Change to the backend directory
echo "Changing to backend directory..."
cd backend

# Run the Uvicorn server
echo "Starting FastAPI server with Uvicorn..."
echo "Access the dashboard at http://localhost:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Deactivate on exit (e.g., Ctrl+C)
echo "Server stopped."
deactivate
