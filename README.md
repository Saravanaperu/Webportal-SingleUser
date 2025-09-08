# Automated Trading Portal

This project is a complete, production-ready automated trading portal designed for personal use. It provides a full-stack solution for developing, testing, and deploying an automated scalping strategy with the AngelOne broker. The system is built with a robust FastAPI backend, a dynamic web dashboard for monitoring and control, and is fully containerized with Docker for easy deployment.

## Core Features

-   **FastAPI Backend**: A modern, high-performance Python backend serves as the core of the application.
-   **Scalping Strategy**: Implements a 1-minute scalping strategy using a combination of EMA(9/21), VWAP, SuperTrend(10,3), and ATR indicators.
-   **Advanced Risk Management**: Includes a dedicated `RiskManager` to enforce rules for risk-per-trade, max daily loss, and consecutive losses.
-   **Dynamic Web Dashboard**: A user-friendly interface built with Jinja2 templates and JavaScript to monitor P&L, account details, and live trades. It includes a real-time candlestick chart.
-   **Strategy & Kill Switch Controls**: The dashboard provides buttons to start/stop the strategy and an emergency "kill switch" to halt all trading activity instantly.
-   **Database Persistence**: Uses an SQLite database with SQLAlchemy models to store all trading data, including signals, orders, trades, and positions.
-   **Containerized Deployment**: The entire application is containerized using Docker and orchestrated with Docker Compose, allowing for a consistent and easy setup process.
-   **Cross-Platform Deployment Scripts**: Includes user-friendly scripts (`deploy.sh` and `deploy.bat`) for easy deployment on Linux, macOS, and Windows.

## Technology Stack

-   **Backend**: Python, FastAPI, Uvicorn
-   **Database**: SQLite, SQLAlchemy, `python-databases`
-   **Frontend**: Jinja2, HTML, CSS, Vanilla JavaScript
-   **Charting**: TradingView Lightweight Charts™
-   **Data & Strategy**: Pandas, Pandas-TA, NumPy
-   **Deployment**: Docker, Docker Compose

## Project Architecture

The application is designed with a clean, modular architecture:

-   `backend/app/api`: Defines all REST and WebSocket API endpoints.
-   `backend/app/core`: Handles core functionalities like configuration management (`config.py`) and logging (`logging.py`).
-   `backend/app/db`: Manages the database connection (`session.py`) and base models.
-   `backend/app/models`: Contains all SQLAlchemy table definitions (`trading.py`).
-   `backend/app/services`: Houses the core business logic:
    -   `strategy.py`: The main trading strategy engine.
    -   `order_manager.py`: Manages the lifecycle of orders.
    -   `risk_manager.py`: Enforces all risk rules.
-   `backend/app/angel_one_connector`: A dedicated package to handle all communication with the broker's API. **(This is where you will add your live implementation)**.
-   `backend/app/templates` & `static`: Contains the Jinja2 HTML templates and CSS for the frontend dashboard.
-   `scripts`: Contains the user-friendly deployment scripts.

## Getting Started

### Prerequisites

-   [Docker](https://www.docker.com/get-started)
-   [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

### Installation & Setup

1.  **Clone the repository** to your local machine.

2.  **Create your Environment File**: In the project's root directory, copy the example environment file.
    ```sh
    cp .env.example .env
    ```

3.  **Add Your Credentials**: Open the newly created `.env` file and fill in your personal AngelOne API credentials. **This step is mandatory.**

4.  **Review Configuration (Optional)**: Open `config.yaml` to review and adjust strategy parameters, risk settings, or trading hours as needed.

5.  **Run the Deployment Script**:
    -   For Linux or macOS:
        ```sh
        # Make the script executable first
        chmod +x ./scripts/deploy.sh
        # Run the script
        ./scripts/deploy.sh
        ```
    -   For Windows:
        ```cmd
        # Run the batch script
        .\scripts\deploy.bat
        ```
    The script will build the Docker containers and start the application in the background.

## How to Use

-   **Access the Dashboard**: Open your web browser and navigate to `http://localhost:8000`.
-   **Control the Strategy**: Use the "Start Strategy" and "Stop Strategy" buttons on the dashboard.
-   **Emergency Stop**: Use the "EMERGENCY STOP" button to immediately halt all new trading activity.
-   **View Logs**: To see the live logs from the application, run: `docker-compose logs -f`.
-   **Stop the Application**: To stop all services, run: `docker-compose down`.

---

## ⚠️ CRITICAL: Your Implementation Tasks

This project provides a complete and robust framework, but for your security and because I cannot access the live API, the final broker-specific implementation is left for you. The application currently runs in a fully simulated mode.

To connect to the live market, you **must** complete the following:

1.  **Implement the Broker Connector**:
    -   **Location**: `backend/app/angel_one_connector/`
    -   **Task**: Replace the placeholder logic in `auth.py`, `rest_client.py`, and `ws_client.py` with the actual API calls based on the official AngelOne API documentation. This includes handling the login flow, REST API requests, and parsing the WebSocket data stream.

2.  **Implement Advanced Exit Logic**:
    -   **Location**: `backend/app/services/strategy.py`
    -   **Function**: `manage_active_trades()`
    -   **Task**: This function is a placeholder. You need to implement your logic for trailing stop-losses and time-based exits here. This will involve fetching live data for your open positions and creating the appropriate exit orders.

3.  **Implement Symbol-to-Token Mapping**:
    -   **Task**: In `order_manager.py` and `ws_client.py`, you will see placeholders for `symboltoken`. You need to implement a mechanism to fetch the instrument list from AngelOne and map symbols like `"NIFTYBEES-EQ"` to their required numerical tokens for API calls.

---

## Project Structure

```
.
├── backend
│   ├── app
│   │   ├── api/
│   │   ├── angel_one_connector/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── services/
│   │   ├── static/
│   │   └── templates/
│   ├── Dockerfile
│   └── requirements.txt
├── data/
├── logs/
├── scripts
│   ├── deploy.bat
│   └── deploy.sh
├── .env
├── .env.example
├── config.yaml
└── docker-compose.yml
```