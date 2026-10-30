
import argparse
import csv
import hashlib
import json
import random
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


SEED = 20261022

SCHEMAS = {
    "sku": ["sku_id", "name", "uom", "unit_cost"],
    "location": ["location_id", "name"],
    "supplier": ["supplier_id", "name", "status"],
    "supplier_capacity": [
        "capacity_id", "supplier_id", "weekly_capacity",
        "moq", "effective_from", "effective_to"
    ],
    "lead_time": [
        "lead_time_id", "supplier_id", "lead_days",
        "effective_from", "effective_to"
    ],
    "inventory": [
        "inventory_id", "sku_id", "location_id",
        "as_of_date", "on_hand", "uom"
    ],
    "forecast_demand": [
        "demand_id", "sku_id", "location_id",
        "week", "quantity", "uom"
    ],
    "purchase_order": [
        "po_id", "sku_id", "location_id", "supplier_id",
        "quantity", "ordered_on", "expected_arrival",
        "status", "uom"
    ],
    "production_plan": [
        "production_id", "sku_id", "location_id",
        "week", "planned_quantity", "status", "uom"
    ],
    "production_capacity": [
        "location_id", "week", "max_production_units"
    ],
    "bom": [
        "bom_id", "parent_sku_id", "component_sku_id",
        "quantity_per_unit", "uom",
        "effective_from", "effective_to", "status"
    ],
    "shortage": [
        "shortage_id", "sku_id", "location_id",
        "week", "opening_balance", "inbound", "demand",
        "projected_balance", "shortage_qty",
        "priority_score", "status", "cause"
    ],
    "mitigation_option": [
        "mitigation_id", "shortage_id", "option_type",
        "quantity", "estimated_cost", "status", "reason"
    ],
    "ground_truth": [
        "case_id", "issue_type",
        "expected_decision", "description"
    ],
}


def open_writer(folder, name):
    path = folder / f"{name}.csv"
    handle = path.open("w", newline="", encoding="utf-8")
    writer = csv.DictWriter(handle, fieldnames=SCHEMAS[name])
    writer.writeheader()
    return handle, writer


def file_hash(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def generate_streaming(
    out,
    skus=3000,
    locations=50,
    weeks=52,
    suppliers=500,
    orders=10000,
    seed=SEED,
):
    if min(skus, locations, weeks, suppliers) < 1:
        raise ValueError(
            "SKUs, locations, weeks and suppliers must be positive"
        )

    if weeks > 52:
        raise ValueError("Weeks must not exceed 52")

    if orders < 0:
        raise ValueError("Orders cannot be negative")

    folder = Path(out)

    if folder.exists() and any(folder.iterdir()):
        raise ValueError(
            f"Output folder is not empty: {folder}. "
            "Use a new output folder."
        )

    folder.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    start = date.fromisocalendar(2026, 1, 1)
    started = time.perf_counter()
    counts = {name: 0 for name in SCHEMAS}

    print(
        "Starting streaming supply-chain generation...",
        flush=True,
    )

    def write_rows(name, rows):
        handle, writer = open_writer(folder, name)

        try:
            for row in rows:
                writer.writerow(row)
                counts[name] += 1
        finally:
            handle.close()

    sku_costs = {}

    def sku_rows():
        for number in range(1, skus + 1):
            sku_id = f"SKU-{number:06d}"
            unit_cost = rng.randint(10, 200)
            sku_costs[sku_id] = unit_cost

            yield {
                "sku_id": sku_id,
                "name": f"Product {number}",
                "uom": "EA",
                "unit_cost": unit_cost,
            }

    write_rows("sku", sku_rows())

    def location_rows():
        for number in range(1, locations + 1):
            yield {
                "location_id": f"LOC-{number:04d}",
                "name": f"Warehouse {number}",
            }

    write_rows("location", location_rows())

    def supplier_rows():
        for number in range(1, suppliers + 1):
            yield {
                "supplier_id": f"SUP-{number:04d}",
                "name": f"Supplier {number}",
                "status": "ACTIVE",
            }

    write_rows("supplier", supplier_rows())

    capacities = {}
    lead_days = {}

    def capacity_rows():
        for number in range(1, suppliers + 1):
            supplier_id = f"SUP-{number:04d}"
            capacity = rng.randint(200, 1000)
            capacities[supplier_id] = capacity

            yield {
                "capacity_id": f"CAP-{supplier_id}",
                "supplier_id": supplier_id,
                "weekly_capacity": capacity,
                "moq": 10,
                "effective_from": "2025-12-29",
                "effective_to": "2027-01-01",
            }

    write_rows("supplier_capacity", capacity_rows())

    def lead_rows():
        for number in range(1, suppliers + 1):
            supplier_id = f"SUP-{number:04d}"
            days = rng.randint(7, 28)
            lead_days[supplier_id] = days

            yield {
                "lead_time_id": f"LT-{supplier_id}",
                "supplier_id": supplier_id,
                "lead_days": days,
                "effective_from": "2025-12-29",
                "effective_to": "2027-01-01",
            }

    write_rows("lead_time", lead_rows())

    def capacity_plan_rows():
        for location_number in range(1, locations + 1):
            location_id = f"LOC-{location_number:04d}"

            for week_number in range(1, weeks + 1):
                yield {
                    "location_id": location_id,
                    "week": f"2026W{week_number:02d}",
                    "max_production_units": 100,
                }

    write_rows("production_capacity", capacity_plan_rows())

    def bom_rows():
        if skus < 3:
            return

        component_count = max(1, skus // 5)
        component_count = min(component_count, skus - 1)
        bom_number = 0

        for parent_number in range(
            component_count + 1, skus + 1
        ):
            parent_id = f"SKU-{parent_number:06d}"

            first_component = (
                (parent_number - component_count - 1)
                % component_count
            ) + 1

            component_numbers = [first_component]

            if component_count >= 2:
                second_component = (
                    first_component % component_count
                ) + 1
                component_numbers.append(second_component)

            for component_number in component_numbers:
                bom_number += 1

                yield {
                    "bom_id": f"BOM-{bom_number:06d}",
                    "parent_sku_id": parent_id,
                    "component_sku_id": (
                        f"SKU-{component_number:06d}"
                    ),
                    "quantity_per_unit": (
                        1 if component_number == first_component
                        else 2
                    ),
                    "uom": "EA",
                    "effective_from": "2026-01-01",
                    "effective_to": "2027-01-01",
                    "status": "ACTIVE",
                }

    write_rows("bom", bom_rows())

    arrivals = defaultdict(int)
    committed = defaultdict(int)

    # Allocate all orders against the delivery week.
    # Each supplier/week has a fixed capacity.
    # If a selected supplier is full, choose another
    # supplier with sufficient available capacity.
    def purchase_order_rows():
        for number in range(1, orders + 1):
            sku_number = rng.randint(1, skus)
            location_number = rng.randint(1, locations)
            preferred_supplier = rng.randint(1, suppliers)
            week_number = rng.randint(1, weeks)

            sku_id = f"SKU-{sku_number:06d}"
            location_id = f"LOC-{location_number:04d}"

            arrival = start + timedelta(
                weeks=week_number - 1
            )

            arrival_week = arrival.isocalendar()
            week_key = (
                arrival_week.year,
                arrival_week.week,
            )

            requested_quantity = rng.randint(10, 80)

            selected_supplier = None
            selected_quantity = None

            for offset in range(suppliers):
                supplier_number = (
                    (preferred_supplier - 1 + offset)
                    % suppliers
                ) + 1

                supplier_id = f"SUP-{supplier_number:04d}"

                capacity_key = (
                    supplier_id,
                    week_key[0],
                    week_key[1],
                )

                available = (
                    capacities[supplier_id]
                    - committed[capacity_key]
                )

                if available >= requested_quantity:
                    selected_supplier = supplier_id
                    selected_quantity = requested_quantity
                    break

            if selected_supplier is None:
                raise ValueError(
                    "Not enough supplier capacity to "
                    f"allocate purchase order {number} "
                    f"in delivery week {week_number}. "
                    "Increase suppliers or capacity, "
                    "or reduce the order count."
                )

            capacity_key = (
                selected_supplier,
                week_key[0],
                week_key[1],
            )
            committed[capacity_key] += selected_quantity

            ordered_on = arrival - timedelta(
                days=lead_days[selected_supplier]
            )

            arrivals[
                (sku_id, location_id, week_number)
            ] += selected_quantity

            yield {
                "po_id": f"PO-2026-{number:06d}",
                "sku_id": sku_id,
                "location_id": location_id,
                "supplier_id": selected_supplier,
                "quantity": selected_quantity,
                "ordered_on": ordered_on.isoformat(),
                "expected_arrival": arrival.isoformat(),
                "status": "OPEN",
                "uom": "EA",
            }

    write_rows("purchase_order", purchase_order_rows())

    print(
        "Purchase orders generated: "
        f"{counts['purchase_order']:,}",
        flush=True,
    )

    inventory_file, inventory_writer = open_writer(
        folder, "inventory"
    )
    demand_file, demand_writer = open_writer(
        folder, "forecast_demand"
    )
    production_file, production_writer = open_writer(
        folder, "production_plan"
    )
    shortage_file, shortage_writer = open_writer(
        folder, "shortage"
    )
    mitigation_file, mitigation_writer = open_writer(
        folder, "mitigation_option"
    )

    shortage_number = 0
    production_number = 0

    try:
        for sku_number in range(1, skus + 1):
            sku_id = f"SKU-{sku_number:06d}"

            for location_number in range(
                1, locations + 1
            ):
                location_id = f"LOC-{location_number:04d}"
                balance = rng.randint(80, 350)

                inventory_writer.writerow({
                    "inventory_id": (
                        f"INV-{sku_id}-{location_id}"
                    ),
                    "sku_id": sku_id,
                    "location_id": location_id,
                    "as_of_date": start.isoformat(),
                    "on_hand": balance,
                    "uom": "EA",
                })
                counts["inventory"] += 1

                for week_number in range(
                    1, weeks + 1
                ):
                    week = f"2026W{week_number:02d}"
                    quantity = rng.randint(15, 65)

                    if (
                        week_number in (6, 12, 40)
                        and rng.random() < 0.12
                    ):
                        quantity *= 3

                    demand_writer.writerow({
                        "demand_id": (
                            f"DEM-{sku_id}-{location_id}-{week}"
                        ),
                        "sku_id": sku_id,
                        "location_id": location_id,
                        "week": week,
                        "quantity": quantity,
                        "uom": "EA",
                    })
                    counts["forecast_demand"] += 1

                    production_number += 1
                    production_writer.writerow({
                        "production_id": (
                            f"PROD-{production_number:08d}"
                        ),
                        "sku_id": sku_id,
                        "location_id": location_id,
                        "week": week,
                        "planned_quantity": max(
                            1, quantity // 5
                        ),
                        "status": "PROPOSED_UNVERIFIED",
                        "uom": "EA",
                    })
                    counts["production_plan"] += 1

                    opening = balance
                    inbound = arrivals.get(
                        (
                            sku_id,
                            location_id,
                            week_number,
                        ),
                        0,
                    )

                    balance = (
                        opening + inbound - quantity
                    )

                    if balance < 0:
                        shortage_number += 1
                        shortage_id = (
                            "SHORT-2026-"
                            f"{shortage_number:08d}"
                        )
                        missing = -balance

                        shortage_writer.writerow({
                            "shortage_id": shortage_id,
                            "sku_id": sku_id,
                            "location_id": location_id,
                            "week": week,
                            "opening_balance": opening,
                            "inbound": inbound,
                            "demand": quantity,
                            "projected_balance": balance,
                            "shortage_qty": missing,
                            "priority_score": (
                                missing
                                * sku_costs[sku_id]
                            ),
                            "status": "OPEN",
                            "cause": (
                                "DEMAND_EXCEEDS_AVAILABLE"
                            ),
                        })
                        counts["shortage"] += 1

                        mitigation_writer.writerow({
                            "mitigation_id": (
                                f"MIT-{shortage_id}-01"
                            ),
                            "shortage_id": shortage_id,
                            "option_type": "EXPEDITE_SUPPLY",
                            "quantity": missing,
                            "estimated_cost": round(
                                missing
                                * sku_costs[sku_id]
                                * 1.25,
                                2,
                            ),
                            "status": (
                                "CANDIDATE_UNVERIFIED"
                            ),
                            "reason": (
                                "Requires supplier capacity, "
                                "MOQ and lead-time confirmation"
                            ),
                        })
                        counts["mitigation_option"] += 1

            if sku_number % 500 == 0:
                print(
                    f"Processed {sku_number:,}/"
                    f"{skus:,} SKUs; "
                    f"{counts['forecast_demand']:,} "
                    "demand rows",
                    flush=True,
                )
    finally:
        inventory_file.close()
        demand_file.close()
        production_file.close()
        shortage_file.close()
        mitigation_file.close()

    anomaly_types = [
        "INBOUND_DOUBLE_COUNT",
        "UNAPPROVED_SUBSTITUTE",
        "SUPPLIER_CAPACITY_EXCEEDED",
        "LEAD_TIME_IGNORED",
        "UOM_MISMATCH",
    ]

    def truth_rows():
        for number, kind in enumerate(
            anomaly_types, start=1
        ):
            yield {
                "case_id": f"CASE-{number:03d}",
                "issue_type": kind,
                "expected_decision": "FLAG_FOR_REVIEW",
                "description": (
                    "Synthetic isolated test case; "
                    "not applied to baseline tables"
                ),
            }

    write_rows("ground_truth", truth_rows())

    manifest = {
        "seed": seed,
        "parameters": {
            "skus": skus,
            "locations": locations,
            "weeks": weeks,
            "suppliers": suppliers,
            "orders": orders,
        },
        "row_counts": counts,
        "sha256": {
            path.name: file_hash(path)
            for path in sorted(
                folder.glob("*.csv")
            )
        },
        "notes": [
            "All data is synthetic.",
            "CSV files are generated by streaming.",
            "Supplier capacity is allocated by delivery week.",
            "Orders respect generated supplier lead times.",
            "Production proposals are unverified.",
            "Shortages exclude proposed production.",
            "Mitigation candidates are not approved.",
            "Full production feasibility is not established.",
        ],
    }

    manifest_path = folder / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    elapsed = time.perf_counter() - started

    print("\nSTREAMING GENERATION COMPLETED")
    print(f"Time taken: {elapsed:.2f} seconds")
    print(f"Output folder: {folder}")

    for name, count in counts.items():
        print(f"{name}: {count:,}")

    print(f"Manifest saved: {manifest_path}")
    print(
        "Important: Production and mitigation "
        "decisions remain unverified."
    )

    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Generate synthetic supply-chain "
            "CSV datasets using streaming"
        )
    )

    parser.add_argument(
        "--out",
        default="outputs/streaming_full",
    )
    parser.add_argument(
        "--skus",
        type=int,
        default=3000,
    )
    parser.add_argument(
        "--locations",
        type=int,
        default=50,
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=52,
    )
    parser.add_argument(
        "--suppliers",
        type=int,
        default=500,
    )
    parser.add_argument(
        "--orders",
        type=int,
        default=10000,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SEED,
    )

    args = parser.parse_args()

    try:
        generate_streaming(
            out=args.out,
            skus=args.skus,
            locations=args.locations,
            weeks=args.weeks,
            suppliers=args.suppliers,
            orders=args.orders,
            seed=args.seed,
        )
    except ValueError as error:
        parser.error(str(error))
