"""Supabase client and insert helpers."""

import math
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")


def get_client():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
    return create_client(url, key)


def _clean_float(v):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def _clean_row(d):
    return {k: _clean_float(v) for k, v in d.items()}


def get_max_date(client, table):
    """Return the latest date in a table, or None if empty."""
    result = client.table(table).select("date").order("date", desc=True).limit(1).execute()
    if result.data:
        return result.data[0]["date"]
    return None


def upsert_batch(client, table, rows, conflict_columns, batch_size=500, retries=3):
    """Batch upsert rows into a table. Returns (total, new, skipped)."""
    if not rows:
        return 0, 0, 0

    cleaned = [_clean_row(r) for r in rows]
    total = len(cleaned)
    new = 0
    for i in range(0, total, batch_size):
        batch = cleaned[i:i + batch_size]
        for attempt in range(retries):
            try:
                result = client.table(table).upsert(
                    batch, on_conflict=conflict_columns
                ).execute()
                new += len(result.data) if result.data else 0
                break
            except Exception as e:
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    print(f"    retry {attempt + 1}/{retries} in {wait}s ({e.__class__.__name__})")
                    time.sleep(wait)
                else:
                    raise

    return total, new, total - new


def log_ingestion(client, source, target_table, total, new, skipped, duration_ms):
    client.table("ingestion_log").insert({
        "source": source,
        "target_table": target_table,
        "records_total": total,
        "records_new": new,
        "records_skipped": skipped,
        "duration_ms": duration_ms,
    }).execute()


def fetch_all(client, table, columns="*", order_by="date", filters=None):
    """Fetch all rows from a table, paginating past the 1000-row default limit."""
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        query = client.table(table).select(columns).order(order_by).range(offset, offset + page_size - 1)
        if filters:
            for col, vals in filters.items():
                query = query.in_(col, vals)
        result = query.execute()
        rows = result.data or []
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
    return all_rows
