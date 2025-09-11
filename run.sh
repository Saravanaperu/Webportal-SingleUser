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

# Build the frontend
echo "Building the frontend..."
cd frontend
npm install
npm run build
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to build the frontend."
    cd ..
    exit 1
fi
cd ..
echo "Frontend built successfully."

# Change to the backend directory
echo "Changing to backend directory..."
cd backend || { echo "Failed to change to backend directory"; exit 1; }

# Run the Uvicorn server from within the backend directory
echo "Starting FastAPI server with Uvicorn..."
echo "Access the dashboard at http://localhost:8000"
../$VENV_DIR/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../server.log 2>&1 &

# Wait for a few seconds to see the startup logs
sleep 5

# Check if the server is running
if ps -p $! > /dev/null
then
   echo "Server started successfully."
else
   echo "Server failed to start. Check server.log for details."
   cat ../server.log
   exit 1
fi

echo "The server is running in the background. To stop it, run 'kill $!'."
