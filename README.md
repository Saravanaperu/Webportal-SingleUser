# Automated Trading Portal

This project is a complete, production-ready automated trading portal designed for personal use. It provides a full-stack solution for developing, testing, and deploying an automated scalping strategy with the AngelOne broker. The system is built with a robust FastAPI backend and a dynamic web dashboard for monitoring and control.

## Core Features

-   **FastAPI Backend**: A modern, high-performance Python backend serves as the core of the application.
-   **Live Scalping Strategy**: Implements a 1-minute scalping strategy using a combination of EMA(9/21), VWAP, SuperTrend(10,3), and ATR indicators, running on live market data.
-   **Full Order Lifecycle**: Manages orders from signal generation to execution, tracking open positions and their live P&L.
-   **Advanced Exit Logic**: Implements Stop-Loss, Take-Profit, Time-Based Exits, and a simple ATR-based Trailing Stop-Loss.
-   **Dynamic Web Dashboard**: A user-friendly interface to monitor P&L, account details, open positions, and today's orders in real-time.
-   **Strategy & Kill Switch Controls**: The dashboard provides buttons to start/stop the strategy and an emergency "kill switch" to halt all trading activity instantly.
-   **Database Persistence**: Uses an SQLite database to store all trading data, including signals, orders, and trades.

## Technology Stack

-   **Backend**: Python, FastAPI, Uvicorn
-   **Database**: SQLite, SQLAlchemy
-   **Frontend**: Jinja2, HTML, CSS, Vanilla JavaScript
-   **Charting**: TradingView Lightweight Charts™
-   **Data & Strategy**: Pandas, Pandas-TA, NumPy

---

## Getting Started

This guide explains how to set up and run the application on a bare-metal operating system (Linux, macOS, or Windows) without Docker.

### **1. Clone the Repository**

First, clone the repository to your local machine.

### **2. Create Your Environment File**

In the project's root directory, copy the example environment file. This file is where you will store your broker credentials.

```sh
# For Linux or macOS
cp .env.example .env

# For Windows
copy .env.example .env
```

Open the newly created `.env` file with a text editor and fill in your personal Angel One API credentials. **This step is mandatory.**

### **3. Run the Setup Script**

The setup script will create a Python virtual environment and install all the necessary dependencies.

-   **For Linux or macOS**:
    ```sh
    # Make the script executable first
    chmod +x setup.sh
    # Run the setup script
    ./setup.sh
    ```

-   **For Windows**:
    ```cmd
    # Run the setup batch script
    .\setup.bat
    ```

### **4. Run the Application**

Once the setup is complete, you can start the trading portal.

-   **For Linux or macOS**:
    ```sh
    ./run.sh
    ```

-   **For Windows**:
    ```cmd
    .\run.bat
    ```

The script will start the web server.

## How to Use

-   **Access the Dashboard**: Open your web browser and navigate to `http://localhost:8000`.
-   **Control the Strategy**: Use the "Start Strategy" and "Stop Strategy" buttons on the dashboard.
-   **Monitor Activity**: Watch the "Open Positions" and "Today's Orders" tables to see the bot's activity in real-time.
-   **Emergency Stop**: Use the "EMERGENCY STOP" button to immediately halt all new trading activity.
-   **Stop the Application**: To stop the server, go to the terminal where you ran the `run` script and press `Ctrl+C`.

## Optional: Telegram Notifications

This project includes an optional feature to send you real-time notifications about trading activity via a Telegram bot.

### **How to Set It Up**

1.  **Create a Telegram Bot**:
    *   Open Telegram and search for the `@BotFather` bot.
    *   Start a chat with BotFather and send the `/newbot` command.
    *   Follow the prompts to name your bot and choose a username.
    *   BotFather will give you a unique **Bot Token**. Copy this value.

2.  **Get Your Chat ID**:
    *   Search for the `@userinfobot` bot on Telegram and start a chat with it.
    *   It will immediately send you a message containing your **Chat ID**. Copy this value.

3.  **Update Your Environment File**:
    *   Open your `.env` file.
    *   Paste the Bot Token and Chat ID into the `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` fields, respectively.

4.  **Start Your Bot**:
    *   You must send the `/start` command (or any message) to your new bot from your personal Telegram account before it can send you messages.

Once configured, the application will automatically start sending notifications when you run it.

---

## Project Architecture

The application is designed with a clean, modular architecture:

-   `backend/app/api`: Defines all REST and WebSocket API endpoints.
-   `backend/app/core`: Handles core functionalities like configuration management and logging.
-   `backend/app/db`: Manages the database connection and base models.
-   `backend/app/models`: Contains all SQLAlchemy table definitions.
-   `backend/app/services`: Houses the core business logic (`strategy.py`, `order_manager.py`, `risk_manager.py`).
-   `backend/app/angel_one_connector`: A dedicated package to handle all communication with the broker's API.
-   `backend/app/templates` & `static`: Contains the Jinja2 HTML templates, CSS, and JavaScript for the frontend dashboard.
-   `setup.sh`, `run.sh`: Setup and execution scripts for Linux/macOS.
-   `setup.bat`, `run.bat`: Setup and execution scripts for Windows.