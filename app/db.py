import json
import os
from pathlib import Path

from dotenv import load_dotenv
import requests
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_FILE = DATA_DIR / "devotional_store.json"
DATA_DIR.mkdir(exist_ok=True)


def _read_local_store():
    if not DATA_FILE.exists():
        return {"journal_entries": [], "prayer_requests": [], "devotionals": []}
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if "devotionals" not in data:
            data["devotionals"] = []
        return data
    except json.JSONDecodeError:
        return {"journal_entries": [], "prayer_requests": [], "devotionals": []}


def _write_local_store(store):
    DATA_FILE.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _is_real_supabase_config() -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False

    url = SUPABASE_URL.lower()
    key = SUPABASE_KEY.lower()

    if "your-project.supabase.co" in url:
        return False
    if "your-anon" in key or "your-" in key or "change-me" in key:
        return False

    return True


def _get_client() -> Client | None:
    if not _is_real_supabase_config():
        return None

    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None


def _devotionals_rest_request(method, *, params=None, payload=None):
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/devotionals"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if method == "POST":
        headers["Prefer"] = "return=representation"

    response = requests.request(
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    return response.json() if response.content else []


def _fallback_local_entries(key, limit=None):
    data = _read_local_store().get(key, [])
    return data[-limit:] if limit else data


def get_daily_devotionals(limit=None):
    client = _get_client()
    if client is None:
        if _is_real_supabase_config():
            try:
                return _devotionals_rest_request(
                    "GET",
                    params={"select": "*", "order": "date.desc", "limit": limit or 1000},
                )
            except Exception:
                pass
        return _fallback_local_entries("devotionals", limit)

    try:
        response = client.table("devotionals").select("*").order("created_at", desc=True).limit(limit or 1000).execute()
        return response.data if response.data else []
    except Exception:
        return _fallback_local_entries("devotionals", limit)


def save_daily_devotional(title, verse, body, date):
    client = _get_client()
    payload = {"title": title, "verse": verse, "body": body, "date": date}

    if client is None:
        if _is_real_supabase_config():
            try:
                rows = _devotionals_rest_request("POST", payload=payload)
                return rows[0] if rows else payload
            except Exception:
                pass
        store = _read_local_store()
        entry = {"id": len(store["devotionals"]) + 1, "title": title, "verse": verse, "body": body, "date": date, "created_at": "now"}
        store["devotionals"].append(entry)
        _write_local_store(store)
        return entry

    try:
        response = client.table("devotionals").insert(payload).execute()
        return response.data[0] if response.data else payload
    except Exception:
        store = _read_local_store()
        entry = {"id": len(store["devotionals"]) + 1, "title": title, "verse": verse, "body": body, "date": date, "created_at": "now"}
        store["devotionals"].append(entry)
        _write_local_store(store)
        return entry


def get_journal_entries(limit=None):
    client = _get_client()
    if client is None:
        return _fallback_local_entries("journal_entries", limit)

    try:
        response = client.table("journal_entries").select("*").order("created_at", desc=True).limit(limit or 1000).execute()
        return response.data if response.data else []
    except Exception:
        return _fallback_local_entries("journal_entries", limit)


def save_journal_entry(name, reflection):
    client = _get_client()
    payload = {"name": name, "reflection": reflection}

    if client is None:
        store = _read_local_store()
        entry = {"id": len(store["journal_entries"]) + 1, "name": name, "reflection": reflection, "created_at": "now"}
        store["journal_entries"].append(entry)
        _write_local_store(store)
        return entry

    try:
        response = client.table("journal_entries").insert(payload).execute()
        return response.data[0] if response.data else payload
    except Exception:
        store = _read_local_store()
        entry = {"id": len(store["journal_entries"]) + 1, "name": name, "reflection": reflection, "created_at": "now"}
        store["journal_entries"].append(entry)
        _write_local_store(store)
        return entry


def get_prayer_requests(limit=None):
    client = _get_client()
    if client is None:
        return _fallback_local_entries("prayer_requests", limit)

    try:
        response = client.table("prayer_requests").select("*").order("created_at", desc=True).limit(limit or 1000).execute()
        return response.data if response.data else []
    except Exception:
        return _fallback_local_entries("prayer_requests", limit)


def save_prayer_request(name, request):
    client = _get_client()
    payload = {"name": name, "request": request}

    if client is None:
        store = _read_local_store()
        prayer = {"id": len(store["prayer_requests"]) + 1, "name": name, "request": request, "created_at": "now"}
        store["prayer_requests"].append(prayer)
        _write_local_store(store)
        return prayer

    try:
        response = client.table("prayer_requests").insert(payload).execute()
        return response.data[0] if response.data else payload
    except Exception:
        store = _read_local_store()
        prayer = {"id": len(store["prayer_requests"]) + 1, "name": name, "request": request, "created_at": "now"}
        store["prayer_requests"].append(prayer)
        _write_local_store(store)
        return prayer
