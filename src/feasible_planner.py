
import argparse
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

from src.validators import validate_purchase_orders


def load_csv(path):
    """Read a CSV file and return its rows."""
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def save_csv(path, rows, fieldnames):
    """Save rows to CSV, including headers when there are no rows."""
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plan(folder):
    folder = Path(folder)

    # Step 1: Load the supply-chain data.
    orders = load_csv(folder / "purchase_order.csv")
    capacities = load_csv(folder / "supplier_capacity.csv")
    lead_times = load_csv(folder / "lead_time.csv")
    inventory = load_csv(folder / "inventory.csv")
    demand = load_csv(folder / "forecast_demand.csv")

    # Step 2: Validate supplier capacity and lead times.
    issues = validate_purchase_orders(
        orders, capacities, lead_times
    )

    # Step 3: Save a detailed supplier validation report.
    validation_report = folder / "supplier_validation_report.csv"

    validation_fields = [
        "po_id",
        "supplier_id",
        "week",
        "issue",
        "ordered_quantity",
        "weekly_capacity"
    ]

    save_csv(
        validation_report,
        issues,
        validation_fields
    )

    # Individual purchase orders that failed validation.
    invalid_po_ids = {
        issue["po_id"]
        for issue in issues
        if issue.get("po_id")
    }

    # A supplier-week capacity violation blocks all orders
    # in that supplier-week until a valid allocation is made.
    invalid_supplier_weeks = {
        (issue["supplier_id"], issue["week"])
        for issue in issues
        if issue["issue"] == "SUPPLIER_CAPACITY_EXCEEDED"
    }

    # Step 4: Calculate original and feasible incoming supply.
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

        # Original supply includes all purchase orders.
        all_arrivals[key] += quantity

        capacity_blocked = (
            order["supplier_id"],
            week_label
        ) in invalid_supplier_weeks

        # Feasible supply excludes invalid orders.
        if (
            order["po_id"] not in invalid_po_ids
            and not capacity_blocked
        ):
            feasible_arrivals[key] += quantity

    # Step 5: Load opening inventory balances.
    original_balances = {}
    feasible_balances = {}

    for item in inventory:
        key = (
            item["sku_id"],
            item["location_id"]
        )

        original_balances[key] = int(item["on_hand"])
        feasible_balances[key] = int(item["on_hand"])

    # Step 6: Calculate inventory balances week by week.
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

    # Step 7: Save the feasible shortage planning report.
    report_path = folder / "feasible_shortage_plan.csv"

    planning_fields = [
        "sku_id",
        "location_id",
        "week",
        "demand",
        "original_inbound",
        "feasible_inbound",
        "original_projected_balance",
        "feasible_projected_balance",
        "feasible_shortage_qty"
    ]

    save_csv(
        report_path,
        results,
        planning_fields
    )

    # Step 8: Display the results.
    print(f"Orders checked: {len(orders)}")
    print(f"Validation issues: {len(issues)}")
    print(f"Planning rows: {len(results)}")
    print(f"Supplier report saved: {validation_report}")
    print(f"Planning report saved: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate supplier constraints and calculate feasible shortages"
    )

    parser.add_argument(
        "--input",
        default="outputs/my_first_run",
        help="Folder containing supply-chain CSV files"
    )

    args = parser.parse_args()
    plan(args.input)
