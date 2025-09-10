#!/bin/bash
#
# This script runs the test suite for the Automated Trading Portal.
# It assumes you have already run setup.sh to create the environment.

VENV_DIR="venv"

# Set the environment state to 'test'
export ENV_STATE=test

# Check if the virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: Virtual environment not found at './${VENV_DIR}'."
    echo "Please run the setup.sh script first."
    exit 1
fi

# Run pytest using the venv's python
echo "Running pytest..."
./$VENV_DIR/bin/pytest

echo "Tests finished."
