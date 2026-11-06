from datetime import datetime, timedelta
import json
import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import get_mysql_connection, get_redis_client
from models import Device, SensorData


tags_metadata = [
    {"name": "Auth", "description": "Security & Access Control"},
    {"name": "IoT Registry", "description": "Device Management (MySQL)"},
    {"name": "Telemetry", "description": "Sensor Data (MySQL + Redis cache)"},
    {"name": "Analytics", "description": "Aggregations over telemetry (MySQL)"},
    {"name": "System", "description": "Healthchecks"},
]

app = FastAPI(
    title="Industrial IoT Cloud API",
    description="""
Backend infrastructure for collecting, storing, and analyzing data from distributed IoT sensors.

Features: OAuth2, SQL storage (MySQL) and in-memory caching (Redis).
""",
    version="3.1.0",
    openapi_tags=tags_metadata,
)

# -------------------------
# Security (OAuth2 / JWT)
# -------------------------
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set. Copy .env.example to .env and fill it in.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD is not set. Copy .env.example to .env and fill it in.")

FAKE_USERS_DB = {
    "admin": {"username": "admin", "password_hash": pwd_context.hash(ADMIN_PASSWORD)}
}


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username


# -------------------------
# DB helpers (MySQL)
# -------------------------
def insert_sensor_reading_mysql(data: SensorData) -> None:
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO sensor_readings (device_id, temperature, humidity, timestamp)
        VALUES (%s, %s, %s, %s)
        """,
        (data.device_id, data.temperature, data.humidity, data.timestamp),
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_latest_reading_mysql(device_id: str):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT device_id, temperature, humidity, timestamp
        FROM sensor_readings
        WHERE device_id = %s
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (device_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return None

    # Make timestamp JSON-friendly and consistent with Redis cached values
    if isinstance(row.get("timestamp"), datetime):
        row["timestamp"] = row["timestamp"].isoformat()

    return row


def get_summary_stats_mysql():
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            COUNT(*) AS total_readings,
            AVG(temperature) AS avg_temp,
            MAX(temperature) AS max_temp,
            AVG(humidity) AS avg_humidity
        FROM sensor_readings
        """
    )
    stats = cursor.fetchone()
    cursor.close()
    conn.close()

    if not stats or stats.get("total_readings", 0) == 0:
        return {"message": "Initializing..."}

    # mysql-connector may return Decimal for AVG; cast safely
    def to_float(v):
        return float(v) if v is not None else 0.0

    return {
        "total_readings": int(stats.get("total_readings", 0)),
        "avg_temp": to_float(stats.get("avg_temp")),
        "max_temp": to_float(stats.get("max_temp")),
        "avg_humidity": to_float(stats.get("avg_humidity")),
    }


# -------------------------
# Endpoints
# -------------------------
@app.post("/token", tags=["Auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or not pwd_context.verify(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {
        "access_token": create_access_token(data={"sub": user["username"]}),
        "token_type": "bearer",
    }


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "operational", "modules": ["API", "MySQL", "Redis"]}


@app.get("/devices", tags=["IoT Registry"])
def get_devices():
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM devices")
        devices = cursor.fetchall()
        cursor.close()
        conn.close()
        return devices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sensor-data", tags=["Telemetry"])
def add_sensor_data(data: SensorData, current_user: str = Depends(get_current_user)):
    """Write telemetry to MySQL (history) + Redis (latest cache)."""

    try:
        insert_sensor_reading_mysql(data)

        r = get_redis_client()
        r.set(f"last_reading:{data.device_id}", json.dumps(data.dict(), default=str))

        return {"status": "accepted", "timestamp": datetime.now()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sensor-data/latest/{device_id}", tags=["Telemetry"])
def get_latest_reading(device_id: str):
    try:
        # 1) cache first
        r = get_redis_client()
        cached = r.get(f"last_reading:{device_id}")
        if cached:
            return json.loads(cached)

        # 2) fallback to MySQL history
        reading = get_latest_reading_mysql(device_id)
        if reading:
            return reading

        raise HTTPException(status_code=404, detail="No data")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/summary", tags=["Analytics"])
def get_system_stats():
    try:
        return get_summary_stats_mysql()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
