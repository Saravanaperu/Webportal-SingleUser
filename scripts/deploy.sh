#!/bin/bash

# This script provides a robust way to deploy the trading portal.
# It checks for dependencies, ensures the environment is set up,
# and then uses docker-compose to build and run the application.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Helper Functions ---
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# --- Prerequisite Checks ---
echo "Step 1: Checking prerequisites..."

if ! command_exists docker; then
    echo "Error: docker could not be found. Please install Docker before running this script."
    exit 1
fi

if ! command_exists docker-compose; then
    echo "Error: docker-compose could not be found. Please install Docker Compose."
    exit 1
fi

echo "Docker and Docker Compose found."

# --- Environment File Check ---
echo "Step 2: Checking for .env file..."

if [ ! -f .env ]; then
    echo "Warning: .env file not found."
    if [ ! -f .env.example ]; then
        echo "Error: .env.example not found! Cannot create .env file. Please restore it."
        exit 1
    fi

    echo "Copying from .env.example to .env..."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: A new .env file has been created."
    echo "Please open the '.env' file and fill in your AngelOne credentials."
    echo "Then, run this script again to start the application."
    exit 0
fi

echo ".env file found."

# --- Deployment ---
echo "Step 3: Starting deployment..."

echo "Pulling latest base images from Docker Hub..."
docker-compose pull

echo "Building application containers and starting services..."
# --force-recreate ensures containers are updated if the image or config changes.
# -d runs the services in detached mode (in the background).
# --remove-orphans cleans up any old containers from services that no longer exist.
docker-compose up --build --force-recreate --remove-orphans -d

echo ""
echo "------------------------------------------------------"
echo "✅ Deployment Complete!"
echo ""
echo "  - The application is running in the background."
echo "  - Access the dashboard at: http://localhost:8000"
echo ""
echo "  - To view live logs, run:    docker-compose logs -f"
echo "  - To stop the application, run: docker-compose down"
echo "------------------------------------------------------"

exit 0
