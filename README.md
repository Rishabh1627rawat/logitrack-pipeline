# 🚚 LogiTrack — Logistics Data Pipeline

> *87% of businesses report having the least visibility when goods are in transit.*
> *Only 6% of logistics companies achieve full operational visibility.*
> — State of Visibility Report, 2024

This pipeline was built to solve exactly that.

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
│                     DATA SOURCES                            │
│   Shipment Master    Scan Events     Hub Master             │
│       (CSV)            (JSON)          (CSV)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              APACHE AIRFLOW (Orchestration)                  │
│   Daily Ingest DAG · Scan Events DAG · Bottleneck DAG       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           AZURE DATA LAKE STORAGE GEN 2                      │
│                  Bronze Landing Zone                         │
│  /bronze/shipment_master/year=YYYY/month=MM/day=DD/         │
│  /bronze/scan_events/year=YYYY/month=MM/day=DD/             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         DATABRICKS + PYSPARK (Transformation)               │
│                                                             │
│  Bronze → Silver → Gold  (Medallion Architecture)           │
│                                                             │
│  Bronze : Raw data landed as-is, schema enforced           │
│  Silver : Cleaned, joined, dwell time calculated           │
│  Gold   : Aggregations, bottleneck scores, dark periods    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    SNOWFLAKE                                 │
│              Data Warehouse Layer                            │
│  fact_shipments · fact_hub_performance · fact_daily_patterns│
│  dim_hubs · dim_carriers · dim_date                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 STREAMLIT DASHBOARD                          │
│  Dark periods · Hub bottleneck ranking · Carrier performance│
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | Apache Airflow |
| Storage | Azure Data Lake Storage Gen 2 |
| Processing | Databricks, PySpark |
| Table format | Delta Lake |
| Warehouse | Snowflake |
| Dashboard | Streamlit |
| Data generation | Python, Faker, Geopy |
| Language | Python 3.11 |

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
Pipeline detects gaps between consecutive scans beyond expected transit windows.

### 2. Warehouse Bottleneck Detection
```
Hub              Avg Dwell   Expected   Delay   Bottleneck Score
─────────────────────────────────────────────────────────────────
Nagpur Sorting   16.0 hrs    2 hrs      14 hrs  1,246  ← #1
Mumbai Gateway    4.2 hrs    3 hrs       1 hr     470
Delhi Sorting     1.5 hrs    2 hrs       0 hrs      0  ← healthy
```
Bottleneck Score = avg_delay_hrs × delayed_shipment_count

---

## 📁 Project Structure

```
logitrack-pipeline/
│
├── data_generator/
│   ├── synthetic_data_generator.py   # Generates realistic shipment data
│   └── hub_master.py                 # 17 Indian logistics hubs across 5 regions
│
├── dags/
│   ├── ingest_dag.py                 # Daily shipment + scan event ingestion
│   ├── bottleneck_dag.py             # Warehouse bottleneck detection trigger
│   └── dark_period_dag.py            # Dark period detection trigger
│
├── notebooks/
│   ├── bronze/
│   │   └── bronze_ingestion.py       # Raw data landing + schema validation
│   ├── silver/
│   │   └── silver_transformation.py  # Dwell time calc + joins + dedup
│   └── gold/
│       ├── gold_daily_shipments.py   # Daily shipment counts
│       ├── gold_hub_performance.py   # Hub bottleneck scores
│       ├── gold_dark_periods.py      # Dark period detection
│       └── gold_daily_patterns.py    # Day/time delay patterns
│
├── warehouse/
│   └── snowflake_schema.sql          # Star schema DDL
│
├── dashboard/
│   └── app.py                        # Streamlit ops dashboard
│
├── docs/
│   └── architecture.png
│
├── requirements.txt
└── README.md
```

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

## 🧠 Key Engineering Decisions

**Why medallion architecture?**
Bronze keeps raw data untouched for reprocessing. Silver has clean, joined data. Gold has business-ready aggregations. Each layer has a clear purpose — debugging is easy.

**Why dwell time for bottleneck detection instead of GPS?**
Real logistics companies track parcels via barcode/RFID scans at hubs — not continuous GPS. Dwell time (arrived_at vs departed_at) is what ops teams actually monitor. This is the same approach used by DHL and FedEx internally.

**Why distance-based SLA instead of fixed SLA?**
Delhi → Faridabad (25 km) and Delhi → Mumbai (1,145 km) cannot have the same SLA. Geopy calculates aerial distance which is multiplied by 1.3 for road distance approximation — matching real courier zone systems.

**Why Snowflake over Azure Synapse?**
Snowflake is multi-cloud and widely adopted across industries — skills transfer regardless of cloud provider. Better fit for a portfolio project targeting diverse employers.

---

## 📈 Gold Layer Calculations

Gold layer builds insights in this exact order:

```
Step 1 → Daily total shipments per hub
Step 2 → Daily delayed shipments + on-time count
Step 3 → Daily average delay hours
Step 4 → Hub-level dwell time vs expected dwell
Step 5 → Bottleneck score, dark periods, carrier performance
```

Each step depends on the previous — skipping any step produces incorrect aggregations.

---

## 🚦 Project Status

- [x] Synthetic data generator with distance-based SLA
- [x] Hub master — 17 hubs across 5 regions (North/South/East/West/Central)
- [ ] Airflow DAGs — in progress
- [ ] Bronze layer ingestion notebook
- [ ] Silver transformation — dwell time calculation
- [ ] Gold aggregations — bottleneck + dark period detection
- [ ] Snowflake star schema
- [ ] Streamlit dashboard

---

## 🔮 Future Scope

- Real-time streaming with Apache Kafka + Spark Streaming
- ML-based SLA breach prediction replacing rule-based scoring
- Integration with real carrier APIs (DHL Developer API)
- Power BI dashboard for executive reporting
- dbt models for Gold layer transformations

---

## ⚙️ How to Run Data Generator

```bash
# Clone the repo
git clone https://github.com/Rishabh1627rawat/logitrack-pipeline.git
cd logitrack-pipeline

# Install dependencies
pip install -r requirements.txt

# Generate synthetic data
python data_generator/synthetic_data_generator.py
```

Output files in `data/raw/`:
```
shipment_master.csv          ← 500 shipments
hub_master.csv               ← 17 hubs
checkpoint_scan_events.json  ← ~3500 events
```

---

## 📚 References

- [State of Visibility 2024 — Tive](https://www.tive.com/blog/the-state-of-visibility-2024-report-a-sneak-peek)
- [The Visibility Gap in Supply Chains — Transvirtual](https://www.transvirtual.com/us/blog/visibility-gap-in-supply-chains/)
- [Real-Time Freight Visibility Challenges — Trinetix](https://www.trinetix.com/insights/real-time-freight-visibility)

---

*Built by Rishabh Rawat — Data Engineer*
