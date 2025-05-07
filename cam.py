import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
import time
from PIL import Image
from io import BytesIO

# Configuration
USERNAME = "admin"
PASSWORD = "password123"

# URLs
CHANNEL1_API_URL = "https://api.thingspeak.com/channels/2695368/feeds.json?results=1"
CHANNEL2_API_URL = "https://api.thingspeak.com/channels/2844558/feeds.json?results=1"
ESP32_CAM_URL = "http://172.20.10.3/capture"  # Replace with your actual ESP32-CAM stream URL for capturing images

# Thresholds
GAS_THRESHOLD = 300
FALL_KEYWORD = "Fall"

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "sensor_data_worker1" not in st.session_state:
    st.session_state.sensor_data_worker1 = pd.DataFrame()

if "sensor_data_worker2" not in st.session_state:
    st.session_state.sensor_data_worker2 = pd.DataFrame()

# Login Page
def login_page():
    st.title("🔐 Login Page")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == USERNAME and password == PASSWORD:
            st.session_state.logged_in = True
            st.success("✅ Logged in successfully!")
            time.sleep(1)
            st.rerun()

        else:
            st.error("❌ Invalid username or password!")

# Fetch data from ThingSpeak
def get_channel1_data():
    try:
        response = requests.get(CHANNEL1_API_URL, timeout=5)
        data = response.json()
        latest = data["feeds"][-1]
        return {
            "accX": float(latest["field1"] or 0),
            "accY": float(latest["field2"] or 0),
            "accZ": float(latest["field3"] or 0),
            "mq9": float(latest["field6"] or 0),
            "temp_env": float(latest["field4"] or 0),
            "humidity": float(latest["field5"] or 0),
            "battery": float(latest["field7"] or 0),
            "fall_status": latest["field8"] or "Unknown"
        }
    except Exception:
        return None

def get_channel2_data():
    try:
        response = requests.get(CHANNEL2_API_URL, timeout=5)
        data = response.json()
        latest = data["feeds"][-1]
        return {
            "bpm": float(latest["field1"] or 0),
            "avg_bpm": float(latest["field2"] or 0),
            "temp_health": float(latest["field3"] or 0)
        }
    except Exception:
        return None

# Dummy Worker 2 Data
def get_dummy_worker2_data():
    now = datetime.now()
    return {
        "accX": 0.5,
        "accY": 0.3,
        "accZ": 9.8,
        "mq9": 150,
        "temp_env": 22.5,
        "humidity": 55,
        "battery": 3.7,
        "fall_status": "No Fall",
        "bpm": 78,
        "avg_bpm": 75,
        "temp_health": 36.5,
        "timestamp": now
    }

# Alert Checker
def check_alerts(data):
    alerts = []
    if data["mq9"] >= GAS_THRESHOLD:
        alerts.append("⚠️ High Gas Level Detected!")
    if FALL_KEYWORD.lower() in data["fall_status"].lower():
        alerts.append("🚨 Fall Detected!")
    return alerts

# ESP32-CAM Test
def fetch_cam_image(url):
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            return image
        else:
            return None
    except:
        return None

# Main Dashboard
def main_dashboard():
    st.set_page_config(page_title="Sensor Dashboard", layout="wide")
    st.title("📊 Real-Time Sensor Monitoring Dashboard")

    worker_option = st.sidebar.selectbox("Select Worker", ["Worker 1", "Worker 2"])

    if worker_option == "Worker 1":
        ch1_data = get_channel1_data()
        ch2_data = get_channel2_data()

        if ch1_data and ch2_data:
            now = datetime.now()
            full_data = {**ch1_data, **ch2_data, "timestamp": now}
            st.session_state.sensor_data_worker1 = pd.concat(
                [st.session_state.sensor_data_worker1, pd.DataFrame([full_data])],
                ignore_index=True
            )

            # Alerts
            for alert in check_alerts(ch1_data):
                st.error(alert)

            # Display metrics
            st.subheader("📌 Worker 1 Live Sensor Metrics")
            col1, col2, col3 = st.columns(3)
            col1.metric("Acc X", f"{ch1_data['accX']} m/s²")
            col2.metric("Acc Y", f"{ch1_data['accY']} m/s²")
            col3.metric("Acc Z", f"{ch1_data['accZ']} m/s²")

            col4, col5, col6 = st.columns(3)
            col4.metric("MQ9 Gas", ch1_data["mq9"])
            col5.metric("Env Temp", f"{ch1_data['temp_env']}°C")
            col6.metric("Humidity", f"{ch1_data['humidity']}%")

            col7, col8, col9 = st.columns(3)
            col7.metric("Battery", f"{ch1_data['battery']} V")
            col8.metric("Fall", ch1_data["fall_status"])
            col9.metric("BPM", ch2_data["bpm"])

            col10, col11 = st.columns(2)
            col10.metric("Avg BPM", ch2_data["avg_bpm"])
            col11.metric("Body Temp", f"{ch2_data['temp_health']}°C")

            # Image Stream (Replacing video stream)
            st.subheader("📹 Live ESP32-CAM Image Stream")
            image = fetch_cam_image(ESP32_CAM_URL)
            if image:
                st.image(image, use_column_width=True)
            else:
                st.warning("🚫 ESP32-CAM Deactivated or Not Reachable!")

            # Graphs
            df = st.session_state.sensor_data_worker1.copy()
            df = df[df["timestamp"] >= datetime.now() - timedelta(hours=1)]
            if not df.empty:
                st.subheader("📈 Acceleration Over Time (1 Hour)")
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=df["timestamp"], y=df["accX"], name="Acc X"))
                fig1.add_trace(go.Scatter(x=df["timestamp"], y=df["accY"], name="Acc Y"))
                fig1.add_trace(go.Scatter(x=df["timestamp"], y=df["accZ"], name="Acc Z"))
                fig1.update_layout(title="Acceleration", xaxis_title="Time", yaxis_title="m/s²")
                st.plotly_chart(fig1, use_container_width=True)

                st.subheader("❤️ Health Parameters Over Time (1 Hour)")
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=df["timestamp"], y=df["bpm"], name="BPM"))
                fig2.add_trace(go.Scatter(x=df["timestamp"], y=df["avg_bpm"], name="Avg BPM"))
                fig2.add_trace(go.Scatter(x=df["timestamp"], y=df["temp_health"], name="Body Temp"))
                fig2.update_layout(title="Health Monitoring", xaxis_title="Time", yaxis_title="Value")
                st.plotly_chart(fig2, use_container_width=True)

            # Data Table
            st.subheader("📋 Worker 1 Data Log")
            st.dataframe(df.tail(50))

            # Download Button
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Worker 1 Data", data=csv, file_name="worker1_data.csv", mime="text/csv")

            time.sleep(1)
            st.rerun()


        else:
            st.error("⚠️ Could not fetch data from ThingSpeak. Please check your API or network.")

    elif worker_option == "Worker 2":
        dummy = get_dummy_worker2_data()
        st.session_state.sensor_data_worker2 = pd.concat(
            [st.session_state.sensor_data_worker2, pd.DataFrame([dummy])],
            ignore_index=True
        )

        st.subheader("📌 Worker 2 Live Sensor Metrics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Acc X", f"{dummy['accX']} m/s²")
        col2.metric("Acc Y", f"{dummy['accY']} m/s²")
        col3.metric("Acc Z", f"{dummy['accZ']} m/s²")

        col4, col5, col6 = st.columns(3)
        col4.metric("MQ9 Gas", dummy["mq9"])
        col5.metric("Env Temp", f"{dummy['temp_env']}°C")
        col6.metric("Humidity", f"{dummy['humidity']}%")

        col7, col8, col9 = st.columns(3)
        col7.metric("Battery", f"{dummy['battery']} V")
        col8.metric("Fall", dummy["fall_status"])
        col9.metric("BPM", dummy["bpm"])

        col10, col11 = st.columns(2)
        col10.metric("Avg BPM", dummy["avg_bpm"])
        col11.metric("Body Temp", f"{dummy["temp_health"]}°C")

        df = st.session_state.sensor_data_worker2.copy()
        df = df[df["timestamp"] >= datetime.now() - timedelta(hours=1)]

        if not df.empty:
            st.subheader("📈 Worker 2 Acceleration Over Time")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["timestamp"], y=df["accX"], name="Acc X"))
            fig.add_trace(go.Scatter(x=df["timestamp"], y=df["accY"], name="Acc Y"))
            fig.add_trace(go.Scatter(x=df["timestamp"], y=df["accZ"], name="Acc Z"))
            fig.update_layout(title="Acceleration", xaxis_title="Time", yaxis_title="m/s²")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("❤️ Worker 2 Health Metrics Over Time")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df["timestamp"], y=df["bpm"], name="BPM"))
            fig2.add_trace(go.Scatter(x=df["timestamp"], y=df["avg_bpm"], name="Avg BPM"))
            fig2.add_trace(go.Scatter(x=df["timestamp"], y=df["temp_health"], name="Body Temp"))
            fig2.update_layout(title="Health Metrics", xaxis_title="Time", yaxis_title="Value")
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📋 Worker 2 Data Log")
        st.dataframe(df.tail(50))

        # Download Button
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Worker 2 Data", data=csv, file_name="worker2_data.csv", mime="text/csv")

        time.sleep(1)
        st.rerun()


# Login validation
if st.session_state.logged_in:
    main_dashboard()
else:
    login_page()
