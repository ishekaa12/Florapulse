# FloraPulse: IoT Smart Plant Irrigation System
 
FloraPulse is an IoT-based smart irrigation system. An ESP32 reads soil moisture, temperature, humidity and rain, and sends the data over Wi-Fi to a FastAPI backend. The backend stores every reading in SQLite, decides whether the plant needs water using soil moisture and the OpenWeather forecast, and sends a pump command back to the device. A Streamlit dashboard shows live and historical data, the pump status and the reasoning behind each decision.
 
Built as a third-semester mini project at Usha Mittal Institute of Technology, SNDT Women's University, Mumbai.
 
## How it works
 
```
ESP32 --POST reading (X-Device-Key)--> FastAPI --> SQLite
                                         |  checks cached OpenWeather forecast
                                         |  applies the irrigation rule
ESP32 <--{"pump":{"action":"ON","duration_seconds":10}}--
Streamlit dashboard <--REST + JWT--> FastAPI
```


<h2 align="center">My Project</h2>

<p align="center">
    <img width="335" height="200" alt="image" src="https://github.com/user-attachments/assets/df00eb06-d78a-4e33-b3fa-50bb7f1a537d" />
</p>

 
1. **Sense:** capacitive soil-moisture sensor, DHT22 and a rain sensor, sampled by the ESP32 and posted every 30 seconds. Rain is sampled every second and an early post is sent when it starts.
2. **Decide:** water only if soil moisture is below 35%, the rain sensor is dry, and the 24-hour forecast shows no more than 50% chance of rain. Every decision is stored with its reason, including the forecast percentage.
3. **Act:** the backend returns a pump command in the response. The firmware runs the relay and enforces its own limits (maximum run time and a cooldown). The backend also applies a cooldown between runs.
4. **Predict:** the drying rate over the last 24 hours gives an estimate of the time until the next watering.
5. **Display:** live readings, weather, pump status, last decision, analytics and an admin view.
A manual **Water now** button on the dashboard queues a command that is delivered on the device's next check-in (up to 30 seconds), subject to the cooldown.
 
## Features
 
- Real-time soil moisture, temperature, humidity and rain monitoring
- Weather-aware automatic irrigation (OpenWeather forecast, cached for 10 minutes)
- Backend-issued pump commands with cooldown and device-side safety limits
- Predicted time until next watering from the soil drying rate
- Multi-plant support, JWT login, and role-based admin pages
- Device authentication with an `X-Device-Key` header
- Dashboard, sensor status, and analytics built from real stored data
- ESP32 simulator for testing without hardware
## Technology stack
 
| Layer | Technology |
|---|---|
| Firmware | ESP32, Arduino C++, DHT22, capacitive soil sensor, rain sensor, relay and DC pump |
| Backend | FastAPI, Uvicorn, SQLAlchemy, SQLite, Pydantic, python-jose (JWT) |
| External API | OpenWeather (5-day / 3-hour forecast) |
| Frontend | Streamlit, Plotly, pandas, requests |
| Language | Python 3.10+ |
 
## Project structure
 
```
IOT-Based-Smart-Irrigation-System/
├── app.py                      Streamlit entry point
├── requirements.txt            Frontend dependencies
├── assets/                     Images and backgrounds
├── pages/                      Streamlit pages
│   ├── 1_Welcome.py  2_Login.py  3_Sign_Up.py  4_Create.py  5_Garden.py
│   ├── 6_Dashboard.py          Live monitoring dashboard
│   ├── 7_About.py  8_Profile.py  9_Admin.py  9_Sensors.py
│   └── 10_Settings.py  11_Analytics.py  12_Weather.py
├── florapulse-backend/
│   ├── .env.example            Copy to .env and fill in
│   ├── requirements.txt
│   ├── simulate_esp32.py       Sensor simulator
│   └── app/
│       ├── main.py             API routes
│       ├── config.py  database.py  database_models.py  models.py
│       ├── services/
│       │   ├── irrigation_engine.py   Watering rule
│       │   ├── prediction_engine.py   Drying rate and next-watering estimate
│       │   ├── weather_service.py     OpenWeather client with cache
│       │   └── pump_service.py        Pump commands, cooldown, manual queue
│       └── utils/  auth.py  validators.py
└── hardware/
    ├── florapulse_firmware.ino
    └── config.example.h        Wi-Fi, server URL, device key (copy to config.h)
```
 
## Setup
 
### Prerequisites
Python 3.10+, Git, Arduino IDE (for the firmware).
 
### 1. Backend
```bash
cd florapulse-backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then set the values below
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
 
`.env` values:
```
OPENWEATHER_API_KEY=your_openweather_key
DEVICE_API_KEY=a-long-random-string
```
Generate a device key with `python3 -c "import secrets; print(secrets.token_hex(16))"`. On first start the backend creates the database and seeds an admin account, a demo account, a demo plant and the sensor `ESP32_DEMO_001`. Change the seeded passwords before exposing the server beyond your own machine.
 
API docs: http://localhost:8000/docs
 
### 2. Frontend
```bash
# from the project root
python -m venv venv-frontend && source venv-frontend/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Open http://localhost:8501 and log in with the seeded demo account.
 
### 3. Sensor data: simulator or real device
 
**Simulator** (no hardware needed), from `florapulse-backend`:
```bash
python simulate_esp32.py                         # the demo sensor
python simulate_esp32.py ESP32_DEMO_001 MY_ID_2  # several sensors
```
 
**ESP32:**
1. Install the ESP32 board package and the libraries *DHT sensor library*, *Adafruit Unified Sensor* and *ArduinoJson* (v7).
2. Copy `config.example.h` to `config.h` and set your Wi-Fi, your computer's LAN IP in the server URL, and the same device key as in `.env`. Do not commit `config.h`.
3. Calibrate the soil sensor: record the raw reading in open air (dry) and in water (wet) and set them in the firmware.
4. The computer and the ESP32 must be on the same network. Phone hotspots work, but the ESP32 needs a 2.4 GHz network.
5. The sensor ID in the firmware must match the sensor ID entered when adding the plant.
Do not run the simulator and the real device for the same sensor ID at the same time.
 
## API overview
 
| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Plants | `POST /api/plants/create`, `GET /api/plants/my-plants`, `GET /api/plants/{id}` |
| Sensors | `GET /api/sensors/my-sensors`, `POST /api/sensors/register`, `GET /api/sensors/{sensor_id}/status` |
| Sensor data | `POST /api/sensor-data/upload` (device key), `GET /api/sensor-data/history` |
| Prediction | `GET /api/plants/{id}/depletion-rate`, `GET /api/plants/{id}/next-watering-prediction` |
| Pump | `POST /api/plants/{id}/water-now`, `GET /api/plants/{id}/pump-status` |
| Decisions | `GET /api/plants/{id}/latest-decision`, `GET /api/plants/{id}/activity` |
| Weather | `GET /api/weather/current` |
| Other | `POST /api/irrigation/decide`, `GET /api/dashboard/live`, `GET /health` |
| Admin | `GET /api/admin/users`, `/plants`, `/sensors`, `/readings` |
 
Upload request body:
```json
{"sensor_id": "ESP32_DEMO_001", "moisture": 42.5, "temperature": 27.1,
 "humidity": 61.0, "rain_detected": false}
```
Response includes `decision` and `pump: {action, duration_seconds}`.
 
## Notes and limitations
 
- Readings are stored in local time and pump events in UTC.
- The pending "Water now" queue is held in memory and is cleared when the backend restarts.
- Pump runtime is commanded by the backend, but the backend cannot confirm the relay actually ran.
- Prediction accuracy has not been formally measured. The drying-rate method discards rates above 10% per hour as outliers.
- The Water vs. Energy and Cost Analysis charts on the Analytics page use sample data and are labelled as such, because the system has no flow or energy meter.
- Settings thresholds are saved per user but do not yet change the backend, which uses a fixed 35% threshold.
- Plant photos are accepted by the form but not yet stored.
- Language and time zone settings are stored but not applied.
- SQLite and a single backend process are suited to a demo or small deployment. Passwords use salted SHA-256; bcrypt or argon2 would be preferable beyond a college project.
- Do not commit `.env`, `*.db`, `settings_*.json` or `config.h`.
## Future work
 
- Persist the manual-command queue, and report relay state back from the device
- Make thresholds configurable per plant from the dashboard
- Store plant photos
- Measure prediction accuracy over repeated dry-down cycles
- Per-device keys, HTTPS and bcrypt for deployment
- Multi-zone irrigation and more sensor types
## Team
 
| Name | Contribution |
|---|---|
| **Isheka** | Backend (API, database, irrigation and prediction logic, weather integration, pump commands) and hardware (ESP32 firmware and integration) |
| **Shreeya** | Frontend (Streamlit pages, UI design and styling) |
| **Pranjali** | Frontend and hardware (sensor wiring and assembly) |
 
## License
 
Educational project: Usha Mittal Institute of Technology, SNDT Women's University, Mumbai.
 
