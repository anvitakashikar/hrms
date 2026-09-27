import math
from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.database import get_store
from app.dependencies.auth import get_current_user, require_roles
from app.services.policy_service import get_policy_value

router = APIRouter()
store = get_store()
HR_ROLES = ("admin", "hr")
REVIEW_ROLES = ("admin", "hr", "manager")


def _org_id(user: Dict[str, Any]) -> str:
    if not user.get("org_id"):
        raise HTTPException(status_code=409, detail="Complete organization setup first")
    return user["org_id"]


def _visible_records(user: Dict[str, Any]) -> List[Dict[str, Any]]:
    records = store.list_module_records("attendance_records", _org_id(user))
    if user.get("role") in HR_ROLES or user.get("role") == "manager":
        return records
    return [item for item in records if item.get("user_id") == user["id"]]


def _active_assignment(user_id: str, org_id: str) -> Optional[Dict[str, Any]]:
    assignments = store.list_module_records("shift_assignments", org_id)
    active = [item for item in assignments if item.get("user_id") == user_id and item.get("active", True)]
    return active[-1] if active else None


def _coordinates(payload: Dict[str, Any]) -> Optional[tuple]:
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    if latitude is None and longitude is None:
        return None
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Valid latitude and longitude are required") from exc
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=422, detail="Location coordinates are out of range")
    return latitude, longitude


def _distance_meters(first: tuple, second: tuple) -> float:
    radius = 6371000
    lat1, lon1 = map(math.radians, first)
    lat2, lon2 = map(math.radians, second)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _validate_attendance_location(user: Dict[str, Any], payload: Dict[str, Any], event: str) -> Optional[Dict[str, Any]]:
    org_id = _org_id(user)
    zones = [zone for zone in store.list_module_records("geo_fence_zones", org_id) if zone.get("active", True)]
    coordinates = _coordinates(payload)
    if zones and coordinates is None:
        raise HTTPException(status_code=422, detail="Location is required for attendance at this organization")
    if coordinates is None:
        return None
    matches = []
    for zone in zones:
        center = (float(zone["latitude"]), float(zone["longitude"]))
        distance = _distance_meters(coordinates, center)
        if distance <= float(zone["radius_meters"]):
            matches.append({"zone_id": zone["id"], "distance_meters": round(distance, 1)})
    if zones and not matches:
        violation = store.create_module_record("geo_fence_violations", {
            "org_id": org_id,
            "user_id": user["id"],
            "event": event,
            "latitude": coordinates[0],
            "longitude": coordinates[1],
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        })
        store.add_audit_log(user["id"], org_id, "attendance.geofence_violation", {"record_id": violation["id"], "event": event})
        raise HTTPException(status_code=403, detail="Attendance location is outside the configured work zones")
    ping = store.create_module_record("location_ping_logs", {
        "org_id": org_id,
        "user_id": user["id"],
        "event": event,
        "latitude": coordinates[0],
        "longitude": coordinates[1],
        "matched_zones": matches,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "retention_purpose": "attendance_event",
    })
    return {"ping_id": ping["id"], "matched_zones": matches}


@router.post("/shifts", status_code=status.HTTP_201_CREATED)
def create_shift(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    name = str(payload.get("name", "")).strip()
    start_time = payload.get("start_time")
    end_time = payload.get("end_time")
    try:
        time.fromisoformat(start_time)
        time.fromisoformat(end_time)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Shift start_time and end_time must be HH:MM values") from exc
    if not name:
        raise HTTPException(status_code=422, detail="Shift name is required")
    shift = store.create_module_record("shifts", {
        "org_id": org_id,
        "name": name,
        "start_time": start_time,
        "end_time": end_time,
        "grace_minutes": max(0, int(payload.get("grace_minutes", 0))),
        "break_minutes": max(0, int(payload.get("break_minutes", 0))),
        "overtime_after_minutes": max(0, int(payload.get("overtime_after_minutes", 0))),
        "active": True,
        "created_by": current_user["id"],
    })
    store.add_audit_log(current_user["id"], org_id, "attendance.shift.created", {"record_id": shift["id"]})
    return shift


@router.get("/shifts")
def list_shifts(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return store.list_module_records("shifts", _org_id(current_user))


@router.post("/shifts/{shift_id}/assignments", status_code=status.HTTP_201_CREATED)
def assign_shift(
    shift_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    if store.get_module_record("shifts", shift_id, org_id) is None:
        raise HTTPException(status_code=404, detail="Shift not found")
    employee_id = payload.get("employee_id")
    employee = next((item for item in store.list_employees(org_id) if item["id"] == employee_id), None)
    user_id = payload.get("user_id")
    if employee:
        linked_user = store.get_user_by_email(employee["email"])
        user_id = linked_user["id"] if linked_user else user_id
    if not user_id or not store.get_user_by_id(user_id) or store.get_user_by_id(user_id).get("org_id") != org_id:
        raise HTTPException(status_code=422, detail="An employee in this organization is required")
    for assignment in store.list_module_records("shift_assignments", org_id):
        if assignment.get("user_id") == user_id and assignment.get("active", True):
            store.update_module_record("shift_assignments", assignment["id"], org_id, {"active": False})
    return store.create_module_record("shift_assignments", {
        "org_id": org_id,
        "shift_id": shift_id,
        "employee_id": employee_id,
        "user_id": user_id,
        "effective_from": payload.get("effective_from", date.today().isoformat()),
        "active": True,
    })


@router.post("/geo-fences", status_code=status.HTTP_201_CREATED)
def create_geo_fence(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES))) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
        radius = float(payload.get("radius_meters", 150))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Latitude, longitude, and radius are required") from exc
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180 and 10 <= radius <= 5000):
        raise HTTPException(status_code=422, detail="Coordinates or radius are outside allowed bounds")
    return store.create_module_record("geo_fence_zones", {
        "org_id": org_id,
        "name": str(payload.get("name", "Work site")).strip(),
        "latitude": latitude,
        "longitude": longitude,
        "radius_meters": radius,
        "active": True,
        "created_by": current_user["id"],
    })


@router.post("/check-in", status_code=status.HTTP_200_OK)
def check_in(
    payload: Dict[str, Any] = Body(default={}),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    now = datetime.now(timezone.utc)
    today_records = [item for item in store.list_module_records("attendance_records", org_id) if item.get("user_id") == current_user["id"] and item.get("work_date") == now.date().isoformat()]
    if any(item.get("check_out_at") is None for item in today_records):
        raise HTTPException(status_code=409, detail="You are already checked in")
    location = _validate_attendance_location(current_user, payload, "check_in")
    assignment = _active_assignment(current_user["id"], org_id)
    shift = store.get_module_record("shifts", assignment["shift_id"], org_id) if assignment else None
    late_minutes = 0
    if shift:
        scheduled_start = datetime.combine(now.date(), time.fromisoformat(shift["start_time"]), tzinfo=timezone.utc)
        grace_minutes = int(get_policy_value(current_user, "attendance", "grace_minutes", shift["grace_minutes"]))
        late_minutes = max(0, int((now - scheduled_start).total_seconds() // 60) - grace_minutes)
    item = store.create_module_record("attendance_records", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "employee_name": f"{current_user['first_name']} {current_user['last_name']}",
        "work_date": now.date().isoformat(),
        "check_in_at": now.isoformat(),
        "check_in_time": now.strftime("%H:%M"),
        "check_out_at": None,
        "check_out_time": None,
        "shift_id": shift["id"] if shift else None,
        "late_minutes": late_minutes,
        "early_departure_minutes": 0,
        "overtime_minutes": 0,
        "working_minutes": 0,
        "status": "late" if late_minutes else "checked_in",
        "location_event": location,
    })
    store.add_audit_log(current_user["id"], org_id, "attendance.checked_in", {"record_id": item["id"]})
    return item


@router.post("/check-out", status_code=status.HTTP_200_OK)
def check_out(
    payload: Dict[str, Any] = Body(default={}),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    now = datetime.now(timezone.utc)
    open_record = next((item for item in reversed(store.list_module_records("attendance_records", org_id)) if item.get("user_id") == current_user["id"] and item.get("work_date") == now.date().isoformat() and not item.get("check_out_at")), None)
    if open_record is None:
        raise HTTPException(status_code=409, detail="No open attendance session")
    location = _validate_attendance_location(current_user, payload, "check_out")
    checked_in = datetime.fromisoformat(open_record["check_in_at"])
    shift = store.get_module_record("shifts", open_record.get("shift_id"), org_id) if open_record.get("shift_id") else None
    break_minutes = shift.get("break_minutes", 0) if shift else 0
    working_minutes = max(0, int((now - checked_in).total_seconds() // 60) - break_minutes)
    early_departure = 0
    overtime = 0
    if shift:
        scheduled_end = datetime.combine(now.date(), time.fromisoformat(shift["end_time"]), tzinfo=timezone.utc)
        early_departure = max(0, int((scheduled_end - now).total_seconds() // 60))
        shift_minutes = (datetime.combine(now.date(), time.fromisoformat(shift["end_time"])) - datetime.combine(now.date(), time.fromisoformat(shift["start_time"]))).total_seconds() // 60
        overtime_after = int(get_policy_value(current_user, "overtime", "overtime_after_minutes", shift["overtime_after_minutes"]))
        overtime = max(0, int(working_minutes - shift_minutes - overtime_after))
    updated = store.update_module_record("attendance_records", open_record["id"], org_id, {
        "check_out_at": now.isoformat(),
        "check_out_time": now.strftime("%H:%M"),
        "working_minutes": working_minutes,
        "early_departure_minutes": early_departure,
        "overtime_minutes": overtime,
        "status": "half_day" if working_minutes < 240 else ("late" if open_record["late_minutes"] else "present"),
        "check_out_location_event": location,
    })
    store.add_audit_log(current_user["id"], org_id, "attendance.checked_out", {"record_id": updated["id"]})
    return updated


@router.post("/regularization-requests", status_code=status.HTTP_201_CREATED)
def create_regularization_request(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    work_date = payload.get("work_date")
    try:
        date.fromisoformat(work_date)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="work_date must use YYYY-MM-DD") from exc
    record_id = payload.get("attendance_record_id")
    if record_id:
        record = store.get_module_record("attendance_records", record_id, org_id)
        if record is None or record.get("user_id") != current_user["id"]:
            raise HTTPException(status_code=404, detail="Attendance record not found")
    requested_times = {}
    for field in ("requested_check_in", "requested_check_out"):
        value = payload.get(field)
        if value:
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail=f"{field} must be an ISO-8601 timestamp") from exc
            parsed = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
            requested_times[field] = parsed.isoformat()
    if not requested_times:
        raise HTTPException(status_code=422, detail="At least one corrected check-in or check-out is required")
    if not str(payload.get("reason", "")).strip():
        raise HTTPException(status_code=422, detail="A reason is required")
    if requested_times.get("requested_check_in") and requested_times.get("requested_check_out"):
        if datetime.fromisoformat(requested_times["requested_check_out"]) <= datetime.fromisoformat(requested_times["requested_check_in"]):
            raise HTTPException(status_code=422, detail="Corrected check-out must follow check-in")
    request = store.create_module_record("attendance_regularization_requests", {
        "org_id": org_id,
        "user_id": current_user["id"],
        "attendance_record_id": record_id,
        "work_date": work_date,
        "requested_check_in": requested_times.get("requested_check_in"),
        "requested_check_out": requested_times.get("requested_check_out"),
        "reason": str(payload.get("reason", "")).strip(),
        "status": "pending",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    store.add_audit_log(current_user["id"], org_id, "attendance.regularization.submitted", {"record_id": request["id"]})
    return request


@router.get("/regularization-requests")
def list_regularization_requests(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    items = store.list_module_records("attendance_regularization_requests", _org_id(current_user))
    if current_user.get("role") not in REVIEW_ROLES:
        items = [item for item in items if item.get("user_id") == current_user["id"]]
    return items


@router.patch("/regularization-requests/{request_id}/decision")
def decide_regularization_request(
    request_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_roles(*REVIEW_ROLES)),
) -> Dict[str, Any]:
    org_id = _org_id(current_user)
    decision = payload.get("status")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Status must be approved or rejected")
    item = store.get_module_record("attendance_regularization_requests", request_id, org_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Regularization request not found")
    if item["status"] != "pending":
        raise HTTPException(status_code=409, detail="Request has already been reviewed")
    updated = store.update_module_record("attendance_regularization_requests", request_id, org_id, {
        "status": decision,
        "reviewed_by": current_user["id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_comment": str(payload.get("comment", "")).strip(),
    })
    if decision == "approved" and item.get("attendance_record_id"):
        changes = {}
        for source, target in (("requested_check_in", "check_in_at"), ("requested_check_out", "check_out_at")):
            if item.get(source):
                changes[target] = item[source]
        record = store.get_module_record("attendance_records", item["attendance_record_id"], org_id)
        if record and changes:
            checked_in = changes.get("check_in_at", record.get("check_in_at"))
            checked_out = changes.get("check_out_at", record.get("check_out_at"))
            if checked_in and checked_out:
                changes["working_minutes"] = max(0, int((datetime.fromisoformat(checked_out) - datetime.fromisoformat(checked_in)).total_seconds() // 60))
            store.update_module_record("attendance_records", record["id"], org_id, changes)
    store.add_audit_log(current_user["id"], org_id, "attendance.regularization.reviewed", {"record_id": request_id, "status": decision})
    store.create_module_record("notification_logs", {
        "org_id": org_id,
        "user_id": item["user_id"],
        "event": f"attendance.regularization.{decision}",
        "title": f"Attendance request {decision}",
        "message": f"Your attendance regularization request for {item['work_date']} was {decision}.",
        "entity_type": "attendance_regularization_request",
        "entity_id": request_id,
        "read_at": None,
    })
    return updated


@router.get("/location-history")
def location_history(
    user_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    org_id = _org_id(current_user)
    target_id = user_id or current_user["id"]
    if target_id != current_user["id"] and current_user.get("role") not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Location history is restricted to the employee and HR/Admin")
    return [item for item in store.list_module_records("location_ping_logs", org_id) if item.get("user_id") == target_id]


@router.get("/summary")
def attendance_summary(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    records = _visible_records(current_user)
    today = date.today().isoformat()
    today_records = [item for item in records if item.get("work_date") == today]
    return {
        "checked_in": sum(1 for item in today_records if item.get("check_in_at") and not item.get("check_out_at")),
        "present": sum(1 for item in today_records if item.get("status") in {"present", "late", "half_day"}),
        "present_rate": round(100 * len(today_records) / max(len(store.list_employees(_org_id(current_user))), 1), 1),
        "late_arrivals": sum(1 for item in today_records if item.get("late_minutes", 0) > 0),
        "team_size": max(len(store.list_employees(_org_id(current_user))), 1),
        "working_minutes": sum(item.get("working_minutes", 0) for item in today_records),
        "overtime_minutes": sum(item.get("overtime_minutes", 0) for item in today_records),
    }


@router.get("/history")
def attendance_history(
    month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    records = _visible_records(current_user)
    if month:
        records = [item for item in records if str(item.get("work_date", "")).startswith(month)]
    return sorted(records, key=lambda item: (item.get("work_date", ""), item.get("check_in_at", "")), reverse=True)


@router.get("/reports/monthly")
def monthly_report(
    month: str = Query(..., regex=r"^\d{4}-\d{2}$"),
    current_user: Dict[str, Any] = Depends(require_roles(*HR_ROLES)),
) -> Dict[str, Any]:
    records = [item for item in store.list_module_records("attendance_records", _org_id(current_user)) if item.get("work_date", "").startswith(month)]
    return {
        "month": month,
        "record_count": len(records),
        "late_arrivals": sum(1 for item in records if item.get("late_minutes", 0) > 0),
        "absence_count": sum(1 for item in records if item.get("status") == "absent"),
        "half_days": sum(1 for item in records if item.get("status") == "half_day"),
        "working_minutes": sum(item.get("working_minutes", 0) for item in records),
        "overtime_minutes": sum(item.get("overtime_minutes", 0) for item in records),
        "items": records,
    }


@router.get("/")
def list_attendance(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _visible_records(current_user)
