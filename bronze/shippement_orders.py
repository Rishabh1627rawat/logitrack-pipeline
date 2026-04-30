from faker import Faker
from faker.providers import BaseProvider
from datetime import timedelta, datetime
from geopy.distance import geodesic
from itertools import combinations
from collections import Counter
import random
import pandas as pd
import os


execution_date = datetime.now().strftime("%Y-%m-%d")

# ─────────────────────────────────────────────
# CITY COORDINATES — Indian logistics hubs
# ─────────────────────────────────────────────

CITY_COORDINATES = {
    # North
    "Delhi":          (28.6139, 77.2090),
    "Noida":          (28.5355, 77.3910),
    "Gurgaon":        (28.4595, 77.0266),
    "Faridabad":      (28.4089, 77.3178),
    "Ghaziabad":      (28.6692, 77.4538),
    "Ludhiana":       (30.9010, 75.8573),
    "Amritsar":       (31.6340, 74.8723),
    "Jalandhar":      (31.3260, 75.5762),
    "Chandigarh":     (30.7333, 76.7794),
    "Jaipur":         (26.9124, 75.7873),
    "Jodhpur":        (26.2389, 73.0243),
    "Udaipur":        (24.5854, 73.7125),

    # Central
    "Lucknow":        (26.8467, 80.9462),
    "Kanpur":         (26.4499, 80.3319),
    "Varanasi":       (25.3176, 82.9739),
    "Agra":           (27.1767, 78.0081),
    "Indore":         (22.7196, 75.8577),
    "Bhopal":         (23.2599, 77.4126),
    "Nagpur":         (21.1458, 79.0882),
    "Raipur":         (21.2514, 81.6296),

    # West
    "Mumbai":         (19.0760, 72.8777),
    "Pune":           (18.5204, 73.8567),
    "Nashik":         (19.9975, 73.7898),
    "Ahmedabad":      (23.0225, 72.5714),
    "Surat":          (21.1702, 72.8311),
    "Vadodara":       (22.3072, 73.1812),
    "Rajkot":         (22.3039, 70.8022),

    # East
    "Kolkata":        (22.5726, 88.3639),
    "Patna":          (25.5941, 85.1376),
    "Ranchi":         (23.3441, 85.3096),
    "Jamshedpur":     (22.8046, 86.2029),
    "Bhubaneswar":    (20.2961, 85.8245),
    "Guwahati":       (26.1445, 91.7362),

    # South
    "Bengaluru":      (12.9716, 77.5946),
    "Chennai":        (13.0827, 80.2707),
    "Hyderabad":      (17.3850, 78.4867),
    "Coimbatore":     (11.0168, 76.9558),
    "Kochi":          (9.9312,  76.2673),
    "Visakhapatnam":  (17.6868, 83.2185),
    "Madurai":        (9.9252,  78.1198),
}

# ─────────────────────────────────────────────
# DISTANCE CACHE — precompute once, O(1) lookup
# 300K shipments ke liye 300K geopy calls nahi
# Sirf 861 unique pairs precompute honge
# ─────────────────────────────────────────────

print("📍 Precomputing distance cache...")
DISTANCE_CACHE = {}
cities = list(CITY_COORDINATES.keys())

for c1, c2 in combinations(cities, 2):
    aerial = geodesic(CITY_COORDINATES[c1], CITY_COORDINATES[c2]).km
    road   = round(aerial * 1.3, 1)
    DISTANCE_CACHE[(c1, c2)] = road
    DISTANCE_CACHE[(c2, c1)] = road

print(f"✅ {len(DISTANCE_CACHE)} city pairs cached\n")


# ─────────────────────────────────────────────
# DISTANCE → ZONE → SLA MAPPING
# ─────────────────────────────────────────────

def get_zone(distance_km):
    if distance_km <= 50:
        return "Local"
    elif distance_km <= 300:
        return "Zone A"
    elif distance_km <= 800:
        return "Zone B"
    elif distance_km <= 1500:
        return "Zone C"
    else:
        return "Zone D"

def get_sla_hours(zone, shipment_type):
    base_sla = {
        "Local":  {"Express": 12,  "Standard": 24,  "Economy": 48},
        "Zone A": {"Express": 24,  "Standard": 48,  "Economy": 72},
        "Zone B": {"Express": 36,  "Standard": 72,  "Economy": 96},
        "Zone C": {"Express": 48,  "Standard": 96,  "Economy": 120},
        "Zone D": {"Express": 72,  "Standard": 120, "Economy": 168},
    }
    return base_sla[zone][shipment_type]

def calculate_distance(city1, city2):
    # O(1) cache lookup — no geopy call
    return DISTANCE_CACHE[(city1, city2)]


# ─────────────────────────────────────────────
# CUSTOM FAKER PROVIDER
# ─────────────────────────────────────────────

class LogisticsProvider(BaseProvider):

    CARRIERS = ["BlueDart", "DTDC", "DHL", "Delhivery", "Ecom Express"]

    INTERMEDIATE_HUBS = [
        "Nagpur", "Indore", "Bhopal", "Vadodara", "Nashik",
        "Lucknow", "Chandigarh", "Chennai", "Gurgaon",
        "Pune", "Agra", "Hyderabad", "Bengaluru",
        "Ahmedabad", "Kolkata", "Amritsar"
    ]

    def shipment_id(self):
        date_part = self.generator.date_time_this_year().strftime("%Y%m%d")
        return f"SHP-{date_part}-{self.random_int(10000, 99999)}"

    def order_id(self):
        return f"ORD-{self.random_int(100000, 999999)}"

    def customer_id(self):
        return f"CUST-{self.random_int(1000, 9999)}"

    def carrier_name(self):
        return self.random_element(self.CARRIERS)

    def shipment_type(self):
        return self.random_element([
            "Express", "Express",
            "Standard", "Standard", "Standard", "Standard",
            "Economy", "Economy"
        ])

    def origin_and_destination(self):
        origin      = self.random_element(cities)
        destination = self.random_element(cities)
        while destination == origin:
            destination = self.random_element(cities)
        return origin, destination

    def weight_kg(self):
        return round(random.uniform(0.1, 30.0), 2)

    def booking_timestamp(self):
        return self.generator.date_time_between(
            start_date="-30d",
            end_date="now"
        )


# ─────────────────────────────────────────────
# INITIALIZE FAKER
# ─────────────────────────────────────────────

fake = Faker("en_IN")
fake.add_provider(LogisticsProvider)


# ─────────────────────────────────────────────
# FILE 1 — SHIPMENT MASTER
# ─────────────────────────────────────────────

def generate_shipment_master(num_records=100000):
    records = []

    for _ in range(num_records):
        booking_ts   = fake.booking_timestamp()
        s_type       = fake.shipment_type()
        carrier      = fake.carrier_name()
        origin, dest = fake.origin_and_destination()

        distance_km  = calculate_distance(origin, dest)   # cache lookup
        zone         = get_zone(distance_km)
        sla_hrs      = get_sla_hours(zone, s_type)
        expected_ts  = booking_ts + timedelta(hours=sla_hrs)

        records.append({
            "shipment_id":          fake.shipment_id(),
            "order_id":             fake.order_id(),
            "customer_id":          fake.customer_id(),
            "carrier_name":         carrier,
            "shipment_type":        s_type,
            "origin_hub":           origin,
            "destination_hub":      dest,
            "distance_km":          distance_km,
            "zone":                 zone,
            "weight_kg":            fake.weight_kg(),
            "booking_timestamp":    booking_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "sla_hours":            sla_hrs,
            "expected_delivery_ts": expected_ts.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return records


# ─────────────────────────────────────────────
# FILE 2 — HUB MASTER (static)
# ─────────────────────────────────────────────

def generate_hub_master():
    return [

        # ── NORTH REGION ──────────────────────────────────────
        {
            "hub_id": "HUB001", "hub_name": "Delhi Sorting Center",
            "city": "Delhi", "region": "North", "hub_type": "SORTING",
            "expected_dwell_hrs": 2, "max_capacity": 6000, "operating_shift": "24x7"
        },
        {
            "hub_id": "HUB010", "hub_name": "Jaipur North Hub",
            "city": "Jaipur", "region": "North", "hub_type": "SORTING",
            "expected_dwell_hrs": 2, "max_capacity": 2500, "operating_shift": "24x7"
        },
        {
            "hub_id": "HUB016", "hub_name": "Chandigarh Sorting Hub",
            "city": "Chandigarh", "region": "North", "hub_type": "SORTING",
            "expected_dwell_hrs": 3, "max_capacity": 2000, "operating_shift": "24x7"
        },
        {
            "hub_id": "HUB015", "hub_name": "Amritsar Delivery Hub",
            "city": "Amritsar", "region": "North", "hub_type": "DELIVERY",
            "expected_dwell_hrs": 1, "max_capacity": 1200, "operating_shift": "Day"
        },
        {
            "hub_id": "HUB017", "hub_name": "Lucknow Distribution Hub",
            "city": "Lucknow", "region": "North", "hub_type": "SORTING",
            "expected_dwell_hrs": 2, "max_capacity": 2800, "operating_shift": "24x7"
        },

        # ── WEST REGION ───────────────────────────────────────
        {
            "hub_id": "HUB002", "hub_name": "Mumbai Gateway Hub",
            "city": "Mumbai", "region": "West", "hub_type": "SORTING",
            "expected_dwell_hrs": 3, "max_capacity": 7000, "operating_shift": "24x7"
        },
        {
            "hub_id": "HUB009", "hub_name": "Pune Delivery Center",
            "city": "Pune", "region": "West", "hub_type": "DELIVERY",
            "expected_dwell_hrs": 1, "max_capacity": 2500, "operating_shift": "Day"
        },
        {
            "hub_id": "HUB008", "hub_name": "Ahmedabad Sorting Hub",
            "city": "Ahmedabad", "region": "West", "hub_type": "SORTING",
            "expected_dwell_hrs": 2, "max_capacity": 3500, "operating_shift": "24x7"
        },
        {
            "hub_id": "HUB014", "hub_name": "Nashik Delivery Hub",
            "city": "Nashik", "region": "West",              # ✅ Fixed — was "South" before
            "hub_type": "DELIVERY",
            "expected_dwell_hrs": 1, "max_capacity": 2800, "operating_shift": "Day"
        },

        # ── SOUTH REGION ──────────────────────────────────────
        {
            "hub_id": "HUB003", "hub_name": "Bengaluru Tech Hub",
            "city": "Bengaluru", "region": "South", "hub_type": "SORTING",
            "expected_dwell_hrs": 2, "max_capacity": 5000, "operating_shift": "24x7"
        },
        {
            "hub_id": "HUB006", "hub_name": "Chennai South Gateway",
            "city": "Chennai", "region": "South", "hub_type": "SORTING",
            "expected_dwell_hrs": 2, "max_capacity": 4000, "operating_shift": "24x7"
        },
        {
            "hub_id": "HUB007", "hub_name": "Hyderabad Distribution Hub",
            "city": "Hyderabad", "region": "South", "hub_type": "DELIVERY",
            "expected_dwell_hrs": 1, "max_capacity": 2000, "operating_shift": "Day"
        },
        {
            "hub_id": "HUB013", "hub_name": "Kochi Delivery Hub",
            "city": "Kochi", "region": "South",              # ✅ Fixed — was "Kerala" (state name)
            "hub_type": "DELIVERY",
            "expected_dwell_hrs": 1, "max_capacity": 3000, "operating_shift": "Day"
        },

        # ── EAST REGION ───────────────────────────────────────
        {
            "hub_id": "HUB005", "hub_name": "Kolkata East Sorting Hub",
            "city": "Kolkata", "region": "East", "hub_type": "SORTING",
            "expected_dwell_hrs": 2, "max_capacity": 4500, "operating_shift": "24x7"
        },

        # ── CENTRAL REGION ────────────────────────────────────
        {
            "hub_id": "HUB004", "hub_name": "Nagpur Central Sorting",
            "city": "Nagpur", "region": "Central", "hub_type": "SORTING",
            "expected_dwell_hrs": 2, "max_capacity": 3500, "operating_shift": "24x7"
        },
        {
            "hub_id": "HUB018", "hub_name": "Indore Central Hub",
            "city": "Indore", "region": "Central", "hub_type": "SORTING",
            "expected_dwell_hrs": 2, "max_capacity": 2200, "operating_shift": "24x7"
        },
    ]


# ─────────────────────────────────────────────
# FILE 3 — CHECKPOINT SCAN EVENTS
# ─────────────────────────────────────────────

def generate_scan_events(shipments, hubs):
    all_events    = []
    event_counter = 1

    city_to_hub = {row["city"]: row["hub_id"] for row in hubs}

    INTERMEDIATE_HUBS = [
        "Nagpur", "Indore", "Bhopal", "Vadodara", "Nashik",
        "Lucknow", "Chandigarh", "Chennai", "Gurgaon",
        "Pune", "Agra", "Hyderabad", "Bengaluru",
        "Ahmedabad", "Kolkata", "Amritsar"
    ]

    for shipment in shipments:
        shipment_id = shipment["shipment_id"]
        origin      = shipment["origin_hub"]
        destination = shipment["destination_hub"]
        distance_km = shipment["distance_km"]
        booking_ts  = shipment["booking_timestamp"]

        current_ts  = datetime.strptime(booking_ts, "%Y-%m-%d %H:%M:%S")

        # Longer distance = more intermediate hubs
        if distance_km <= 300:
            num_intermediate = 0
        elif distance_km <= 800:
            num_intermediate = 1
        else:
            num_intermediate = random.randint(1, 2)

        intermediate = random.sample(INTERMEDIATE_HUBS, num_intermediate)
        route        = [origin] + intermediate + [destination]

        # Delay profile — 70% normal / 20% minor / 10% major
        rand_val = random.randint(1, 100)
        if rand_val <= 70:
            delay_profile = "normal"
        elif rand_val <= 90:
            delay_profile = "minor"
        else:
            delay_profile = "major"

        for i, hub in enumerate(route):
            hub_id = city_to_hub.get(hub)

            # ARRIVED / PICKED_UP
            if i == 0:
                scan_type = "PICKED_UP"
            else:
                segment_distance = distance_km / len(route)
                travel_hrs       = max(2, int(segment_distance / 60))
                current_ts       = current_ts + timedelta(hours=travel_hrs)
                scan_type        = "ARRIVED"

            all_events.append({
                "event_id":       f"EVT-{event_counter:06d}",
                "shipment_id":    shipment_id,
                "hub_name":       hub,
                "hub_id":         hub_id,
                "scan_type":      scan_type,
                "scan_timestamp": current_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "scan_status":    "SUCCESS",
                "delay_profile":  delay_profile,
            })
            event_counter += 1

            # DEPARTED / DELIVERED
            if i == len(route) - 1:
                current_ts = current_ts + timedelta(hours=random.randint(1, 3))
                scan_type  = "DELIVERED"
            else:
                if delay_profile == "normal":
                    dwell_hrs = random.randint(1, 3)
                elif delay_profile == "minor":
                    dwell_hrs = random.randint(4, 8)
                else:
                    dwell_hrs = random.randint(12, 20) if i == 1 else random.randint(1, 3)

                current_ts = current_ts + timedelta(hours=dwell_hrs)
                scan_type  = "DEPARTED"

            all_events.append({
                "event_id":       f"EVT-{event_counter:06d}",
                "shipment_id":    shipment_id,
                "hub_name":       hub,
                "hub_id":         hub_id,
                "scan_type":      scan_type,
                "scan_timestamp": current_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "scan_status":    "SUCCESS",
                "delay_profile":  delay_profile,
            })
            event_counter += 1

    return all_events


# ─────────────────────────────────────────────
# SAVE AS PARQUET — date partitioned
# ADLS pe jaake Spark easily read karega
# ─────────────────────────────────────────────

def save_parquet(data, dataset_name, exec_date):
    folder   = "/opt/airflow/dags/data/raw"
    os.makedirs(folder, exist_ok=True)

    filepath = f"{folder}/{dataset_name}_{exec_date}.parquet"
    pd.DataFrame(data).to_parquet(filepath, index=False, compression="snappy")
    print(f"✅ Saved {len(data)} records → {filepath}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":

    NUM_SHIPMENTS = 100000

    print(f"\n🚚 LogiTrack — Synthetic Data Generator v2")
    print(f"{'─'*50}")
    print(f"Generating {NUM_SHIPMENTS} shipments for {execution_date}...\n")

    shipments = generate_shipment_master(NUM_SHIPMENTS)
    save_parquet(shipments, "shipment_master", execution_date)

    hubs = generate_hub_master()
    save_parquet(hubs, "hub_master", execution_date)

    events = generate_scan_events(shipments, hubs)
    save_parquet(events, "checkpoint_scan_events", execution_date)

    zones    = Counter(s["zone"] for s in shipments)
    types    = Counter(s["shipment_type"] for s in shipments)
    carriers = Counter(s["carrier_name"] for s in shipments)

    print(f"\n📊 Summary:")
    print(f"  Total shipments : {len(shipments)}")
    print(f"  Total events    : {len(events)}")

    print(f"\n  Zone breakdown (distance-based):")
    for z, c in sorted(zones.items()):
        print(f"    {z:8} = {c} shipments")

    print(f"\n  Shipment type:")
    for t, c in types.items():
        print(f"    {t:10} = {c} shipments")

    print(f"\n  Carrier:")
    for cr, c in carriers.items():
        print(f"    {cr:15} = {c} shipments")

    print(f"\n✅ Done! Files saved to /opt/airflow/dags/data/raw/")
    print(f"{'─'*50}\n")