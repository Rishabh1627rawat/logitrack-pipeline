# 🚚 LogiTrack — Logistics Data Pipeline

> *87% of businesses report having the least visibility when goods are in transit.*
> *Only 6% of logistics companies achieve full operational visibility.*
> — State of Visibility Report, 2024

An end-to-end **ELT pipeline** that solves shipment visibility gaps and warehouse bottleneck detection using a modern data stack — Airflow, Azure ADLS Gen 2, Databricks, and Snowflake.

---

## 📌 Problem Statement

Large logistics companies move thousands of shipments daily across warehouses, sorting hubs, and delivery centers. But when something goes wrong — a delayed parcel, a missed SLA — **nobody knows where it happened or why.**

Two core problems this pipeline solves:

**1. Shipment Visibility Gap**
Shipment data lives in fragmented systems — carrier scanners, warehouse management systems, driver apps. When a parcel moves between hubs, it can go "dark" for 10–18 hours with zero tracking updates. Ops teams are blind until the customer complains.

**2. Warehouse Bottleneck Detection**
When a shipment is delayed, everyone blames someone else — carrier blames the hub, hub blames staffing, manager blames the carrier. Nobody has the data to prove anything. This pipeline calculates dwell time at every hub for every shipment and surfaces exactly which hub is consistently causing delays — and when.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              DATA GENERATION (Source Simulation)            │
│   shippement_orders.py — Faker-based synthetic data         │
│   Generates: shipments, scan events, hubs                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              APACHE AIRFLOW (Orchestration)                  │
│   Triggering.py — Single orchestrator DAG with 3 tasks     │
│   ├─ BashOperator: Generate raw data                        │
│   ├─ PythonOperator: Upload to ADLS                         │
│   └─ DatabricksRunNowOperator: Trigger Silver job           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           AZURE DATA LAKE STORAGE GEN 2 (Bronze)             │
│   Container: bronzeshippingdata                             │
│   Path: bronze/{YYYY-MM-DD}/                                │
│   Format: Raw CSV/JSON files (untouched)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         DATABRICKS + PYSPARK (Silver Layer)                  │
│   Notebook: Shipment_logistic.ipynb                         │
│   - Schema enforcement & cleaning                           │
│   - Deduplication                                           │
│   - Dwell time calculation per hub                          │
│   - Joins: shipments × scan_events × hubs                   │
│   Output: Parquet files → ADLS silver/shippment_delays/     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              SNOWFLAKE (Warehouse + Gold Layer)              │
│                                                             │
│  ┌────────────────────────────────────────────────┐        │
│  │ Storage Integration → External Stage           │        │
│  │ COPY INTO → shipping_logistic_silver (wide)    │        │
│  └────────────────────────────────────────────────┘        │
│                       ↓                                     │
│  Gold Layer — 6 SQL-based use cases:                       │
│  • Dark Period Detection                                    │
│  • SLA Breach Analysis                                      │
│  • Hub-wise Total Delay                                     │
│  • Worst Performing Routes                                  │
│  • Worst Performing Carriers                                │
│  • Worst Day Patterns per Hub                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 STREAMLIT DASHBOARD (Planned)                │
│  Dark periods · Hub bottleneck ranking · Carrier performance│
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | Apache Airflow |
| Source Simulation | Python, Faker, Geopy |
| Lake Storage | Azure Data Lake Storage Gen 2 |
| Silver Processing | Databricks, PySpark |
| File Format (Silver→Gold) | Apache Parquet |
| Warehouse | Snowflake (Storage Integration + External Stage) |
| Gold Layer | Snowflake SQL |
| Dashboard | Streamlit *(planned)* |
| Language | Python 3.11, SQL |

---

## 🧠 Why ELT Instead of ETL? (Key Engineering Decision)

Initially, the plan was to do all transformations in PySpark on Databricks and use Snowflake purely for storage. **I changed this approach during implementation.** Here's why:

**Heavy lifting belongs in Databricks. Business logic belongs in SQL.**

- **Bronze → Silver:** Complex joins, dwell-time calculation, scan-sequence ordering — these are **PySpark's strength**. Big data, complex transformations, parallelized.
- **Silver → Gold:** Simple aggregations (`GROUP BY hub`, `AVG(delay)`, `COUNT(delayed)`) — these are **SQL's strength**. Auto-scaling Snowflake warehouses, result caching, analyst-friendly.

**Benefits of this split:**
1. **Cost** — Snowflake auto-suspends in 60s; Databricks cluster doesn't. ~10x cheaper for aggregations.
2. **Maintainability** — Business logic changes (e.g., SLA threshold) take 2 minutes in SQL vs 30 min in PySpark.
3. **Team alignment** — Analysts can read/modify Gold SQL directly without learning PySpark.
4. **Right tool for right job** — Databricks for transformations, Snowflake for analytics.

This is the **modern ELT pattern** used at Netflix, Airbnb, and most data-driven companies in 2024–2026.

---

## 📊 What This Pipeline Detects

### 1. Dark Period Detection
```
Shipment SHP-001 journey:

09:00 AM → Picked up — Jodhpur          ✅
12:00 PM → Arrived   — Jaipur Hub       ✅
02:00 PM → Departed  — Jaipur Hub       ✅

[  NO SCAN FOR 14 HOURS  ❌ ]

04:00 AM → Arrived   — Nagpur Hub       🚨 DARK PERIOD FLAGGED
```
`Dark_Period_detection.sql` flags gaps between consecutive scans beyond expected transit windows.

### 2. Warehouse Bottleneck Detection
```
Hub              Avg Dwell   Expected   Delay   Bottleneck Score
─────────────────────────────────────────────────────────────────
Nagpur Sorting   16.0 hrs    2 hrs      14 hrs  1,246  ← #1
Mumbai Gateway    4.2 hrs    3 hrs       1 hr     470
Delhi Sorting     1.5 hrs    2 hrs       0 hrs      0  ← healthy
```
`Total_Time_delay_at_each_hub.sql` ranks hubs by dwell-time delay.

### 3. SLA Breach Analysis
`Sla_Breech.sql` flags shipments that exceeded their distance-based SLA.

### 4. Worst Carrier / Route / Day Patterns
- `Worst_Carrier.sql` — carrier-wise delay scoring
- `WorstRoute.sql` — origin-destination pair analysis
- `Worst_Day_each_hub.sql` — day-of-week patterns per hub

---

## 📁 Project Structure

```
logitrack-pipeline/
│
├── bronze/
│   └── shippement_orders.py            # Faker-based data generator (source simulation)
│
├── Dags/
│   └── Triggering.py                   # Airflow orchestrator DAG
│                                       # Tasks: generate → upload → trigger Databricks
│
├── silver/
│   └── Shipment_logistic.ipynb         # Databricks PySpark notebook
│                                       # Cleaning, dwell-time calc, joins
│
├── Gold/                               # Snowflake SQL — business use cases
│   ├── Gold_Layer.sql                  # Main aggregation table
│   ├── Dark_Period_detection.sql       # Dark period flagging
│   ├── Sla_Breech.sql                  # SLA breach detection
│   ├── Total_Time_delay_at_each_hub.sql # Hub bottleneck ranking
│   ├── WorstRoute.sql                  # Route performance
│   ├── Worst_Carrier.sql               # Carrier performance
│   └── Worst_Day_each_hub.sql          # Day-pattern analysis
│
├── warehouse/                          # Snowflake setup (TO ADD)
│   └── snowflake_setup.sql             # DDL: database, schema, integration, stage, table
│
├── dashboard/                          # Streamlit dashboard (TO BUILD)
│   └── app.py
│
├── .gitignore
├── LICENSE
├── requirements.txt                    # TO ADD
└── README.md
```

---

## ❄️ Snowflake Setup

The Gold layer runs entirely in Snowflake using a **Storage Integration → External Stage → COPY INTO** pattern. This avoids credential hardcoding and uses Snowflake's native ADLS connector.

### Setup Flow

```sql
-- 1. Database & Schema
CREATE DATABASE shipping_logistic;
CREATE SCHEMA shipping_logistic.shipping_gold_schema;

-- 2. Storage Integration (secure Azure AD-based connection)
CREATE STORAGE INTEGRATION azure_adls_silver
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'AZURE'
  AZURE_TENANT_ID = '<tenant-id>'
  ENABLED = TRUE
  STORAGE_ALLOWED_LOCATIONS = ('azure://shippingdata.blob.core.windows.net/silvershippingdata/silver/shippment_delays');

-- 3. File Format
CREATE FILE FORMAT shipping_gold_layer TYPE = PARQUET;

-- 4. External Stage
CREATE STAGE azure_silver_stage
  URL = 'azure://shippingdata.blob.core.windows.net/silvershippingdata/silver/shippment_delays/'
  STORAGE_INTEGRATION = azure_adls_silver
  FILE_FORMAT = shipping_gold_layer;

-- 5. Load Silver data into Snowflake
COPY INTO shipping_logistic.shipping_gold_schema.shipping_logistic_silver
FROM @azure_silver_stage
PATTERN = '.*part-.*\.parquet'
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;

-- 6. Run Gold layer SQL queries on this table
```

Full DDL is available in `warehouse/snowflake_setup.sql`.

---

## 🗺️ Data Model

### Synthetic Data — What Gets Generated

**Shipment Master** — booking information
```
shipment_id · order_id · customer_id · carrier_name
origin_hub · destination_hub · distance_km · zone
shipment_type · weight_kg · booking_timestamp
sla_hours · expected_delivery_ts
```

**Checkpoint Scan Events** — tracking events
```
event_id · shipment_id · hub_name · scan_type
scan_timestamp · scan_status · delay_profile
```

**Hub Master** — reference data
```
hub_id · hub_name · city · region · hub_type
expected_dwell_hrs · max_capacity · operating_shift
```

### Distance-Based SLA System
```
Local   (0–50 km)    → Express: 12hrs  Standard: 24hrs  Economy: 48hrs
Zone A  (50–300 km)  → Express: 24hrs  Standard: 48hrs  Economy: 72hrs
Zone B  (300–800 km) → Express: 36hrs  Standard: 72hrs  Economy: 96hrs
Zone C  (800–1500km) → Express: 48hrs  Standard: 96hrs  Economy: 120hrs
Zone D  (1500km+)    → Express: 72hrs  Standard: 120hrs Economy: 168hrs
```
SLA is calculated using `geopy` geodesic distance — not hardcoded.

---

## 🧠 Other Engineering Decisions

**Why medallion architecture?**
Bronze keeps raw data untouched for reprocessing. Silver has clean, joined data. Gold has business-ready aggregations. Each layer has a clear purpose — debugging is easy.

**Why dwell time for bottleneck detection instead of GPS?**
Real logistics companies track parcels via barcode/RFID scans at hubs — not continuous GPS. Dwell time (arrived_at vs departed_at) is what ops teams actually monitor. This is the same approach used by DHL and FedEx internally.

**Why distance-based SLA instead of fixed SLA?**
Delhi → Faridabad (25 km) and Delhi → Mumbai (1,145 km) cannot have the same SLA. Geopy calculates aerial distance which is multiplied by 1.3 for road distance approximation — matching real courier zone systems.

**Why Snowflake Storage Integration over hardcoded credentials?**
Storage Integration uses Azure AD-based authentication — no SAS tokens or keys in code. This is the production-recommended way to connect Snowflake with Azure.

**Why Parquet between Silver and Gold?**
Columnar format, compressed, schema-aware. Snowflake's `COPY INTO` with `MATCH_BY_COLUMN_NAME` reads Parquet natively and handles schema evolution gracefully.

---

## 🚦 Project Status

✅ Synthetic data generator with distance-based SLA (Faker + Geopy)

✅ Hub master — 17 hubs across 5 regions

✅ Airflow DAG with 3 tasks (generate → upload → trigger Databricks)

✅ Bronze layer — raw landing in ADLS Gen 2

✅ Silver transformation — PySpark notebook with dwell time + joins

✅ Snowflake Storage Integration + External Stage setup

✅ Silver → Snowflake load via COPY INTO (Parquet)

✅ Gold layer — 6 SQL-based use case queries

✅ DAG extension to trigger Snowflake load + Gold queries

✅ Power BI Dashboard



<img width="979" height="520" alt="Hub" src="https://github.com/user-attachments/assets/2a351768-9c0e-4c1f-aae0-03be334f15ff" />




<img width="1012" height="509" alt="HUb 2" src="https://github.com/user-attachments/assets/6c516b66-60de-4ad7-9bbd-26431625b106" />





 <img width="980" height="518" alt="Hub 3" src="https://github.com/user-attachments/assets/4dc3de5c-71ad-4c21-ad55-9ae941553fce" /> 



 

<img width="1000" height="499" alt="hub 4" src="https://github.com/user-attachments/assets/9c9c1d10-f1ff-4ae6-9e99-55b912e38415" />





---

## 🔮 Future Scope

- **Snowpipe** for auto-ingest (replace manual COPY INTO)
- **MERGE-based incremental loads** to handle duplicates
- **dbt** for Gold layer modeling, testing, and lineage
- **Real-time streaming** with Apache Kafka + Spark Streaming
- **ML-based SLA breach prediction** replacing rule-based scoring
- **Integration with real carrier APIs** (DHL Developer API)
- **Power BI dashboard** for executive reporting
- **Data quality framework** (Great Expectations)

---

## ⚙️ How to Run

### Prerequisites
- Python 3.11
- Azure subscription with ADLS Gen 2
- Databricks workspace
- Snowflake account
- Apache Airflow

### Setup

```bash
# Clone the repo
git clone https://github.com/Rishabh1627rawat/logitrack-pipeline.git
cd logitrack-pipeline

# Install dependencies
pip install -r requirements.txt

# Generate synthetic data (manual run)
python bronze/shippement_orders.py
```

### Snowflake Setup
Run `warehouse/snowflake_setup.sql` in your Snowflake worksheet to create:
- Database, schema, table
- Storage integration with Azure
- External stage pointing to your ADLS silver path
- Initial COPY INTO command

### Airflow DAG
Place `Dags/Triggering.py` in your Airflow `dags/` folder. Configure connections:
- `adls_conn` — Azure Data Lake connection
- `databricks_default` — Databricks connection

---

## 📚 References

- [State of Visibility 2024 — Tive](https://www.tive.com/blog/the-state-of-visibility-2024-report-a-sneak-peek)
- [The Visibility Gap in Supply Chains — Transvirtual](https://www.transvirtual.com/us/blog/visibility-gap-in-supply-chains/)
- [Real-Time Freight Visibility Challenges — Trinetix](https://www.trinetix.com/insights/real-time-freight-visibility)
- [Snowflake Storage Integration with Azure](https://docs.snowflake.com/en/user-guide/data-load-azure-config)

---

*Built by Rishabh Rawat — Data Engineer*
