from fastapi import FastAPI, HTTPException, Depends, Header, Form
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

# ============= IMPORTS: Database & Models =============
# pyrefly: ignore[missing-import]
from app.database import get_db
# pyrefly: ignore[missing-import]
from app.config import settings
# pyrefly: ignore[missing-import]
from app.database_models import (
    User, Plant, Sensor, SensorReading,
    IrrigationDecision, PumpEvent, SystemStatus
)

# ============= IMPORTS: Services & Utils =============
# pyrefly: ignore[missing-import]
from app.services.irrigation_engine import decide_irrigation
# pyrefly: ignore[missing-import]
from app.services.prediction_engine import predict_next_watering, calculate_depletion_rate
# pyrefly: ignore[missing-import]
from app.services.weather_service import fetch_weather_forecast, get_cached_forecast
# pyrefly: ignore[missing-import]
import app.services.pump_service as pump_service
# pyrefly: ignore[missing-import]
from app.utils.validators import validate_sensor_data
# pyrefly: ignore[missing-import]
from app.utils.auth import (
    hash_password, verify_password,
    create_access_token, decode_access_token, verify_device_key
)

# ============= IMPORTS: Pydantic Models =============
# pyrefly: ignore[missing-import]
from app.models import SensorDataRequest, UserCreate, UserLogin

# ============= CREATE APP =============
app = FastAPI(
    title="FloraPulse Backend",
    description="Smart plant irrigation system with sensors and predictions",
    version="1.0.0"
)


# ============= STARTUP EVENT =============
@app.on_event("startup")
def startup():
    """Initialize system on startup"""
    print("🌱 FloraPulse Backend Starting...")
    print(f"Database: {settings.database_url}")
    print("✅ System ready")


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "FloraPulse Backend"
    }


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    existing = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()

    if existing:
        raise HTTPException(400, detail="Username or email already exists")

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
        full_name=user.full_name
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "message": "User registered successfully"
    }


@app.post("/api/auth/login")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login and receive JWT access token."""
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )

    user.last_login = datetime.now()
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "is_admin": user.is_admin,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name
        }
    }


@app.get("/api/auth/me")
def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Get current authenticated user info (route handler, not a dependency)."""
    if not authorization:
        raise HTTPException(401, detail="Not authenticated")

    token = authorization[7:] if authorization.startswith("Bearer ") else authorization

    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(401, detail="Invalid token")

    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(404, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name
    }


def get_authenticated_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Dependency: return the authenticated SQLAlchemy User object."""
    if not authorization:
        raise HTTPException(401, detail="Not authenticated")

    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    token_data = decode_access_token(token)

    if not token_data:
        raise HTTPException(401, detail="Invalid token")

    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(404, detail="User not found")

    return user


# ============================================================================
# PLANT MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/plants/create")
def create_plant(
    name: str = Form(...),
    sensor_id: str = Form(...),
    description: str = Form(default=""),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Create a new plant for authenticated user."""
    if not authorization:
        raise HTTPException(401, detail="Not authenticated")

    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    token_data = decode_access_token(token)

    if not token_data:
        raise HTTPException(401, detail="Invalid token")

    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(404, detail="User not found")

    new_plant = Plant(
        user_id=user.id,
        name=name,
        description=description
    )
    db.add(new_plant)
    db.commit()
    db.refresh(new_plant)

    new_sensor = Sensor(
        plant_id=new_plant.id,
        sensor_id=sensor_id
    )
    db.add(new_sensor)
    db.commit()
    db.refresh(new_sensor)

    return {
        "id": new_plant.id,
        "name": new_plant.name,
        "sensor_id": new_sensor.sensor_id,
        "description": new_plant.description,
        "created_at": new_plant.created_at,
        "message": "Plant created successfully"
    }


@app.get("/api/plants/my-plants")
def get_user_plants(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Get all plants for authenticated user."""
    if not authorization:
        raise HTTPException(401, detail="Not authenticated")

    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(401, detail="Invalid token")

    plants = db.query(Plant).filter(Plant.user_id == token_data["user_id"]).all()

    return {
        "plants": [
            {
                "id": p.id,
                "name": p.name,
                "created_at": p.created_at,
                "sensors_count": len(p.sensors)
            }
            for p in plants
        ]
    }


@app.get("/api/plants/{plant_id}")
def get_plant_details(
    plant_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get plant details including sensors and latest readings."""
    if not authorization:
        raise HTTPException(401, detail="Not authenticated")

    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(401, detail="Invalid token")

    plant = db.query(Plant).filter(
        Plant.id == plant_id,
        Plant.user_id == token_data["user_id"]
    ).first()

    if not plant:
        raise HTTPException(404, detail="Plant not found")

    return {
        "id": plant.id,
        "name": plant.name,
        "description": plant.description,
        "created_at": plant.created_at,
        "sensors_count": len(plant.sensors)
    }


@app.get("/api/plants/{plant_id}/depletion-rate")
def get_plant_depletion_rate(plant_id: int, db: Session = Depends(get_db)):
    """Get current soil moisture depletion rate for a plant."""
    return calculate_depletion_rate(db, plant_id=plant_id, hours_lookback=24)


@app.get("/api/plants/{plant_id}/next-watering-prediction")
def get_next_watering_prediction(plant_id: int, db: Session = Depends(get_db)):
    """Predict when a plant will next require watering."""
    return predict_next_watering(db, plant_id=plant_id)


@app.post("/api/plants/{plant_id}/water-now")
def water_now(
    plant_id: int,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """Queue a manual watering request for a plant owned by the user."""
    plant = db.query(Plant).filter(
        Plant.id == plant_id,
        Plant.user_id == user.id
    ).first()

    if not plant:
        raise HTTPException(404, detail="Plant not found")

    ok, message = pump_service.queue_manual(db, plant_id)
    if not ok:
        raise HTTPException(429, detail=message)

    return {"status": "queued", "message": message}


@app.get("/api/plants/{plant_id}/pump-status")
def get_plant_pump_status(
    plant_id: int,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """Get pump status for a plant owned by the user."""
    plant = db.query(Plant).filter(
        Plant.id == plant_id,
        Plant.user_id == user.id
    ).first()

    if not plant:
        raise HTTPException(404, detail="Plant not found")

    return pump_service.pump_status(db, plant_id)


@app.get("/api/weather/current")
def weather_current(user: User = Depends(get_authenticated_user)):
    """Cached forecast, the same data the irrigation decisions use."""
    f = get_cached_forecast(settings.default_city, settings.weather_cache_minutes)
    return {"city": settings.default_city, **f}


@app.get("/api/plants/{plant_id}/latest-decision")
def latest_decision(
    plant_id: int,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """Most recent irrigation decision (with reason text) for a plant."""
    plant = db.query(Plant).filter(
        Plant.id == plant_id,
        Plant.user_id == user.id
    ).first()
    if not plant:
        raise HTTPException(404, detail="Plant not found")

    d = (
        db.query(IrrigationDecision)
        .filter(IrrigationDecision.plant_id == plant_id)
        .order_by(IrrigationDecision.timestamp.desc())
        .first()
    )
    if not d:
        return {"decision": None}

    return {
        "decision": d.decision,
        "reason": d.reason,
        "confidence": d.confidence,
        "moisture_level": d.moisture_level
    }


@app.get("/api/plants/{plant_id}/activity")
def plant_activity(
    plant_id: int,
    hours: int = 72,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """Pump runs and decision counts for a plant over the last N hours."""
    plant = db.query(Plant).filter(
        Plant.id == plant_id,
        Plant.user_id == user.id
    ).first()
    if not plant:
        raise HTTPException(404, detail="Plant not found")

    since_utc = datetime.utcnow() - timedelta(hours=hours)   # pump events are stored in UTC
    since_local = datetime.now() - timedelta(hours=hours)    # decisions use the DB's local default

    pumps = (
        db.query(PumpEvent)
        .filter(
            PumpEvent.plant_id == plant_id,
            PumpEvent.action == "ON",
            PumpEvent.timestamp >= since_utc
        )
        .order_by(PumpEvent.timestamp)
        .all()
    )
    counts = (
        db.query(IrrigationDecision.decision, func.count())
        .filter(
            IrrigationDecision.plant_id == plant_id,
            IrrigationDecision.timestamp >= since_local
        )
        .group_by(IrrigationDecision.decision)
        .all()
    )

    return {
        "pump_events": [
            {
                "timestamp": p.timestamp.isoformat() + "Z",
                "duration_seconds": p.duration_seconds,
                "reason": p.reason
            }
            for p in pumps
        ],
        "decision_counts": {d: n for d, n in counts}
    }


# ============================================================================
# SENSOR MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/sensors/my-sensors")
def get_my_sensors(authorization: str = Header(None), db: Session = Depends(get_db)):
    """
    Return all sensors belonging to the authenticated user's plants,
    each enriched with the latest sensor reading values.
    """
    if not authorization:
        raise HTTPException(401, detail="Not authenticated")

    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(401, detail="Invalid token")

    user_id = token_data["user_id"]

    user_plants = db.query(Plant).filter(Plant.user_id == user_id).all()
    plant_map = {p.id: p.name for p in user_plants}

    if not plant_map:
        return {"sensors": []}

    sensors = (
        db.query(Sensor)
        .filter(Sensor.plant_id.in_(list(plant_map.keys())))
        .all()
    )

    result = []
    for sensor in sensors:
        latest = (
            db.query(SensorReading)
            .filter(SensorReading.sensor_id == sensor.id)
            .order_by(SensorReading.timestamp.desc())
            .first()
        )
        result.append({
            "sensor_id": sensor.sensor_id,
            "plant_name": plant_map.get(sensor.plant_id, f"Plant {sensor.plant_id}"),
            "plant_id": sensor.plant_id,
            "is_connected": sensor.is_connected,
            "last_data_received": sensor.last_data_received.isoformat() if sensor.last_data_received else None,
            "latest_moisture": round(latest.moisture, 1) if latest else None,
            "latest_temperature": round(latest.temperature, 1) if latest and latest.temperature else None,
            "latest_humidity": round(latest.humidity, 1) if latest and latest.humidity else None,
            "rain_detected": latest.rain_detected if latest else False,
            "last_reading_at": latest.timestamp.isoformat() if latest else None,
        })

    return {"sensors": result}


@app.get("/api/sensors/{sensor_id}/status")
def get_sensor_status(sensor_id: str, db: Session = Depends(get_db)):
    """Get sensor connection status and latest reading."""
    sensor = db.query(Sensor).filter(Sensor.sensor_id == sensor_id).first()

    if not sensor:
        raise HTTPException(404, detail="Sensor not found")

    latest_reading = (
        db.query(SensorReading)
        .filter(SensorReading.sensor_id == sensor.id)
        .order_by(SensorReading.timestamp.desc())
        .first()
    )

    return {
        "sensor_id": sensor.sensor_id,
        "sensor_name": sensor.sensor_name,
        "plant_id": sensor.plant_id,
        "is_connected": sensor.is_connected,
        "last_data_received": sensor.last_data_received,
        "latest_moisture": latest_reading.moisture if latest_reading else None,
        "latest_temperature": latest_reading.temperature if latest_reading else None,
        "latest_timestamp": latest_reading.timestamp if latest_reading else None
    }


@app.post("/api/sensors/register")
def register_sensor(
    sensor_id: str = Form(...),
    plant_id: int = Form(...),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Register a sensor string-ID against an existing plant.
    Requires the plant to belong to the authenticated user.
    """
    if not authorization:
        raise HTTPException(401, detail="Not authenticated")

    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(401, detail="Invalid token")

    plant = db.query(Plant).filter(
        Plant.id == plant_id,
        Plant.user_id == token_data["user_id"]
    ).first()
    if not plant:
        raise HTTPException(404, detail=f"Plant {plant_id} not found or not owned by you")

    existing = db.query(Sensor).filter(Sensor.sensor_id == sensor_id).first()
    if existing:
        if existing.plant_id != plant_id:
            raise HTTPException(
                409,
                detail=f"Sensor '{sensor_id}' is already registered to another plant"
            )
        return {
            "status": "already_registered",
            "sensor_id": sensor_id,
            "plant_id": plant_id,
            "message": "Sensor already registered to this plant"
        }

    new_sensor = Sensor(
        plant_id=plant_id,
        sensor_id=sensor_id,
        sensor_name=f"Sensor {sensor_id}",
        is_connected=False,
    )
    db.add(new_sensor)
    db.commit()
    db.refresh(new_sensor)

    return {
        "status": "registered",
        "sensor_id": sensor_id,
        "plant_id": plant_id,
        "message": "Sensor registered successfully"
    }


# ============================================================================
# SENSOR DATA ENDPOINTS
# ============================================================================

@app.post(
    "/api/sensor-data/upload",
    dependencies=[Depends(verify_device_key)]
)
def upload_sensor_data(
    request: SensorDataRequest,
    db: Session = Depends(get_db)
):
    """Upload sensor data, make a weather-aware decision, and issue a pump command."""

    # 1. Validate incoming sensor data.
    is_valid, message = validate_sensor_data(
        request.moisture,
        request.temperature,
        request.humidity
    )
    if not is_valid:
        raise HTTPException(400, detail=message)

    # 2. Find the registered sensor and its plant.
    sensor = db.query(Sensor).filter(
        Sensor.sensor_id == request.sensor_id
    ).first()
    if not sensor:
        raise HTTPException(
            404,
            detail=(
                f"Sensor '{request.sensor_id}' not registered. "
                "Call POST /api/sensors/register first, "
                "or add the plant via the web app."
            )
        )

    plant_id = sensor.plant_id
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(404, detail="Associated plant not found")

    # 3. Update sensor connection status and save the reading.
    sensor.is_connected = True
    sensor.last_data_received = datetime.now()

    reading = SensorReading(
        sensor_id=sensor.id,
        moisture=request.moisture,
        temperature=request.temperature,
        humidity=request.humidity,
        rain_detected=request.rain_detected
    )

    db.add(reading)
    db.add(sensor)
    db.commit()
    db.refresh(reading)

    # 4. Retrieve the cached weather forecast.
    forecast = get_cached_forecast(
        settings.default_city,
        settings.weather_cache_minutes
    )
    rain_prob = forecast.get("rain_probability", 0)

    # 5. Make the irrigation decision using sensor and forecast data.
    result = decide_irrigation(
        request.moisture,
        request.rain_detected,
        rain_prob
    )

    reason = f"{result['reason']} [forecast rain {rain_prob:.0f}%"
    reason += "]" if forecast.get("available") else ", forecast unavailable]"

    # 6. Save the irrigation decision.
    decision = IrrigationDecision(
        plant_id=plant_id,
        moisture_level=request.moisture,
        decision=result["decision"],
        reason=reason[:500],
        confidence=result["confidence"]
    )
    db.add(decision)
    db.commit()

    # 7. Generate the pump command (the device must execute it).
    pump = pump_service.command_for_upload(
        db,
        plant_id,
        result["decision"],
        reason
    )

    return {
        "status": "success",
        "reading_id": reading.id,
        "plant_id": plant_id,
        "sensor_id": request.sensor_id,
        "decision": result["decision"],
        "confidence": result["confidence"],
        "pump": pump
    }


@app.get("/api/sensor-data/history")
def get_sensor_history(
    hours: int = 24,
    limit: int = 100,
    sensor_id: str = None,
    plant_id: int = None,
    db: Session = Depends(get_db)
):
    """Get historical sensor readings (newest first)."""
    cutoff_time = datetime.now() - timedelta(hours=hours)

    query = db.query(SensorReading).filter(
        SensorReading.timestamp >= cutoff_time
    )

    if sensor_id:
        sensor = db.query(Sensor).filter(Sensor.sensor_id == sensor_id).first()
        if sensor:
            query = query.filter(SensorReading.sensor_id == sensor.id)
    elif plant_id:
        sensors = db.query(Sensor).filter(Sensor.plant_id == plant_id).all()
        if sensors:
            sensor_ids = [s.id for s in sensors]
            query = query.filter(SensorReading.sensor_id.in_(sensor_ids))
        else:
            return {"readings": []}

    readings = query.order_by(SensorReading.timestamp.desc()).limit(limit).all()

    return {
        "readings": [
            {
                "id": r.id,
                "moisture": r.moisture,
                "temperature": r.temperature,
                "humidity": r.humidity,
                "rain_detected": r.rain_detected,
                "timestamp": r.timestamp
            }
            for r in readings
        ]
    }


# ============================================================================
# SYSTEM STATUS ENDPOINTS
# ============================================================================

@app.get("/api/status")
def get_system_status(db: Session = Depends(get_db)):
    """Get current system status."""
    latest_reading = (
        db.query(SensorReading)
        .order_by(SensorReading.timestamp.desc())
        .first()
    )

    if not latest_reading:
        raise HTTPException(404, detail="No sensor data available")

    return {
        "status": "operational",
        "last_moisture": latest_reading.moisture,
        "last_temperature": latest_reading.temperature,
        "last_humidity": latest_reading.humidity,
        "last_update": latest_reading.timestamp
    }


# ============================================================================
# IRRIGATION DECISION ENDPOINTS
# ============================================================================

@app.post("/api/irrigation/decide")
def get_irrigation_decision(
    request: SensorDataRequest,
    db: Session = Depends(get_db)
):
    """Get irrigation decision using sensor and weather data."""
    weather = fetch_weather_forecast(settings.default_city)

    result = decide_irrigation(
        request.moisture,
        request.rain_detected,
        weather["rain_probability"]
    )

    return {
        "decision": result["decision"],
        "reason": result["reason"],
        "confidence": result["confidence"],
        "forecast_rain_probability": weather["rain_probability"],
        "sensor_rain_detected": request.rain_detected,
        "current_moisture": request.moisture
    }


# ============================================================================
# PREDICTION ENDPOINTS
# ============================================================================

@app.get("/api/prediction/next-watering")
def get_prediction_by_sensor(
    sensor_id: str = None,
    current_moisture: float = None,   # kept for backward compatibility; prediction uses DB history
    db: Session = Depends(get_db)
):
    """Estimate when next watering will be needed (by sensor, or latest reading overall)."""
    if sensor_id:
        sensor = db.query(Sensor).filter(Sensor.sensor_id == sensor_id).first()
        if not sensor:
            raise HTTPException(404, detail="Sensor not found")
        plant_id = sensor.plant_id
    else:
        latest = (
            db.query(SensorReading)
            .order_by(SensorReading.timestamp.desc())
            .first()
        )
        if not latest:
            raise HTTPException(404, detail="No sensor data available")
        plant_id = latest.sensor.plant_id if latest.sensor else None

    if plant_id is None:
        raise HTTPException(404, detail="No plant data available to predict")

    return predict_next_watering(db, plant_id=plant_id)


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@app.get("/api/dashboard/live")
def get_dashboard_data(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get aggregated data for dashboard for the authenticated user."""
    if not authorization:
        raise HTTPException(401, detail="Not authenticated")

    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(401, detail="Invalid token")

    user_id = token_data["user_id"]

    user_plants = db.query(Plant).filter(Plant.user_id == user_id).all()
    if not user_plants:
        raise HTTPException(404, detail="No plants found for user")

    plant_ids = [p.id for p in user_plants]

    user_sensors = db.query(Sensor).filter(Sensor.plant_id.in_(plant_ids)).all()
    sensor_ids = [s.id for s in user_sensors]

    if not sensor_ids:
        raise HTTPException(404, detail="No sensors found for user")

    latest_reading = (
        db.query(SensorReading)
        .filter(SensorReading.sensor_id.in_(sensor_ids))
        .order_by(SensorReading.timestamp.desc())
        .first()
    )

    if not latest_reading:
        raise HTTPException(404, detail="No sensor data available for this user")

    recent = (
        db.query(SensorReading)
        .filter(SensorReading.sensor_id.in_(sensor_ids))
        .order_by(SensorReading.timestamp.desc())
        .limit(10)
        .all()
    )

    latest_dec = (
        db.query(IrrigationDecision)
        .filter(IrrigationDecision.plant_id.in_(plant_ids))
        .order_by(IrrigationDecision.timestamp.desc())
        .first()
    )

    prediction = predict_next_watering(db, plant_id=plant_ids[0])

    return {
        "latest_reading": {
            "moisture": latest_reading.moisture,
            "temperature": latest_reading.temperature,
            "humidity": latest_reading.humidity,
            "timestamp": latest_reading.timestamp
        },
        "recent_readings": [
            {
                "moisture": r.moisture,
                "temperature": r.temperature,
                "humidity": r.humidity,
                "timestamp": r.timestamp
            }
            for r in recent
        ],
        "latest_decision": {
            "decision": latest_dec.decision,
            "reason": latest_dec.reason,
            "confidence": latest_dec.confidence,
            "timestamp": latest_dec.timestamp
        } if latest_dec else None,
        "prediction": prediction
    }


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "🌱 FloraPulse Backend API",
        "docs": "http://localhost:8000/docs",
        "version": "1.0.0"
    }


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

def get_admin_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Dependency: authenticated user who must be an admin."""
    if not authorization:
        raise HTTPException(401, detail="Not authenticated")

    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(401, detail="Invalid token")

    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(404, detail="User not found")

    if not user.is_admin:
        raise HTTPException(403, detail="Not authorized. Admins only.")

    return user


@app.get("/api/admin/users")
def admin_get_users(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Admin only: get all users"""
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "created_at": u.created_at
        }
        for u in users
    ]


@app.get("/api/admin/plants")
def admin_get_plants(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Admin only: get all plants"""
    plants = db.query(Plant).all()
    return [
        {
            "id": p.id,
            "plant_name": p.name,
            "owner_username": p.owner.username if p.owner else "Unknown",
            "created_at": p.created_at
        }
        for p in plants
    ]


@app.get("/api/admin/sensors")
def admin_get_sensors(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Admin only: get all sensors"""
    sensors = db.query(Sensor).all()
    return [
        {
            "sensor_id": s.sensor_id,
            "plant_name": s.plant.name if s.plant else "Unknown",
            "owner_username": s.plant.owner.username if s.plant and s.plant.owner else "Unknown",
            "is_connected": s.is_connected,
            "last_data_received": s.last_data_received
        }
        for s in sensors
    ]


@app.get("/api/admin/readings")
def admin_get_readings(
    limit: int = 100,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin only: get recent readings"""
    readings = (
        db.query(SensorReading)
        .order_by(SensorReading.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "sensor_id": r.sensor.sensor_id if r.sensor else "Unknown",
            "plant_name": r.sensor.plant.name if r.sensor and r.sensor.plant else "Unknown",
            "moisture": r.moisture,
            "temperature": r.temperature,
            "humidity": r.humidity,
            "timestamp": r.timestamp
        }
        for r in readings
    ]