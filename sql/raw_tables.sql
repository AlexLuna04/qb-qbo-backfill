-- =========================
-- RAW: ITEMS
-- =========================
DROP TABLE IF EXISTS raw.qb_items;

CREATE TABLE raw.qb_items (
    id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    ingested_at_utc TIMESTAMPTZ,
    extract_window_start_utc TIMESTAMPTZ,
    extract_window_end_utc TIMESTAMPTZ,
    page_number INT,
    page_size INT,
    request_payload TEXT
);

-- =========================
-- RAW: CUSTOMERS
-- =========================
DROP TABLE IF EXISTS raw.qb_customers;

CREATE TABLE raw.qb_customers (
    id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    ingested_at_utc TIMESTAMPTZ,
    extract_window_start_utc TIMESTAMPTZ,
    extract_window_end_utc TIMESTAMPTZ,
    page_number INT,
    page_size INT,
    request_payload TEXT
);

-- =========================
-- RAW: INVOICES
-- =========================
DROP TABLE IF EXISTS raw.qb_invoices;

CREATE TABLE raw.qb_invoices (
    id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    ingested_at_utc TIMESTAMPTZ,
    extract_window_start_utc TIMESTAMPTZ,
    extract_window_end_utc TIMESTAMPTZ,
    page_number INT,
    page_size INT,
    request_payload TEXT
);
