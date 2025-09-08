@echo off
setlocal

rem This script provides a robust way to deploy the trading portal on Windows.
rem It checks for dependencies, ensures the environment is set up,
rem and then uses docker-compose to build and run the application.

echo Step 1: Checking prerequisites...

rem Check for Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: docker could not be found. Please install Docker Desktop for Windows.
    goto :eof
)

rem Check for Docker Compose
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: docker-compose could not be found. It is usually included with Docker Desktop.
    goto :eof
)

echo Docker and Docker Compose found.
echo.

rem --- Environment File Check ---
echo Step 2: Checking for .env file...

if not exist .env (
    echo Warning: .env file not found.
    if not exist .env.example (
        echo Error: .env.example not found! Cannot create .env file.
        goto :eof
    )

    echo Copying from .env.example to .env...
    copy .env.example .env >nul
    echo.
    echo IMPORTANT: A new .env file has been created.
    echo Please open the '.env' file and fill in your AngelOne credentials.
    echo Then, run this script again to start the application.
    goto :eof
)

echo .env file found.
echo.

rem --- Deployment ---
echo Step 3: Starting deployment...

echo Pulling latest base images from Docker Hub...
docker-compose pull

echo Building application containers and starting services...
rem --force-recreate ensures containers are updated if the image or config changes.
rem -d runs the services in detached mode (in the background).
rem --remove-orphans cleans up any old containers from services that no longer exist.
docker-compose up --build --force-recreate --remove-orphans -d

echo.
echo ------------------------------------------------------
echo Deployment Complete!
echo.
echo   - The application is running in the background.
echo   - Access the dashboard at: http://localhost:8000
echo.
echo   - To view live logs, run:    docker-compose logs -f
echo   - To stop the application, run: docker-compose down
echo ------------------------------------------------------

endlocal
