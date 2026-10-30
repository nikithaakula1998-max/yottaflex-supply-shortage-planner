
import argparse
import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


REPORT_COLUMNS = [
    "mitigation_id",
    "shortage_id",
    "sku_id",
    "location_id",
    "shortage_week",
    "supplier_id",
    "requested_quantity",
    "potential_quantity",
    "remaining_quantity",
    "estimated_potential_cost",
    "status",
    "reason",
]


def read_csv(folder, filename):
    path = folder / filename
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def week_start(value):
    year = int(value[:4])
    week = int(value[-2:])
    return date.fromisocalendar(year, week, 1)


def week_key(value):
    year, week, _ = value.isocalendar()
    return f"{year}W{week:02d}"


def is_active(row, on_date):
    return (
        date.fromisoformat(row["effective_from"])
        <= on_date
        <= date.fromisoformat(row["effective_to"])
    )


def evaluate_mitigations(folder):
    mitigations = read_csv(folder, "mitigation_option.csv")
    shortages = {
        row["shortage_id"]: row
        for row in read_csv(folder, "shortage.csv")
    }
    suppliers = {
        row["supplier_id"]: row
        for row in read_csv(folder, "supplier.csv")
    }
    purchase_orders = read_csv(folder, "purchase_order.csv")
    capacities = read_csv(folder, "supplier_capacity.csv")
    lead_times = read_csv(folder, "lead_time.csv")

    # A supplier-SKU relationship is inferred only from actual POs.
    # This is evidence, not a confirmed supplier qualification.
    suppliers_by_sku = defaultdict(set)
    committed = defaultdict(float)

    for po in purchase_orders:
        if po["status"].upper() not in {"OPEN", "CONFIRMED"}:
            continue

        supplier_id = po["supplier_id"]
        sku_id = po["sku_id"]
        suppliers_by_sku[sku_id].add(supplier_id)

        order_week = week_key(date.fromisoformat(po["ordered_on"]))
        committed[(supplier_id, order_week)] += float(
            po["quantity"]
        )

    capacity_by_supplier = defaultdict(list)
    lead_by_supplier = defaultdict(list)

    for row in capacities:
        capacity_by_supplier[row["supplier_id"]].append(row)

    for row in lead_times:
        lead_by_supplier[row["supplier_id"]].append(row)

    # Reserve capacity across suggested mitigations.
    reserved = defaultdict(float)
    results = []

    # Process higher-priority shortages first, deterministically.
    def priority(mitigation):
        shortage = shortages.get(mitigation["shortage_id"], {})
        return (
            -float(shortage.get("priority_score", 0)),
            mitigation["mitigation_id"],
        )

    for mitigation in sorted(mitigations, key=priority):
        shortage = shortages.get(mitigation["shortage_id"])

        requested = float(mitigation["quantity"])
        result = {
            "mitigation_id": mitigation["mitigation_id"],
            "shortage_id": mitigation["shortage_id"],
            "sku_id": "",
            "location_id": "",
            "shortage_week": "",
            "supplier_id": "",
            "requested_quantity": requested,
            "potential_quantity": 0,
            "remaining_quantity": requested,
            "estimated_potential_cost": 0,
            "status": "FLAG_FOR_REVIEW",
            "reason": "",
        }

        if shortage is None:
            result["reason"] = "Unknown shortage reference"
            results.append(result)
            continue

        sku_id = shortage["sku_id"]
        result["sku_id"] = sku_id
        result["location_id"] = shortage["location_id"]
        result["shortage_week"] = shortage["week"]

        if mitigation["option_type"] != "EXPEDITE_SUPPLY":
            result["reason"] = "Unsupported mitigation type"
            results.append(result)
            continue

        if requested <= 0:
            result["reason"] = "Invalid requested quantity"
            results.append(result)
            continue

        deadline = week_start(shortage["week"])

        # Assumption: planning starts on the first day of the
        # generated forecast horizon, not the current real-world date.
        all_shortage_weeks = [
            week_start(row["week"])
            for row in shortages.values()
        ]
        planning_start = min(all_shortage_weeks)

        candidates = []

        for supplier_id in sorted(suppliers_by_sku[sku_id]):
            supplier = suppliers.get(supplier_id)

            if supplier is None:
                continue

            if supplier["status"].upper() not in {
                "ACTIVE", "APPROVED"
            }:
                continue

            matching_capacities = [
                row for row in capacity_by_supplier[supplier_id]
                if is_active(row, planning_start)
            ]
            matching_leads = [
                row for row in lead_by_supplier[supplier_id]
                if is_active(row, planning_start)
            ]

            if len(matching_capacities) != 1:
                continue

            if len(matching_leads) != 1:
                continue

            capacity = matching_capacities[0]
            lead = matching_leads[0]

            arrival = planning_start + timedelta(
                days=int(lead["lead_days"])
            )

            # Do not assume unconfirmed expediting can shorten lead time.
            if arrival > deadline:
                continue

            order_week = week_key(planning_start)
            key = (supplier_id, order_week)

            available = max(
                0.0,
                float(capacity["weekly_capacity"])
                - committed[key]
                - reserved[key],
            )

            moq = float(capacity["moq"])

            # A mitigation cannot exceed the remaining shortage.
            quantity = min(
                requested,
                float(shortage["shortage_qty"]),
                available,
            )

            if quantity < moq or quantity <= 0:
                continue

            candidates.append((quantity, supplier_id, key))

        if not candidates:
            result["reason"] = (
                "No evidenced active supplier can meet normal "
                "lead time, MOQ and remaining weekly capacity; "
                "expediting requires separate confirmation"
            )
            results.append(result)
            continue

        # Select the supplier with the highest potential quantity.
        quantity, supplier_id, key = sorted(
            candidates,
            key=lambda item: (-item[0], item[1])
        )[0]

        reserved[key] += quantity

        result["supplier_id"] = supplier_id
        result["potential_quantity"] = round(quantity, 4)
        result["remaining_quantity"] = round(
            max(0, requested - quantity), 4
        )

        unit_cost = (
            float(mitigation["estimated_cost"]) / requested
        )
        result["estimated_potential_cost"] = round(
            unit_cost * quantity, 2
        )

        result["status"] = "POTENTIALLY_FEASIBLE_UNCONFIRMED"
        result["reason"] = (
            "Passes modeled supplier capacity, MOQ and normal "
            "lead-time checks; supplier-SKU qualification and "
            "delivery still require confirmation"
        )

        results.append(result)

    return sorted(
        results,
        key=lambda row: row["mitigation_id"]
    )


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate shortage mitigation feasibility"
    )
    parser.add_argument(
        "--input",
        default="outputs/pipeline_test_01",
        help="Folder containing generated CSV files",
    )
    args = parser.parse_args()

    folder = Path(args.input)
    results = evaluate_mitigations(folder)

    report = folder / "mitigation_feasibility_report.csv"

    with report.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=REPORT_COLUMNS
        )
        writer.writeheader()
        writer.writerows(results)

    print("Mitigation feasibility evaluation completed.")
    print(f"Options checked: {len(results)}")

    counts = defaultdict(int)
    for row in results:
        counts[row["status"]] += 1

    for status, count in sorted(counts.items()):
        print(f"{status}: {count}")

    print(f"Report saved: {report}")
    print(
        "Important: Potential feasibility is not supplier "
        "approval or a guaranteed delivery."
    )


if __name__ == "__main__":
    main()
