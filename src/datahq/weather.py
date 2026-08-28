from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

import requests

from .database import finish_sync, get_client, set_sync_state, start_sync, utc_now_iso

LAT = 51.85
LON = -8.30
START_DATE = date(2023, 5, 23)
FORECAST_DAYS = 15
OPEN_METEO_MAX_PAST_DAYS = 92
ERA5_SAFE_LAG_DAYS = 6
BATCH_SIZE = 500

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_FIELDS = (
    "temperature_2m,"
    "dew_point_2m,"
    "precipitation,"
    "wind_speed_10m,"
    "cloud_cover,"
    "surface_pressure"
)


def _parse_utc(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _number(value):
    if value is None:
        return None
    return float(value)


def _latest_era5_time() -> datetime | None:
    client = get_client()
    result = (
        client.table("weather_hourly")
        .select("time_utc")
        .eq("source", "era5")
        .order("time_utc", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return _parse_utc(result.data[0]["time_utc"])


def _rows_from_open_meteo(
    payload: dict,
    *,
    source: str,
    fetched_at: str,
    forecast_from: datetime | None,
) -> list[dict]:
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        raise RuntimeError("Open-Meteo response contained no hourly weather rows")

    required = (
        "temperature_2m",
        "dew_point_2m",
        "precipitation",
        "wind_speed_10m",
        "cloud_cover",
        "surface_pressure",
    )
    for field in required:
        values = hourly.get(field)
        if values is None or len(values) != len(times):
            raise RuntimeError(f"Open-Meteo response missing/invalid hourly field: {field}")

    response_lat = _number(payload.get("latitude")) or LAT
    response_lon = _number(payload.get("longitude")) or LON

    rows: list[dict] = []
    for idx, raw_time in enumerate(times):
        ts = _parse_utc(raw_time)
        rows.append(
            {
                "time_utc": ts.isoformat(),
                "temp_c": _number(hourly["temperature_2m"][idx]),
                "dewpoint_c": _number(hourly["dew_point_2m"][idx]),
                "precip_mm": _number(hourly["precipitation"][idx]),
                "wind_ms": _number(hourly["wind_speed_10m"][idx]),
                "cloud_pct": _number(hourly["cloud_cover"][idx]),
                "pressure_hpa": _number(hourly["surface_pressure"][idx]),
                "latitude": response_lat,
                "longitude": response_lon,
                "source": source,
                "is_forecast": bool(forecast_from is not None and ts >= forecast_from),
                "source_fetched_at": fetched_at,
                "updated_at": fetched_at,
            }
        )
    return rows


def _upsert_rows(rows: Iterable[dict]) -> int:
    rows = list(rows)
    if not rows:
        return 0

    client = get_client()
    written = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        client.table("weather_hourly").upsert(batch, on_conflict="time_utc").execute()
        written += len(batch)
    return written


def sync_open_meteo() -> None:
    source_name = "weather_open_meteo"
    current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    era5_max = _latest_era5_time()

    if era5_max is None:
        past_days = OPEN_METEO_MAX_PAST_DAYS
    else:
        gap_days = (current_hour.date() - era5_max.date()).days + 1
        if gap_days > OPEN_METEO_MAX_PAST_DAYS:
            raise RuntimeError(
                f"ERA5 is {gap_days} days behind; Open-Meteo forecast endpoint can bridge only "
                f"{OPEN_METEO_MAX_PAST_DAYS} days. Run the ERA5 reconciliation first."
            )
        past_days = max(1, gap_days)

    run_id = start_sync(
        source_name,
        {
            "endpoint": FORECAST_URL,
            "past_days": past_days,
            "forecast_days": FORECAST_DAYS,
            "era5_max": era5_max.isoformat() if era5_max else None,
        },
    )
    records_read = 0
    records_written = 0

    try:
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": LAT,
                "longitude": LON,
                "timezone": "UTC",
                "wind_speed_unit": "ms",
                "hourly": HOURLY_FIELDS,
                "past_days": past_days,
                "forecast_days": FORECAST_DAYS,
            },
            timeout=60,
            headers={"User-Agent": "thearchcobh-datahq/1.0"},
        )
        response.raise_for_status()
        fetched_at = utc_now_iso()
        rows = _rows_from_open_meteo(
            response.json(),
            source="open_meteo",
            fetched_at=fetched_at,
            forecast_from=current_hour,
        )
        records_read = len(rows)

        if era5_max is not None:
            rows = [row for row in rows if _parse_utc(row["time_utc"]) > era5_max]

        client = get_client()
        (
            client.table("weather_hourly")
            .delete()
            .eq("source", "open_meteo")
            .gte("time_utc", current_hour.isoformat())
            .execute()
        )

        records_written = _upsert_rows(rows)
        latest = max((_parse_utc(row["time_utc"]) for row in rows), default=current_hour)
        set_sync_state(source_name, last_cursor=latest.isoformat())
        finish_sync(
            run_id,
            status="success",
            records_read=records_read,
            records_written=records_written,
        )
        print(
            f"Open-Meteo weather sync complete: {records_written} rows "
            f"(past_days={past_days}, forecast_days={FORECAST_DAYS})"
        )
    except Exception as exc:
        finish_sync(
            run_id,
            status="failed",
            records_read=records_read,
            records_written=records_written,
            error_message=str(exc)[:2000],
        )
        raise


def _iter_date_chunks(start: date, end: date, max_days: int = 366):
    cursor = start
    while cursor <= end:
        chunk_end = min(end, cursor + timedelta(days=max_days - 1))
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


def sync_era5() -> None:
    source_name = "weather_era5"
    era5_max = _latest_era5_time()
    start = START_DATE if era5_max is None else (era5_max + timedelta(hours=1)).date()
    end = date.today() - timedelta(days=ERA5_SAFE_LAG_DAYS)

    run_id = start_sync(
        source_name,
        {
            "endpoint": ARCHIVE_URL,
            "model": "era5",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "previous_era5_max": era5_max.isoformat() if era5_max else None,
        },
    )
    records_read = 0
    records_written = 0

    try:
        if start > end:
            set_sync_state(source_name, last_cursor=era5_max.isoformat() if era5_max else None)
            finish_sync(run_id, status="success")
            print("ERA5 reconciliation already current; nothing to fetch")
            return

        fetched_at = utc_now_iso()
        for chunk_start, chunk_end in _iter_date_chunks(start, end):
            response = requests.get(
                ARCHIVE_URL,
                params={
                    "latitude": LAT,
                    "longitude": LON,
                    "start_date": chunk_start.isoformat(),
                    "end_date": chunk_end.isoformat(),
                    "models": "era5",
                    "cell_selection": "nearest",
                    "timezone": "UTC",
                    "wind_speed_unit": "ms",
                    "hourly": HOURLY_FIELDS,
                },
                timeout=90,
                headers={"User-Agent": "thearchcobh-datahq/1.0"},
            )
            response.raise_for_status()
            rows = _rows_from_open_meteo(
                response.json(),
                source="era5",
                fetched_at=fetched_at,
                forecast_from=None,
            )

            expected = ((chunk_end - chunk_start).days + 1) * 24
            if len(rows) != expected:
                raise RuntimeError(
                    f"ERA5 returned {len(rows)} hourly rows for {chunk_start}..{chunk_end}; "
                    f"expected {expected}"
                )

            records_read += len(rows)
            records_written += _upsert_rows(rows)
            print(f"ERA5 loaded {chunk_start}..{chunk_end}: {len(rows)} rows")

        final_time = datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc).replace(
            hour=23, minute=0, second=0, microsecond=0
        )
        set_sync_state(source_name, last_cursor=final_time.isoformat())
        finish_sync(
            run_id,
            status="success",
            records_read=records_read,
            records_written=records_written,
        )
        print(f"ERA5 reconciliation complete: {records_written} rows through {end}")
    except Exception as exc:
        finish_sync(
            run_id,
            status="failed",
            records_read=records_read,
            records_written=records_written,
            error_message=str(exc)[:2000],
        )
        raise


def main() -> None:
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "daily"
    if mode in {"daily", "open-meteo", "open_meteo"}:
        sync_open_meteo()
    elif mode in {"era5", "reconcile"}:
        sync_era5()
    elif mode == "both":
        sync_era5()
        sync_open_meteo()
    else:
        raise SystemExit("Usage: python -m datahq.weather [daily|era5|both]")


if __name__ == "__main__":
    main()
