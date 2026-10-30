
import argparse
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

from src.validators import validate_purchase_orders


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def plan(folder):
    folder = Path(folder)

    orders = load_csv(folder / "purchase_order.csv")
    capacities = load_csv(folder / "supplier_capacity.csv")
    lead_times = load_csv(folder / "lead_time.csv")
    inventory = load_csv(folder / "inventory.csv")
    demand = load_csv(folder / "forecast_demand.csv")

    issues = validate_purchase_orders(
        orders, capacities, lead_times
    )

    invalid_po_ids = {
        issue["po_id"]
        for issue in issues
        if issue.get("po_id")
    }

    # A supplier-week capacity violation affects the whole
    # supplier-week group until its orders can be allocated.
    invalid_supplier_weeks = {
        (issue["supplier_id"], issue["week"])
        for issue in issues
        if issue["issue"] == "SUPPLIER_CAPACITY_EXCEEDED"
    }

    all_arrivals = defaultdict(int)
    feasible_arrivals = defaultdict(int)

    for order in orders:
        arrival = date.fromisoformat(order["expected_arrival"])
        year, week, _ = arrival.isocalendar()
        week_label = f"{year}W{week:02d}"

        key = (
            order["sku_id"],
            order["location_id"],
            week_label
        )

        quantity = int(order["quantity"])
        all_arrivals[key] += quantity

        capacity_blocked = (
            order["supplier_id"], week_label
        ) in invalid_supplier_weeks

        if (
            order["po_id"] not in invalid_po_ids
            and not capacity_blocked
        ):
            feasible_arrivals[key] += quantity

    original_balances = {}
    feasible_balances = {}

    for item in inventory:
        key = (item["sku_id"], item["location_id"])
        original_balances[key] = int(item["on_hand"])
        feasible_balances[key] = int(item["on_hand"])

    results = []

    for item in sorted(
        demand,
        key=lambda row: (
            row["week"],
            row["sku_id"],
            row["location_id"]
        )
    ):
        sku = item["sku_id"]
        location = item["location_id"]
        week = item["week"]
        quantity = int(item["quantity"])

        balance_key = (sku, location)
        arrival_key = (sku, location, week)

        original = (
            original_balances[balance_key]
            + all_arrivals[arrival_key]
            - quantity
        )

        feasible = (
            feasible_balances[balance_key]
            + feasible_arrivals[arrival_key]
            - quantity
        )

        results.append({
            "sku_id": sku,
            "location_id": location,
            "week": week,
            "demand": quantity,
            "original_inbound": all_arrivals[arrival_key],
            "feasible_inbound": feasible_arrivals[arrival_key],
            "original_projected_balance": original,
            "feasible_projected_balance": feasible,
            "feasible_shortage_qty": max(0, -feasible)
        })

        original_balances[balance_key] = original
        feasible_balances[balance_key] = feasible

    report_path = folder / "feasible_shortage_plan.csv"

    with report_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=list(results[0])
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"Orders checked: {len(orders)}")
    print(f"Validation issues: {len(issues)}")
    print(f"Planning rows: {len(results)}")
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default="outputs/my_first_run"
    )
    args = parser.parse_args()
    plan(args.input)
