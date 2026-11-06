import time
import random
import requests
import os
import sys

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
TOKEN_URL = f"{API_URL}/token"
DATA_URL = f"{API_URL}/sensor-data"

# Sensors
DEVICES = ["Sensor-001", "Sensor-002", "Sensor-003", "Sensor-004"]

# Username password 
USERNAME = "admin"
PASSWORD = os.getenv("SIM_PASSWORD")  # same value as ADMIN_PASSWORD, passed in by docker-compose

def get_access_token():
    """
    Docstring for get_access_token
    
    :return: Description
    :rtype: Any | None
    """
    print(f"🔐 Logging in as {USERNAME}...")
    try:
        response = requests.post(TOKEN_URL, data={"username": USERNAME, "password": PASSWORD})
        if response.status_code == 200:
            token = response.json()["access_token"]
            print("✅ Login Successful! Token acquired.")
            return token
        else:
            print(f"❌ Login Failed: {response.text}")
            return None
    except Exception as e:
        print(f"⚠️ Connection Error (Is API running?): {e}")
        return None

# program is starting
print(f"🏭 Starting Industrial IoT Simulator...")
print(f"🎯 Target: {DATA_URL}")

# Await for API
time.sleep(10)

# get first token
token = get_access_token()

# loop 
while True:
    # if there is no any token, get that again
    if not token:
        print("🔄 No token. Retrying login...")
        token = get_access_token()
        time.sleep(5)
        continue

    try:
        # select random device
        device_id = random.choice(DEVICES)
        
        #  smart temp function
        temperature = 0.0
        humidity = 0.0

        if device_id == "Sensor-001": 
            # server room 
            temperature = round(random.uniform(-5.0, 5.0), 2)
            humidity = round(random.uniform(70.0, 80.0), 2)
            
        elif device_id == "Sensor-002": 
            # storage room
            temperature = round(random.uniform(-5.0, 5.0), 2)
            humidity = round(random.uniform(80.0, 90.0), 2) # humid
            
        else: 
            # logistic zone and generator room
            temperature = round(random.uniform(20.0, 30.0), 2)
            humidity = round(random.uniform(40.0, 60.0), 2)

       
        payload = {
            "device_id": device_id,
            "temperature": temperature,
            "humidity": humidity
        }

        # send it to API with token
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(DATA_URL, json=payload, headers=headers)
        
        #  check answer
        if response.status_code == 200:
            print(f"📡 Sent to {device_id}: {temperature}°C | Status: 200 OK")
            
        elif response.status_code == 401: 
           
            print("⚠️ Token expired. Refreshing credentials...")
            token = get_access_token()
            
        else:
            print(f"❌ Failed: {response.status_code} | {response.text}")

    except Exception as e:
        print(f"⚠️ Error sending data: {e}")
      
    
  
    time.sleep(5)