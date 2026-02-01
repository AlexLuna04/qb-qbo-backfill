# QuickBooks Backfill Pipelines – Mage AI + PostgreSQL

## 1. Descripción del proyecto

Este proyecto implementa pipelines de **backfill histórico** desde **QuickBooks Online (QBO)** hacia **PostgreSQL**, utilizando **Mage AI** como orquestador.

El objetivo es:
- Extraer datos históricos desde QBO
- Procesarlos de forma segmentada por ventanas de tiempo
- Persistirlos en una **capa raw** en Postgres
- Garantizar **idempotencia**, observabilidad y control mediante triggers one-time

Se implementan tres pipelines:
- `qb_customers_backfill`
- `qb_items_backfill`
- `qb_invoices_backfill`

---

## 2. Arquitectura

QuickBooks Online (API)
        |
        | OAuth 2.0
        v
Mage AI (Docker)
        |
        | SQLAlchemy
        v
PostgreSQL (raw schema)

Componentes:
- Mage AI: orquestación, triggers, secrets, observabilidad
- PostgreSQL: almacenamiento de la capa raw
- Docker Compose: contenedores

## 3. Pasos para levantar el proyecto

# 3.1 Requisitos

- Docker
- Docker Compose
- Git

# 3.2 Clonar el repositorio

git clone <url_del_repo>
cd qb-backfill

# 3.3 Levantar contenedores

docker compose up -d

Servicios levantados:
- Mage AI → http://localhost:6789
- PostgreSQL → puerto 5432
Mage y Postgres se comunican por nombre de servicio, no por localhost.

## 4. Gestión de secretos
Todos los valores sensibles se almacenan en Mage Secrets.

# 4.1 Secretos de QuickBooks
- QBO_CLIENT_ID:        Identificación OAuth
- QBO_CLIENT_SECRET:    Secreto OAuth
- QBO_REFRESH_TOKEN:    Renovación de access token
- QBO_REALM_ID:     	Identificador de la compañía
- QBO_ENV:          	Entorno (sandbox)

# 4.2 Secretos de PostgreSQL
- PG_HOST:      Nombre del servicio Postgres
- PG_PORT:  	Puerto
- PG_DB:    	Base de datos
- PG_USER:  	Usuario
- PG_PASSWORD:  Contraseña

# 4.3 Rotación y responsables
- Rotación: manual, al expirar tokens o por política de seguridad
- Responsable: equipo de Data / Analytics
No se almacenan secretos en el repositorio ni en archivos .env

## 5. Pipelines de backfill

# 5.1 Pipelines implementados
- qb_customers_backfill
- qb_items_backfill
- qb_invoices_backfill

# 5.2 Parámetros
Todos los pipelines reciben runtime variables desde el trigger:
- fecha_inicio: Inicio del backfill (UTC, ISO 8601)
- fecha_fin:    Fin del backfill (UTC, ISO 8601)

Ejemplo:
2023-01-01T00:00:00+00:00
2023-01-31T00:00:00+00:00

# 5.3 Segmentación (chunking)
- Segmentación diaria
- Cada ejecución procesa ventanas [día, día + 1)
- Evita timeouts y facilita reejecuciones controladas

# 5.4 Paginación y límites
- Paginación QBO: start_position (1000 registros)
- Manejo de límites mediante:
    - chunking temporal
    - refresh de access token por ventana

# 5.5 Observabilidad
Cada pipeline imprime logs estructurados:
- Inicio y fin del pipeline
- Ventanas procesadas
- Número de páginas
- Filas cargadas por ventana
- Duración por tramo

# 5.6 Runbook (reintentos)
Falla por ventana:
- Reejecutar el mismo rango de fechas
- La idempotencia evita duplicados

Falla por auth:
- Rotar refresh token en Mage Secrets
- Reejecutar pipeline

## 6. Trigger one-time

# 6.1 Configuración
- Tipo: schedule
- Frecuencia: once
- Variables:
    - fecha_inicio
    - fecha_fin

# 6.2 Zona horaria
- Mage ejecuta en UTC
- Equivalencia:
    - UTC → Guayaquil (UTC-5)

Ejemplo:
2026-02-01 18:00 UTC
2026-02-01 13:00 Guayaquil

# 6.3 Política post-ejecución

- El trigger se deshabilita manualmente luego de finalizar la ejecución
- Evita reejecuciones accidentales
- Evidencia incluida en carpeta evidencias/

## 7. Esquema raw en PostgreSQL

# 7.1 Tablas

Una tabla por entidad:
- qb_customers
- qb_items
- qb_invoices

# 7.2 Estructura de tablas
CREATE TABLE raw.qb_<entidad> (
    id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    ingested_at_utc TIMESTAMPTZ,
    extract_window_start_utc TIMESTAMPTZ,
    extract_window_end_utc TIMESTAMPTZ,
    page_number INT,
    page_size INT,
    request_payload TEXT
);

# 7.3 Idempotencia
- Upsert por id
- Reejecutar un mismo tramo no genera duplicados
- Evidencia incluida en volumetría

## 8. Validaciones y volumetría

# 8.1 Conteo de registros
SELECT COUNT(*) FROM raw.qb_customers;

# 8.2 Validación por ventana
SELECT
  extract_window_start_utc,
  COUNT(*)
FROM raw.qb_customers
GROUP BY 1
ORDER BY 1;

# 8.3 Validación de idempotencia
- Reejecutar mismo rango
- El conteo total permanece constante

## 9. Troubleshooting
Auth
- Refresh token expirado → rotar secreto

Timezones
- Todas las fechas se manejan en UTC

Paginación
- Si faltan registros → revisar start_position

Postgres
- Verificar permisos y schema raw

## 10. Checklist de aceptación

## ✅ Checklist de aceptación

- [x] Mage AI y PostgreSQL se comunican por nombre de servicio.
- [x] Todos los secretos (QBO y PostgreSQL) Mage Secrets; no hay secretos en el repo/entorno expuesto.
- [x] Pipelines qb_<entidad>_backfill acepta fecha_inicio y fecha_fin (UTC) y segmenta el rango.
- [x] Trigger one-time configurado, ejecutado y luego deshabilitado/marcado como completado
- [x] Esquema raw con tablas por entidad, payload completo y metadatos obligatorios.
- [x] Idempotencia verificada: reejecución de un tramo no genera duplicados.
- [x] Paginación y rate limits manejados y documentados.
- [x] Volumetría y validaciones mínimas registradas y archivadas como evidencia.
- [x] Runbook de reanudación y reintentos disponible y seguido.