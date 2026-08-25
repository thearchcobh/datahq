from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import requests
from icalendar import Calendar

from .database import finish_sync, get_client, set_sync_state, start_sync, utc_now_iso

SOURCE = "cruises"
FEED_URL = "https://raw.githubusercontent.com/thearchcobh/cruiseschedule/main/all-ports.ics"
DUBLIN = ZoneInfo("Europe/Dublin")


def _as_aware_datetime(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=DUBLIN)
        return value
    return datetime.combine(value, time.min, tzinfo=DUBLIN)


def _description_line(description: str, prefix: str) -> str:
    for line in description.splitlines():
        line = line.strip()
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _parse_component(component) -> dict | None:
    uid = str(component.get("UID") or "").strip()
    if not uid:
        return None

    try:
        arrival = _as_aware_datetime(component.decoded("DTSTART"))
        departure = _as_aware_datetime(component.decoded("DTEND"))
    except Exception:
        return None

    description = str(component.get("DESCRIPTION") or "")
    location = str(component.get("LOCATION") or "").strip()
    summary = str(component.get("SUMMARY") or "").strip()

    ship_line = _description_line(description, "🛳")
    vessel = ship_line
    cruise_line = ""
    if "," in ship_line:
        vessel, cruise_line = [part.strip() for part in ship_line.split(",", 1)]

    if not vessel:
        vessel = re.sub(r"^🚢\s*", "", summary).split(" — ", 1)[0].strip()

    pax_text = _description_line(description, "👥")
    pax_digits = re.sub(r"[^0-9]", "", pax_text)
    passengers = int(pax_digits) if pax_digits else None

    marine_traffic_url = _description_line(description, "🔗")
    imo_match = re.search(r"imo[:/]?(\d{7})", marine_traffic_url, flags=re.IGNORECASE)
    imo = imo_match.group(1) if imo_match else None

    return {
        "uid": uid,
        "vessel": vessel or "Unknown",
        "cruise_line": cruise_line or None,
        "imo": imo,
        "port": location or None,
        "arrival": arrival.astimezone(timezone.utc).isoformat(),
        "departure": departure.astimezone(timezone.utc).isoformat(),
        "passengers": passengers,
        "marine_traffic_url": marine_traffic_url or None,
        "source": "port_of_cork",
        "source_feed_url": FEED_URL,
        "raw_description": description,
    }


def _parse_feed(payload: bytes) -> list[dict]:
    if b"BEGIN:VCALENDAR" not in payload or b"END:VCALENDAR" not in payload:
        raise RuntimeError("Cruise feed is not a complete VCALENDAR")

    calendar = Calendar.from_ical(payload)
    rows: list[dict] = []
    seen: set[str] = set()

    for component in calendar.walk():
        if component.name != "VEVENT":
            continue
        row = _parse_component(component)
        if not row or row["uid"] in seen:
            continue
        seen.add(row["uid"])
        rows.append(row)

    if not rows:
        raise RuntimeError("Cruise feed contained zero valid calls")
    return rows


def sync_cruises() -> None:
    run_id = start_sync(SOURCE, {"feed_url": FEED_URL})
    records_read = 0
    records_written = 0

    try:
        response = requests.get(
            FEED_URL,
            timeout=30,
            headers={"User-Agent": "thearchcobh-datahq/1.0"},
        )
        response.raise_for_status()
        rows = _parse_feed(response.content)
        records_read = len(rows)

        client = get_client()
        now = utc_now_iso()

        # Keep every historical call. For future/current rows, absence from the
        # latest feed means "not active in the latest published schedule", not deletion.
        client.table("cruise_calls").update(
            {"active_in_latest_feed": False, "synced_at": now}
        ).eq("source", "port_of_cork").gte("departure", now).execute()

        for row in rows:
            row["last_seen_at"] = now
            row["synced_at"] = now
            row["active_in_latest_feed"] = True

        for start in range(0, len(rows), 200):
            batch = rows[start : start + 200]
            client.table("cruise_calls").upsert(batch, on_conflict="uid").execute()
            records_written += len(batch)

        latest_arrival = max(row["arrival"] for row in rows)
        set_sync_state(SOURCE, last_cursor=latest_arrival)
        finish_sync(
            run_id,
            status="success",
            records_read=records_read,
            records_written=records_written,
        )
        print(f"Cruise sync complete: {records_written} calls")

    except Exception as exc:
        finish_sync(
            run_id,
            status="failed",
            records_read=records_read,
            records_written=records_written,
            error_message=str(exc)[:2000],
        )
        raise
