# Automated Options Trading Portal

This project is a complete, production-ready automated trading portal designed for personal use. It provides a full-stack solution for developing, testing, and deploying an automated options scalping strategy with the AngelOne broker. The system is built with a robust FastAPI backend, a dynamic web dashboard for monitoring and control, and is fully containerized with Docker for easy deployment.

## Key Features

-   **Dynamic Options Strategy**: Automatically trades options (Calls/Puts) on underlying indices like NIFTY and BANKNIFTY.
-   **Autonomous Execution**: The bot is fully autonomous. It handles everything from selecting the correct option contract to placing entry and exit orders without manual intervention.
-   **Live Data Processing**: Connects to the AngelOne WebSocket for both market data and order updates, processing live ticks into 1-minute candles for signal generation.
-   **Advanced Risk Management**:
    -   **Portfolio Protection**: Enforces a maximum daily loss percentage and a limit on consecutive losses to protect your capital.
    -   **Dynamic Position Sizing**: Calculates trade size based on a fixed risk-per-trade percentage for equities, and uses a fixed lot size for options.
    -   **Configurable Exits**: Manages trades with stop-loss, take-profit, and a trailing stop-loss, all configurable in `config.yaml`.
-   **Dynamic Instrument Handling**:
    -   Automatically determines the current weekly expiry for options.
    -   Finds the At-The-Money (ATM) strike price based on the live price of the underlying index.
    -   Dynamically subscribes to the specific option contracts being traded.
-   **Web Dashboard**: A user-friendly interface to monitor P&L, account details, and live trades, with a real-time candlestick chart.
-   **Emergency Controls**: The dashboard provides a "Start/Stop Strategy" button and an "EMERGENCY STOP" button to halt all trading activity instantly.
-   **Database Persistence**: Uses an SQLite database with SQLAlchemy to store all trading data, including signals, orders, trades, and positions.
-   **Containerized Deployment**: Fully containerized with Docker for easy and consistent deployment across different platforms.

## Technology Stack

-   **Backend**: Python, FastAPI, Uvicorn
-   **Database**: SQLite, SQLAlchemy
-   **Frontend**: Jinja2, HTML, CSS, Vanilla JavaScript
-   **Charting**: TradingView Lightweight Charts™
-   **Data & Strategy**: Pandas, Pandas-TA, NumPy
-   **Deployment**: Docker, Docker Compose

## Getting Started

### 1. Prerequisites

-   [Docker](https://www.docker.com/get-started)
-   [Docker Compose](https://docs.docker.com/compose/install/)

### 2. Installation & Setup

1.  **Clone the repository**.

2.  **Create your Environment File**: In the project's root directory, copy the example file.
    ```sh
    cp .env.example .env
    ```

3.  **Add Your Credentials**: Open the newly created `.env` file and fill in your AngelOne API credentials. This is mandatory.

4.  **Configure Your Strategy**: Open `config.yaml` to configure the options strategy.
    -   Set the `underlyings` you want to trade (e.g., "NIFTY", "BANKNIFTY").
    -   Adjust the `sl_percentage` and `tp_percentage` for your risk appetite.
    -   Review other risk and trading hour settings.

5.  **Run the Deployment Script**:
    -   For Linux or macOS: `chmod +x ./scripts/deploy.sh && ./scripts/deploy.sh`
    -   For Windows: `.\scripts\deploy.bat`

    The script will build the Docker containers and start the application in the background.

## How to Use

-   **Access the Dashboard**: Open your web browser and navigate to `http://localhost:8000`.
-   **Control the Strategy**: Use the "Start/Stop Strategy" buttons.
-   **View Logs**: `docker-compose logs -f`.
-   **Stop the Application**: `docker-compose down`.

---

## Project Architecture

-   `backend/app/api`: Defines all REST and WebSocket API endpoints.
-   `backend/app/core`: Handles configuration management and logging.
-   `backend/app/db`: Manages the database connection and models.
-   `backend/app/services`: Houses the core business logic:
    -   `strategy.py`: The main options trading strategy engine.
    -   `order_manager.py`: Manages the lifecycle of orders.
    -   `risk_manager.py`: Enforces all risk rules.
    -   `options_helper.py`: Contains helper functions for options trading.
-   `backend/app/angel_one_connector`: Handles all communication with the broker's API.
-   `backend/app/templates` & `static`: Contains the frontend dashboard files.
-   `scripts`: Contains the user-friendly deployment scripts.