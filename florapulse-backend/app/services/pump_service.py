from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database_models import PumpEvent
from app.config import settings

# plant_id -> True when the user pressed "Water Now" and the device hasn't collected it yet
_pending_manual: dict[int, bool] = {}


def last_pump_on(db: Session, plant_id: int):
    return (db.query(PumpEvent)
              .filter(PumpEvent.plant_id == plant_id, PumpEvent.action == "ON")
              .order_by(PumpEvent.timestamp.desc()).first())


def cooldown_remaining_minutes(db: Session, plant_id: int) -> float:
    last = last_pump_on(db, plant_id)
    if not last:
        return 0.0
    elapsed = datetime.utcnow() - last.timestamp
    remaining = timedelta(minutes=settings.pump_cooldown_minutes) - elapsed
    return max(0.0, remaining.total_seconds() / 60)


def _record_on(db: Session, plant_id: int, reason: str) -> dict:
    db.add(PumpEvent(plant_id=plant_id, timestamp=datetime.utcnow(), action="ON",
                     duration_seconds=settings.pump_duration_seconds,
                     reason=reason[:100]))
    db.commit()
    return {"action": "ON", "duration_seconds": settings.pump_duration_seconds}


def queue_manual(db: Session, plant_id: int):
    """Called by Water Now. Returns (ok, message)."""
    wait = cooldown_remaining_minutes(db, plant_id)
    if wait > 0:
        return False, f"Cooldown active, try again in {wait:.0f} min"
    _pending_manual[plant_id] = True
    return True, "Command queued; delivered on next device check-in"


def command_for_upload(db: Session, plant_id: int, decision: str, reason: str) -> dict:
    """Decide what the device should do right now."""
    off = {"action": "OFF", "duration_seconds": 0}
    if cooldown_remaining_minutes(db, plant_id) > 0:
        _pending_manual.pop(plant_id, None)   # cooldown was started elsewhere; drop it
        return off
    if _pending_manual.pop(plant_id, False):
        return _record_on(db, plant_id, "Manual: Water Now")
    if decision == "WATER":
        return _record_on(db, plant_id, reason)
    return off


def pump_status(db: Session, plant_id: int) -> dict:
    last = last_pump_on(db, plant_id)
    if not last:
        return {"active": False, "last_run": None, "last_reason": None,
                "cooldown_minutes": 0, "pending_manual": _pending_manual.get(plant_id, False)}
    ends = last.timestamp + timedelta(seconds=last.duration_seconds or 0)
    return {"active": datetime.utcnow() < ends,
            "last_run": last.timestamp.isoformat() + "Z",
            "last_reason": last.reason,
            "cooldown_minutes": round(cooldown_remaining_minutes(db, plant_id)),
            "pending_manual": _pending_manual.get(plant_id, False)}