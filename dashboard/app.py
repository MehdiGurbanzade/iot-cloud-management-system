import streamlit as st
import requests
import pandas as pd
import time
import os

API_URL = os.getenv("API_URL", "http://api:8000")

st.set_page_config(
    page_title="Industrial IoT Platform",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar
with st.sidebar:
    st.title("🎛️ Control Panel")
    
    st.subheader("Network Status")
    try:
        health = requests.get(f"{API_URL}/health", timeout=2)
        if health.status_code == 200:
            st.success("✅ API Gateway: ONLINE")
            st.success("✅ SQL Database: CONNECTED")
            st.success("✅ Telemetry Storage (MySQL): ACTIVE")
            st.success("✅ Cache Layer: READY")
        else:
            st.error("⚠️ Network Issues")
    except:
        st.error("❌ SYSTEM OFFLINE")
        st.stop()

    st.markdown("---")
    st.subheader("Settings")
    auto_refresh = st.checkbox("Auto-Refresh Data", value=True)
    show_raw = st.checkbox("Show Raw Payload", value=False)

# main page
st.title("🏭 IoT Sensor Data Platform")
st.markdown("Centralized monitoring system for connected IoT devices. Data Pipeline: **Device** -> **Cloud API** -> **MySQL + Redis**.")

# analyzes and statistics
st.subheader("📊 System Metrics")
try:
    stats_req = requests.get(f"{API_URL}/stats/summary")
    if stats_req.status_code == 200:
        stats = stats_req.json()
        k1, k2, k3, k4 = st.columns(4)
        
        k1.metric("Total Packets Received", stats.get('total_readings', 0))
        k2.metric("Avg Temperature", f"{stats.get('avg_temp', 0):.1f} °C")
        k3.metric("Max Temperature Recorded", f"{stats.get('max_temp', 0):.1f} °C")
        k4.metric("Avg Humidity", f"{stats.get('avg_humidity', 0):.1f} %")
    else:
        st.info("Initializing analytics module...")
except:
    st.warning("Waiting for data stream...")

st.markdown("---")

# data
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📡 Active IoT Devices (SQL)")
    try:
        dev_req = requests.get(f"{API_URL}/devices")
        if dev_req.status_code == 200:
            devices = dev_req.json()
            df = pd.DataFrame(devices)
            st.dataframe(df, hide_index=True, use_container_width=True)
            
            selected_device = st.selectbox("Select Node to Inspect:", df["device_name"] if not df.empty else [])
        else:
            st.warning("No active nodes found.")
            selected_device = None
    except:
        st.error("Failed to fetch device registry.")
        selected_device = None

with col2:
    st.subheader("📉 Live Sensor Telemetry (SQL + Cache)")
    if selected_device:
        placeholder = st.empty()
        with placeholder.container():
            try:
                data_req = requests.get(f"{API_URL}/sensor-data/latest/{selected_device}")
                if data_req.status_code == 200:
                    data = data_req.json()
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Temperature", f"{data['temperature']} °C", delta="Live")
                    m2.metric("Humidity", f"{data['humidity']} %", delta="Live")
                    m3.metric("Signal Status", "OK ✅")
                    
                    st.info(f"⏱️ Packet Time: {data['timestamp']}")
                    
                    if show_raw:
                        st.caption("JSON Payload:")
                        st.code(data, language='json')
                else:
                    st.warning("Waiting for next data packet...")
            except:
                pass
    else:
        st.info("Select a device to view live stream.")

if auto_refresh:
    time.sleep(2)
    st.rerun()