from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from .database import finish_sync, get_client, get_sync_state, set_sync_state, start_sync

BASE_URL = "https://connect.squareup.com"
SQUARE_VERSION = os.getenv("SQUARE_API_VERSION", "2026-07-15")
DEFAULT_LOCATION_ID = "L05Y6CVDJJN86"
INITIAL_START = datetime(2023, 1, 1, tzinfo=timezone.utc)
PAYMENTS_INITIAL_START = datetime(2025, 1, 1, tzinfo=timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def request_json(method: str, path: str, token: str, *, params=None, body=None) -> dict[str, Any]:
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Square-Version": SQUARE_VERSION,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        params=params,
        json=body,
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Square API {response.status_code} {path}: {response.text}")
    return response.json()


def upsert(table: str, rows: list[dict[str, Any]], size: int = 500) -> int:
    if not rows:
        return 0
    client = get_client()
    for i in range(0, len(rows), size):
        client.table(table).upsert(rows[i : i + size]).execute()
    return len(rows)


def sync_team_members(token: str, location_id: str) -> tuple[int, int]:
    cursor = None
    read = written = 0
    while True:
        body: dict[str, Any] = {
            "query": {"filter": {"location_ids": [location_id]}},
            "limit": 200,
        }
        if cursor:
            body["cursor"] = cursor
        data = request_json("POST", "/v2/team-members/search", token, body=body)
        members = data.get("team_members") or []
        read += len(members)
        rows = [{
            "id": m.get("id"),
            "given_name": m.get("given_name"),
            "family_name": m.get("family_name"),
            "status": m.get("status"),
            "created_at": m.get("created_at"),
            "updated_at": m.get("updated_at"),
            "raw_json": m,
        } for m in members if m.get("id")]
        written += upsert("square_team_members", rows)
        cursor = data.get("cursor")
        if not cursor:
            return read, written


def sync_catalog(token: str) -> tuple[int, int]:
    cursor = None
    read = 0
    categories: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    variations: list[dict[str, Any]] = []
    while True:
        params = {"types": "CATEGORY,ITEM,ITEM_VARIATION"}
        if cursor:
            params["cursor"] = cursor
        data = request_json("GET", "/v2/catalog/list", token, params=params)
        objects = data.get("objects") or []
        read += len(objects)
        for obj in objects:
            common = {
                "id": obj.get("id"),
                "is_deleted": bool(obj.get("is_deleted")),
                "version": obj.get("version"),
                "updated_at": obj.get("updated_at"),
                "raw_json": obj,
            }
            if obj.get("type") == "CATEGORY":
                categories.append({**common, "name": (obj.get("category_data") or {}).get("name")})
            elif obj.get("type") == "ITEM":
                d = obj.get("item_data") or {}
                category_id = d.get("category_id")
                if not category_id and d.get("categories"):
                    first = d["categories"][0] or {}
                    category_id = first.get("id") or first.get("category_id")
                items.append({**common, "type": "ITEM", "name": d.get("name"), "category_id": category_id})
            elif obj.get("type") == "ITEM_VARIATION":
                d = obj.get("item_variation_data") or {}
                money = d.get("price_money") or {}
                variations.append({
                    **common,
                    "item_id": d.get("item_id"),
                    "name": d.get("name"),
                    "price_amount": money.get("amount"),
                    "price_currency": money.get("currency"),
                })
        cursor = data.get("cursor")
        if not cursor:
            break
    written = upsert("square_catalogue_categories", categories)
    written += upsert("square_catalogue_items", items)
    written += upsert("square_catalogue_variations", variations)
    return read, written


def sync_orders(token: str, location_id: str) -> tuple[int, int]:
    state = get_sync_state("square_orders") or {}
    last = state.get("last_synced_at")
    last_dt = datetime.fromisoformat(last.replace("Z", "+00:00")) if last else INITIAL_START
    start_at = last_dt - timedelta(days=int(os.getenv("SQUARE_ORDERS_LOOKBACK_DAYS", "7")))
    end_at = now_utc()
    cursor = None
    read = written = 0
    while True:
        body: dict[str, Any] = {
            "location_ids": [location_id],
            "limit": 500,
            "return_entries": False,
            "query": {
                "filter": {
                    "date_time_filter": {"updated_at": {"start_at": iso_utc(start_at), "end_at": iso_utc(end_at)}},
                    "state_filter": {"states": ["COMPLETED"]},
                },
                "sort": {"sort_field": "UPDATED_AT", "sort_order": "ASC"},
            },
        }
        if cursor:
            body["cursor"] = cursor
        data = request_json("POST", "/v2/orders/search", token, body=body)
        orders = data.get("orders") or []
        read += len(orders)
        order_rows: list[dict[str, Any]] = []
        line_rows: list[dict[str, Any]] = []
        for order in orders:
            oid = order.get("id")
            if not oid:
                continue
            total = order.get("total_money") or {}
            tax = order.get("total_tax_money") or {}
            discount = order.get("total_discount_money") or {}
            tip = order.get("total_tip_money") or {}
            service = order.get("total_service_charge_money") or {}
            source = order.get("source") or {}
            order_rows.append({
                "id": oid,
                "location_id": order.get("location_id"),
                "state": order.get("state"),
                "created_at": order.get("created_at"),
                "updated_at": order.get("updated_at"),
                "closed_at": order.get("closed_at"),
                "source_name": source.get("name"),
                "ticket_name": order.get("ticket_name"),
                "customer_id": order.get("customer_id"),
                "total_money_amount": total.get("amount"),
                "total_tax_money_amount": tax.get("amount"),
                "total_discount_money_amount": discount.get("amount"),
                "total_tip_money_amount": tip.get("amount"),
                "total_service_charge_money_amount": service.get("amount"),
                "currency": total.get("currency"),
            })
            for li in order.get("line_items") or []:
                catalog_id = li.get("catalog_object_id")
                uid = li.get("uid") or li.get("id")
                if not catalog_id or not uid:
                    continue
                base = li.get("base_price_money") or {}
                gross = li.get("gross_sales_money") or {}
                li_tax = li.get("total_tax_money") or {}
                li_discount = li.get("total_discount_money") or {}
                li_total = li.get("total_money") or {}
                line_rows.append({
                    "id": f"{oid}:{uid}",
                    "order_id": oid,
                    "uid": uid,
                    "catalog_object_id": catalog_id,
                    "item_type": "ITEM_VARIATION",
                    "item_name": li.get("name"),
                    "variation_name": li.get("variation_name"),
                    "quantity": float(li.get("quantity") or 0),
                    "base_price_money_amount": base.get("amount"),
                    "gross_sales_money_amount": gross.get("amount"),
                    "total_tax_money_amount": li_tax.get("amount"),
                    "total_discount_money_amount": li_discount.get("amount"),
                    "total_money_amount": li_total.get("amount"),
                    "currency": li_total.get("currency") or base.get("currency"),
                    "note": li.get("note"),
                })
        written += upsert("square_orders", order_rows)
        written += upsert("square_order_items", line_rows)
        cursor = data.get("cursor")
        if not cursor:
            break
    set_sync_state("square_orders")
    return read, written


def _payment_row(payment: dict[str, Any], synced_at: str) -> dict[str, Any] | None:
    payment_id = payment.get("id")
    if not payment_id:
        return None

    amount = payment.get("amount_money") or {}
    tip = payment.get("tip_money") or {}
    total = payment.get("total_money") or {}
    refunded = payment.get("refunded_money") or {}
    card_details = payment.get("card_details") or {}
    card = card_details.get("card") or {}
    application = payment.get("application_details") or {}

    fee_amount = 0
    for fee in payment.get("processing_fee") or []:
        fee_money = (fee or {}).get("amount_money") or {}
        fee_amount += int(fee_money.get("amount") or 0)

    currency = (
        total.get("currency")
        or amount.get("currency")
        or refunded.get("currency")
    )

    return {
        "id": payment_id,
        "order_id": payment.get("order_id"),
        "location_id": payment.get("location_id"),
        "team_member_id": payment.get("team_member_id"),
        "employee_id": payment.get("employee_id"),
        "status": payment.get("status"),
        "source_type": payment.get("source_type"),
        "created_at": payment.get("created_at"),
        "updated_at": payment.get("updated_at"),
        "amount_money_amount": amount.get("amount"),
        "tip_money_amount": tip.get("amount"),
        "total_money_amount": total.get("amount"),
        "refunded_money_amount": refunded.get("amount"),
        "processing_fee_amount": fee_amount,
        "currency": currency,
        "card_brand": card.get("card_brand"),
        "card_type": card.get("card_type"),
        "entry_method": card_details.get("entry_method"),
        "application_product": application.get("square_product"),
        "receipt_number": payment.get("receipt_number"),
        "raw_json": payment,
        "synced_at": synced_at,
    }


def _sync_payments_window(
    token: str,
    location_id: str,
    *,
    params: dict[str, Any],
) -> tuple[int, int]:
    cursor = None
    read = written = 0
    synced_at = iso_utc(now_utc())

    while True:
        request_params = {
            "location_id": location_id,
            "limit": 100,
            **params,
        }
        if cursor:
            request_params["cursor"] = cursor

        data = request_json("GET", "/v2/payments", token, params=request_params)
        payments = data.get("payments") or []
        read += len(payments)
        rows = []
        for payment in payments:
            row = _payment_row(payment, synced_at)
            if row:
                rows.append(row)
        written += upsert("square_payments", rows)

        cursor = data.get("cursor")
        if not cursor:
            return read, written


def sync_payments(token: str, location_id: str) -> tuple[int, int]:
    state = get_sync_state("square_payments") or {}
    last = state.get("last_synced_at")
    end_at = now_utc()
    read = written = 0

    if not last:
        # First load: retrieve the full period that overlaps our retained order history.
        # Chunking keeps API responses/pagination manageable and makes a failed first
        # backfill cheap to retry; upserts make overlapping chunk boundaries harmless.
        chunk_start = PAYMENTS_INITIAL_START
        chunk_days = int(os.getenv("SQUARE_PAYMENTS_BACKFILL_CHUNK_DAYS", "180"))
        while chunk_start < end_at:
            chunk_end = min(end_at, chunk_start + timedelta(days=chunk_days))
            r, w = _sync_payments_window(
                token,
                location_id,
                params={
                    "begin_time": iso_utc(chunk_start),
                    "end_time": iso_utc(chunk_end),
                    "sort_field": "CREATED_AT",
                    "sort_order": "ASC",
                },
            )
            read += r
            written += w
            chunk_start = chunk_end
    else:
        # Normal runs follow Payment.updated_at rather than created_at so changes to
        # older payments (notably refunds) are refreshed. A short overlap protects
        # against eventual consistency and boundary timing without a full re-download.
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        lookback_days = int(os.getenv("SQUARE_PAYMENTS_LOOKBACK_DAYS", "14"))
        start_at = last_dt - timedelta(days=lookback_days)
        r, w = _sync_payments_window(
            token,
            location_id,
            params={
                "updated_at_begin_time": iso_utc(start_at),
                "updated_at_end_time": iso_utc(end_at),
                "sort_field": "UPDATED_AT",
                "sort_order": "ASC",
            },
        )
        read += r
        written += w

    set_sync_state("square_payments")
    return read, written


def sync_timecards(token: str, location_id: str) -> tuple[int, int]:
    state = get_sync_state("square_timecards") or {}
    last = state.get("last_synced_at")
    if last:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        start = last_dt - timedelta(days=int(os.getenv("SQUARE_TIMECARDS_LOOKBACK_DAYS", "30")))
    else:
        start = INITIAL_START
    end = now_utc() + timedelta(days=1)
    cursor = None
    read = written = 0
    while True:
        body: dict[str, Any] = {
            "query": {"filter": {"location_ids": [location_id], "start": {"start_at": iso_utc(start), "end_at": iso_utc(end)}}},
            "limit": 200,
        }
        if cursor:
            body["cursor"] = cursor
        data = request_json("POST", "/v2/labor/timecards/search", token, body=body)
        cards = data.get("timecards") or []
        read += len(cards)
        rows = []
        for card in cards:
            wage = card.get("wage") or {}
            rate = wage.get("hourly_rate") or {}
            if card.get("id"):
                rows.append({
                    "id": card.get("id"),
                    "team_member_id": card.get("team_member_id"),
                    "location_id": card.get("location_id"),
                    "start_at": card.get("start_at"),
                    "end_at": card.get("end_at"),
                    "status": card.get("status"),
                    "job_id": wage.get("job_id"),
                    "job_title": wage.get("title"),
                    "hourly_rate_amount": rate.get("amount"),
                    "currency": rate.get("currency"),
                    "created_at": card.get("created_at"),
                    "updated_at": card.get("updated_at"),
                    "raw_json": card,
                })
        written += upsert("square_timecards", rows)
        cursor = data.get("cursor")
        if not cursor:
            break
    set_sync_state("square_timecards")
    return read, written


def sync_scheduled_shifts(token: str, location_id: str) -> tuple[int, int]:
    start = now_utc() - timedelta(days=7)
    end = now_utc() + timedelta(days=21)
    cursor = None
    read = written = 0
    while True:
        body: dict[str, Any] = {
            "query": {"filter": {
                "location_ids": [location_id],
                "start": {"start_at": iso_utc(start), "end_at": iso_utc(end)},
                "scheduled_shift_statuses": ["PUBLISHED"],
            }},
            "limit": 50,
        }
        if cursor:
            body["cursor"] = cursor
        data = request_json("POST", "/v2/labor/scheduled-shifts/search", token, body=body)
        shifts = data.get("scheduled_shifts") or []
        read += len(shifts)
        rows = []
        for shift in shifts:
            d = shift.get("published_shift_details") or {}
            if shift.get("id") and d:
                rows.append({
                    "id": shift.get("id"),
                    "team_member_id": d.get("team_member_id"),
                    "location_id": d.get("location_id") or location_id,
                    "job_id": d.get("job_id"),
                    "start_at": d.get("start_at"),
                    "end_at": d.get("end_at"),
                    "notes": d.get("notes"),
                    "status": "PUBLISHED",
                    "version": shift.get("version"),
                    "created_at": shift.get("created_at"),
                    "updated_at": shift.get("updated_at"),
                    "raw_json": shift,
                })
        written += upsert("square_scheduled_shifts", rows)
        cursor = data.get("cursor")
        if not cursor:
            return read, written


def sync_square() -> None:
    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("SQUARE_ACCESS_TOKEN is not configured")
    location_id = os.getenv("SQUARE_LOCATION_ID") or DEFAULT_LOCATION_ID
    run_id = start_sync("square", {"location_id": location_id})
    read = written = 0
    try:
        r, w = sync_team_members(token, location_id)
        read += r; written += w
        r, w = sync_catalog(token)
        read += r; written += w
        for fn in (sync_orders, sync_payments, sync_timecards, sync_scheduled_shifts):
            r, w = fn(token, location_id)
            read += r; written += w
        set_sync_state("square")
        finish_sync(run_id, status="success", records_read=read, records_written=written)
    except Exception as exc:
        finish_sync(run_id, status="failed", records_read=read, records_written=written, error_message=str(exc))
        raise
