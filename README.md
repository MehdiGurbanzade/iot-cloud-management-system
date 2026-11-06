# Industrial IoT Sensor Platform 🏭

## Overview

Cloud-native **Industrial IoT Platform** that simulates sensors collecting temperature + humidity data, stores telemetry, and visualizes it on a real-time dashboard.

Architecture: **Microservices (Docker)** + **FastAPI** + **MySQL (SQL storage)** + **Redis (cache)**.

---

## 🏗️ System Architecture

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
                └────────────────────┘
                         ▲
                         │
                ┌────────┴───────────┐
                │   Device Loader    │
                └────────────────────┘

---

## 🔍 How It Works

### Storage Design (Why no MongoDB?)
For a project of this size, keeping telemetry in **one SQL database** is simpler to operate and easier to justify:

* **MySQL**
  * `devices` table: device registry
  * `sensor_readings` table: telemetry history (append-only)
* **Redis**
  * stores the latest reading per device for fast UI updates

---

## 🛡️ Security Features

* **OAuth2 + JWT** token system.
* Secrets stored in **`.env`**.
* Docker **health checks**.

---

## 🚀 Running the Project

1. Ensure Docker Desktop is running.
2. Copy `.env.example` to `.env` and fill in every value (database credentials, `SECRET_KEY` for signing JWTs, `ADMIN_PASSWORD` for the API login).
3. From the project folder:
   ```bash
   docker-compose up --build
   ```
4. Dashboard: `http://localhost:8501`
5. API Docs: `http://localhost:8000/docs` (Login: `admin` / the `ADMIN_PASSWORD` from your `.env`)

---

**Author:** Mehdi Gurbanzade · M.Sc. Data Science
