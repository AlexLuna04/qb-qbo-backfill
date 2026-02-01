import requests
import json
import time
from datetime import datetime, timedelta, timezone
from tenacity import retry, wait_exponential, stop_after_attempt
from sqlalchemy import create_engine, text

QBO_BASE_URL = "https://sandbox-quickbooks.api.intuit.com"

def refresh_access_token(client_id, client_secret, refresh_token):
    url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    response = requests.post(
        url,
        auth=(client_id, client_secret),
        headers={"Accept": "application/json"},
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
    )
    response.raise_for_status()
    return response.json()["access_token"]


@retry(wait=wait_exponential(multiplier=1, min=4, max=60),
       stop=stop_after_attempt(5))
def qbo_query(entity, realm_id, token, start_position):
    url = f"{QBO_BASE_URL}/v3/company/{realm_id}/query"
    query = f"SELECT * FROM {entity} STARTPOSITION {start_position} MAXRESULTS 1000"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/text"
    }

    response = requests.post(url, headers=headers, data=query)
    if response.status_code == 429:
        raise Exception("Rate limit alcanzado")
    response.raise_for_status()
    return response.json()


def upsert_raw(engine, table, records, meta):
    with engine.begin() as conn:
        for r in records:
            stmt = text(f"""
                INSERT INTO raw.{table} (id, payload, ingested_at_utc,
                    extract_window_start_utc, extract_window_end_utc,
                    page_number, page_size, request_payload)
                VALUES (
                    :id, :payload, :ingested_at,
                    :w_start, :w_end,
                    :page_number, :page_size, :request_payload
                )
                ON CONFLICT (id) DO UPDATE
                SET payload = EXCLUDED.payload,
                    ingested_at_utc = EXCLUDED.ingested_at_utc
            """)
            conn.execute(stmt, {
                "id": r["Id"],
                "payload": json.dumps(r),
                "ingested_at": meta["ingested_at"],
                "w_start": meta["w_start"],
                "w_end": meta["w_end"],
                "page_number": meta["page_number"],
                "page_size": meta["page_size"],
                "request_payload": meta["request_payload"]
            })
