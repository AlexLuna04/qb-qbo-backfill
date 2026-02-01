from mage_ai.settings.repo import get_repo_path
from mage_ai.data_preparation.shared.secrets import get_secret_value
from datetime import datetime, timedelta, timezone
import sys
import sqlalchemy
import time

repo_path = get_repo_path()
sys.path.append(repo_path)

from qb_extract import (
    refresh_access_token,
    qbo_query,
    upsert_raw
)

@data_loader
def load_items_raw(*args, **kwargs):
    """
    Backfill histórico de Items desde QBO hacia Postgres (raw)
    Segmentado por día (chunking)
    """

    # -------------------------
    # Parámetros desde el trigger
    # -------------------------
    fecha_inicio = kwargs.get("fecha_inicio")
    fecha_fin = kwargs.get("fecha_fin")

    if not fecha_inicio or not fecha_fin:
        raise ValueError("Se requieren fecha_inicio y fecha_fin (ISO UTC)")

    fecha_inicio = datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00"))
    fecha_fin = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))

    print(f"[INIT] Backfill Items {fecha_inicio} → {fecha_fin}")

    # -------------------------
    # Secrets
    # -------------------------
    QBO_CLIENT_ID = get_secret_value('QBO_CLIENT_ID')
    QBO_CLIENT_SECRET = get_secret_value('QBO_CLIENT_SECRET')
    QBO_REFRESH_TOKEN = get_secret_value('QBO_REFRESH_TOKEN')
    QBO_REALM_ID = get_secret_value('QBO_REALM_ID')

    PG_HOST = get_secret_value('PG_HOST')
    PG_PORT = get_secret_value('PG_PORT')
    PG_DB = get_secret_value('PG_DB')
    PG_USER = get_secret_value('PG_USER')
    PG_PASSWORD = get_secret_value('PG_PASSWORD')

    # -------------------------
    # Postgres
    # -------------------------
    engine = sqlalchemy.create_engine(
        f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    )

    current_date = fecha_inicio
    total_rows_global = 0

    # -------------------------
    # Chunking diario
    # -------------------------
    while current_date < fecha_fin:
        window_start = current_date
        window_end = current_date + timedelta(days=1)

        print(f"[WINDOW] Processing {window_start} → {window_end}")

        # OAuth por tramo
        access_token = refresh_access_token(
            QBO_CLIENT_ID,
            QBO_CLIENT_SECRET,
            QBO_REFRESH_TOKEN
        )

        print("[AUTH] Access token refreshed")

        start_position = 1
        page_number = 1
        rows_window = 0
        start_time = time.time()

        while True:
            response = qbo_query(
                entity="Item",
                realm_id=QBO_REALM_ID,
                token=access_token,
                start_position=start_position
            )

            records = response.get("QueryResponse", {}).get("Item", [])

            if not records:
                break

            print(f"[EXTRACT] Page={page_number} Rows={len(records)}")

            upsert_raw(
                engine=engine,
                table="qb_items",
                records=records,
                meta={
                    "ingested_at": datetime.now(timezone.utc),
                    "w_start": window_start,
                    "w_end": window_end,
                    "page_number": page_number,
                    "page_size": len(records),
                    "request_payload": f"Items {window_start} → {window_end}"
                }
            )

            rows_window += len(records)
            total_rows_global += len(records)
            start_position += 1000
            page_number += 1

            if len(records) < 1000:
                break

        duration = round(time.time() - start_time, 2)
        print(f"[DONE] Window rows={rows_window} duration={duration}s")

        current_date = window_end

    print(f"[FINISH] Total rows loaded: {total_rows_global}")

    return {
        "entity": "Item",
        "rows_loaded": total_rows_global,
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_fin": fecha_fin.isoformat()
    }
