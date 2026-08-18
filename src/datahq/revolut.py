from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import requests

from .database import finish_sync, get_client, get_sync_state, set_sync_state, start_sync

BASE_URL = "https://b2b.revolut.com/api/1.0"
DEFAULT_CLIENT_ID = "spJWSodLx2C09lD6xvxMwJbkgKqpb8d5x2kC4KYORGA"
DEFAULT_ISSUER = "example.com"
INITIAL_START = datetime(2023, 1, 1, tzinfo=timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def get_private_key() -> str:
    key = os.environ.get("REVOLUT_PRIVATE_KEY")
    if not key:
        raise RuntimeError("REVOLUT_PRIVATE_KEY is not configured")
    # Supports either a real multiline GitHub secret or a value containing literal \\n.
    return key.replace("\\n", "\n")


def build_client_assertion() -> str:
    client_id = os.environ.get("REVOLUT_CLIENT_ID") or DEFAULT_CLIENT_ID
    issuer = os.environ.get("REVOLUT_ISSUER") or DEFAULT_ISSUER
    now = now_utc()
    payload = {
        "iss": issuer,
        "sub": client_id,
        "aud": "https://revolut.com",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    return jwt.encode(payload, get_private_key(), algorithm="RS256")


def get_access_token() -> str:
    refresh_token = os.environ.get("REVOLUT_REFRESH_TOKEN")
    if not refresh_token:
        raise RuntimeError("REVOLUT_REFRESH_TOKEN is not configured")

    response = requests.post(
        f"{BASE_URL}/auth/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": build_client_assertion(),
        },
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Revolut auth error {response.status_code}: {response.text}")
    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        raise RuntimeError("Revolut auth response did not contain access_token")
    return access_token


def request_json(path: str, access_token: str, *, params=None) -> Any:
    response = requests.get(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Revolut API {response.status_code} {path}: {response.text}")
    return response.json()


def upsert(table: str, rows: list[dict[str, Any]], size: int = 500) -> int:
    if not rows:
        return 0
    client = get_client()
    for i in range(0, len(rows), size):
        client.table(table).upsert(rows[i : i + size]).execute()
    return len(rows)


def sync_accounts(access_token: str) -> tuple[int, int]:
    accounts = request_json("/accounts", access_token)
    if not isinstance(accounts, list):
        raise RuntimeError("Unexpected Revolut /accounts response")

    account_rows: list[dict[str, Any]] = []
    balance_rows: list[dict[str, Any]] = []
    for account in accounts:
        account_id = account.get("id")
        if not account_id:
            continue
        account_rows.append(
            {
                "id": account_id,
                "name": account.get("name"),
                "state": account.get("state"),
                "currency": account.get("currency"),
                "balance": account.get("balance"),
                "public": account.get("public"),
                "created_at": account.get("created_at"),
                "updated_at": account.get("updated_at"),
                "raw_json": account,
            }
        )
        if account.get("balance") is not None and account.get("currency"):
            balance_rows.append(
                {
                    "account_id": account_id,
                    "balance": account.get("balance"),
                    "currency": account.get("currency"),
                    "raw_json": account,
                }
            )

    written = upsert("revolut_accounts", account_rows)
    if balance_rows:
        get_client().table("revolut_balances").insert(balance_rows).execute()
        written += len(balance_rows)
    return len(accounts), written


def sync_transactions(access_token: str) -> tuple[int, int]:
    state = get_sync_state("revolut_transactions") or {}
    last = state.get("last_synced_at")
    if last:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        start = last_dt - timedelta(days=int(os.getenv("REVOLUT_TRANSACTION_LOOKBACK_DAYS", "14")))
    else:
        initial = os.getenv("REVOLUT_INITIAL_START")
        start = datetime.fromisoformat(initial.replace("Z", "+00:00")) if initial else INITIAL_START

    page_to = now_utc()
    read = written = 0

    while True:
        transactions = request_json(
            "/transactions",
            access_token,
            params={"from": iso_utc(start), "to": iso_utc(page_to), "count": 1000},
        )
        if not isinstance(transactions, list):
            raise RuntimeError("Unexpected Revolut /transactions response")
        if not transactions:
            break

        read += len(transactions)
        transaction_rows: list[dict[str, Any]] = []
        leg_rows: list[dict[str, Any]] = []

        for transaction in transactions:
            transaction_id = transaction.get("id")
            if not transaction_id:
                continue
            merchant = transaction.get("merchant") or {}
            card = transaction.get("card") or {}
            legs = transaction.get("legs") or []
            primary_leg = legs[0] if legs else {}

            transaction_rows.append(
                {
                    "id": transaction_id,
                    "type": transaction.get("type"),
                    "state": transaction.get("state"),
                    "request_id": transaction.get("request_id"),
                    "reason_code": transaction.get("reason_code"),
                    "created_at": transaction.get("created_at"),
                    "updated_at": transaction.get("updated_at"),
                    "completed_at": transaction.get("completed_at"),
                    "scheduled_for": transaction.get("scheduled_for"),
                    "related_transaction_id": transaction.get("related_transaction_id"),
                    "reference": transaction.get("reference"),
                    "merchant_name": merchant.get("name"),
                    "merchant_city": merchant.get("city"),
                    "merchant_category_code": merchant.get("category_code"),
                    "merchant_country": merchant.get("country"),
                    "card_id": card.get("id"),
                    # Convenience fields only. Full accounting detail is in revolut_transaction_legs.
                    "amount": primary_leg.get("amount"),
                    "currency": primary_leg.get("currency"),
                    "account_id": primary_leg.get("account_id"),
                    "raw_json": transaction,
                }
            )

            for index, leg in enumerate(legs):
                leg_id = leg.get("leg_id") or f"{transaction_id}:{index}"
                leg_rows.append(
                    {
                        "id": leg_id,
                        "transaction_id": transaction_id,
                        "account_id": leg.get("account_id"),
                        "amount": leg.get("amount"),
                        "fee": leg.get("fee"),
                        "currency": leg.get("currency"),
                        "bill_amount": leg.get("bill_amount"),
                        "bill_currency": leg.get("bill_currency"),
                        "description": leg.get("description"),
                        "balance": leg.get("balance"),
                        "counterparty_json": leg.get("counterparty"),
                        "raw_json": leg,
                    }
                )

        written += upsert("revolut_transactions", transaction_rows)
        written += upsert("revolut_transaction_legs", leg_rows)

        if len(transactions) < 1000:
            break
        last_created_at = transactions[-1].get("created_at")
        if not last_created_at:
            raise RuntimeError("Revolut pagination item missing created_at")
        next_page_to = datetime.fromisoformat(last_created_at.replace("Z", "+00:00"))
        if next_page_to >= page_to:
            raise RuntimeError("Revolut transaction pagination did not move backwards")
        page_to = next_page_to

    set_sync_state("revolut_transactions")
    return read, written


def sync_revolut() -> None:
    run_id = start_sync("revolut")
    read = written = 0
    try:
        access_token = get_access_token()
        r, w = sync_accounts(access_token)
        read += r
        written += w
        r, w = sync_transactions(access_token)
        read += r
        written += w
        set_sync_state("revolut")
        finish_sync(run_id, status="success", records_read=read, records_written=written)
    except Exception as exc:
        finish_sync(
            run_id,
            status="failed",
            records_read=read,
            records_written=written,
            error_message=str(exc),
        )
        raise
