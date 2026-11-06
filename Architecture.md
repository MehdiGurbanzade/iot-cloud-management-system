# System Architecture

## Overview

This project is an **Industrial IoT Platform**. It collects temperature and humidity data from simulated devices (factory sensors) and shows them on a dashboard.

We use a **microservices** approach (Docker containers). Services talk to each other over an internal Docker network.

## Architecture Diagram

                                ┌─────────────────────────┐
                                │   Operator / Admin      │
                                └───────────┬─────────────┘
                                            │
                     ┌──────────────────────┼──────────────────────┐
                     │                      │                      │
                     ▼                      ▼                      ▼
          ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
          │   Dashboard      │   │   Swagger UI     │   │   Direct API     │
          │   (Streamlit)    │   │   /docs          │   │   Access         │
          │   Port 8501      │   │                  │   │   (Secure)       │
          └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
                   │                      │                      │
                   └──────────────────────┼──────────────────────┘
                                          │
                                ┌─────────▼──────────┐
                                │   FastAPI Gateway  │
                                │   Port 8000        │
                                │   - Auth (OAuth2)  │
                                │   - Validation     │
                                │   - Routing        │
                                └─────────┬──────────┘
                                          │
                         ┌────────────────┼────────────────┐
                         │                                 │
                         ▼                                 ▼
              ┌──────────────────┐              ┌──────────────────┐
              │   MySQL          │              │   Redis          │
              │   Port 3306      │              │   Port 6379      │
              │   - devices      │              │   - last_reading │
              │   - sensor_read. │              │   - cache layer  │
              └──────────────────┘              └──────────────────┘
                         ▲
                         │
                ┌────────┴───────────┐
                │  Sensor Simulator  │
                │  - Python Script   │
                │  - Generates Data  │
                └────────────────────┘
                         ▲
                         │
                ┌────────┴───────────┐
                │   Device Loader    │
                │   - Init Script    │
                │   - Runs Once      │
                └────────────────────┘


## How It Works (Simple Explanation)

### 1. The User Interface (Frontend)
* **Streamlit Dashboard (`dashboard/`)** shows live telemetry and simple analytics.
* It does NOT connect to databases directly; it calls the API.

### 2. The Brain (Backend)
* **FastAPI (`api/`)** is the center of the system:
  * OAuth2 login and JWT access tokens
  * validates incoming payloads with Pydantic
  * writes telemetry to MySQL + updates Redis cache

### 3. The Memory (Storage)
We keep the system simple (teacher-friendly) with **SQL + Cache**:

* **MySQL**
  * `devices` table: device registry (rarely changes)
  * `sensor_readings` table: telemetry history (append-only time series)
* **Redis**
  * keeps only the latest reading per device (`last_reading:{device_id}`) for fast dashboards

### 4. The Workers
* **Sensor Simulator (`sensor-simulator/`)** generates fake readings every 5 seconds and pushes them to the API.
* **Device Loader (`device-loader/`)** runs once to create required MySQL tables and insert initial devices.

---

## Data Flow

### Write Path (Saving data)
1. Simulator logs in and gets a token.
2. Simulator sends payload to `POST /sensor-data`.
3. API stores the reading in **MySQL (`sensor_readings`)**.
4. API updates **Redis** with the latest reading.

### Read Path (Showing data)
1. Dashboard calls `GET /sensor-data/latest/{device_id}`.
2. API checks Redis first (fast).
3. If cache miss, API reads the latest record from MySQL.

---

## Security Features

* **OAuth2 + JWT** for protected telemetry endpoints.
* **Secrets in `.env`** (no hard-coded passwords).
* **Health checks** in Docker Compose to ensure services are running.
