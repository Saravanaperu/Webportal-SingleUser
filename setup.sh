#!/bin/bash
#
# This script sets up the environment for the Automated Trading Portal
# on a Linux-based system.

echo "--- Automated Trading Portal Setup ---"
echo ""

# --- 1. Check for Backend Prerequisites ---
echo "Step 1: Checking for Python 3 and pip..."
if ! command -v python3 &> /dev/null
then
    echo "ERROR: python3 could not be found. Please install Python 3."
    exit 1
fi
if ! command -v pip3 &> /dev/null
then
    echo "ERROR: pip3 could not be found. Please install pip for Python 3."
    exit 1
fi
echo "Backend prerequisites found."
echo ""

# --- 2. Check for Frontend Prerequisites ---
echo "Step 2: Checking for Node.js and npm..."
if ! command -v node &> /dev/null
then
    echo "ERROR: Node.js could not be found. Please install Node.js and npm."
    exit 1
fi
if ! command -v npm &> /dev/null
then
    echo "ERROR: npm could not be found. Please install Node.js and npm."
    exit 1
fi
echo "Frontend prerequisites found."
echo ""


# --- 3. Create Virtual Environment ---
VENV_DIR="venv"
echo "Step 3: Creating Python virtual environment in './${VENV_DIR}'..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        exit 1
    fi
    echo "Virtual environment created."
else
    echo "Virtual environment './${VENV_DIR}' already exists. Skipping creation."
fi
echo ""

# --- 4. Install Backend Dependencies ---
echo "Step 4: Verifying virtual environment and installing backend packages..."
if [ ! -f "$VENV_DIR/bin/pip" ]; then
    echo "ERROR: pip not found in the virtual environment."
    echo "This can happen if the 'python3-venv' package is not installed on your system."
    echo "Please try running: sudo apt-get install python3-venv"
    echo "Then, delete the partially created 'venv' directory and run this script again."
    exit 1
fi

# Upgrade pip and setuptools first to handle modern build systems
$VENV_DIR/bin/python3 -m pip install --upgrade pip setuptools wheel
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to upgrade pip and setuptools."
    exit 1
fi

# Now, install the project dependencies
$VENV_DIR/bin/pip install -r backend/requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies from backend/requirements.txt."
    exit 1
fi
echo "Backend dependencies installed successfully."
echo ""

# --- 5. Install Frontend Dependencies ---
echo "Step 5: Installing frontend dependencies..."
cd frontend
npm install
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install frontend dependencies."
    cd ..
    exit 1
fi
cd ..
echo "Frontend dependencies installed successfully."
echo ""


# --- 6. Check for Environment File ---
ENV_FILE=".env"
echo "Step 6: Checking for environment file..."
if [ -f "$ENV_FILE" ]; then
    echo "Environment file '.env' found."
else
    echo "WARNING: Environment file '.env' not found."
    echo "Please copy '.env.example' to '.env' and fill in your Angel One API credentials."
    echo "cp .env.example .env"
fi
echo ""

# --- 7. Create Data and Logs Directories ---
echo "Step 7: Creating 'data' and 'logs' directories..."
mkdir -p data
mkdir -p logs
echo "Directories created."
echo ""

echo "--- Setup Complete! ---"
echo "To run the application, use the provided 'run.sh' script."
echo "./run.sh"
