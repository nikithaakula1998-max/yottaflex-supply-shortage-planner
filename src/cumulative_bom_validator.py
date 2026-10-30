
import argparse
import csv
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

from src.validators import validate_purchase_orders


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def iso_week(value):
    year, week, _ = date.fromisoformat(value).isocalendar()
    return f"{year}W{week:02d}"


def validate_cumulative_bom(input_folder):
    folder = Path(input_folder)

    inventory = read_csv(folder / "inventory.csv")
    bom = read_csv(folder / "bom.csv")
    production = read_csv(folder / "production_plan.csv")

    stock = defaultdict(float)

    for row in inventory:
        key = (row["sku_id"], row["location_id"])
        stock[key] += float(row["on_hand"])

    components_by_product = defaultdict(lambda: defaultdict(float))

    for row in bom:
        if row["status"] != "ACTIVE":
            continue

        product = row["parent_sku_id"]
        component = row["component_sku_id"]
        quantity_per_unit = float(row["quantity_per_unit"])

        if quantity_per_unit <= 0:
            raise ValueError(
                f"Invalid BOM quantity for {product} -> {component}"
            )

        components_by_product[product][component] += quantity_per_unit

    # Load shared production capacity by location and week.
    capacity_path = folder / "production_capacity.csv"
    remaining_capacity = {}

    if capacity_path.exists():
        for row in read_csv(capacity_path):
            key = (row["location_id"], row["week"])

            if key in remaining_capacity:
                raise ValueError(
                    f"Duplicate production capacity record: {key}"
                )

            capacity = float(row["max_production_units"])

            if capacity < 0:
                raise ValueError(
                    f"Negative production capacity for {key}"
                )

            remaining_capacity[key] = capacity

    # Prepare supplier-validated component deliveries.
    arrivals_by_week = defaultdict(list)
    excluded_purchase_orders = 0

    purchase_order_path = folder / "purchase_order.csv"

    if purchase_order_path.exists():
        orders = read_csv(purchase_order_path)

        capacity_file = folder / "supplier_capacity.csv"
        lead_time_file = folder / "lead_time.csv"

        if not capacity_file.exists() or not lead_time_file.exists():
            raise FileNotFoundError(
                "Supplier capacity and lead-time files are required "
                "when purchase orders are present."
            )

        capacities = read_csv(capacity_file)
        lead_times = read_csv(lead_time_file)

        issues = validate_purchase_orders(
            orders, capacities, lead_times
        )

        invalid_po_ids = {
            issue["po_id"]
            for issue in issues
            if issue.get("po_id")
        }

        invalid_supplier_weeks = {
            (issue["supplier_id"], issue["week"])
            for issue in issues
            if issue["issue"] == "SUPPLIER_CAPACITY_EXCEEDED"
        }

        component_skus = {
            component
            for components in components_by_product.values()
            for component in components
        }

        for order in orders:
            if order["sku_id"] not in component_skus:
                continue

            status = order["status"].strip().upper()

            if status not in {"OPEN", "CONFIRMED"}:
                excluded_purchase_orders += 1
                continue

            arrival_week = iso_week(order["expected_arrival"])

            if (
                order["po_id"] in invalid_po_ids
                or (
                    order["supplier_id"],
                    arrival_week,
                ) in invalid_supplier_weeks
            ):
                excluded_purchase_orders += 1
                continue

            quantity = float(order["quantity"])

            if quantity <= 0:
                excluded_purchase_orders += 1
                continue

            key = (order["sku_id"], order["location_id"])

            arrivals_by_week[arrival_week].append(
                (key, quantity)
            )

    production.sort(
        key=lambda row: (
            row["week"],
            row["location_id"],
            row["production_id"],
        )
    )

    report = []
    delivered_quantity = 0.0

    arrival_weeks = sorted(arrivals_by_week)
    arrival_index = 0

    for order in production:
        product = order["sku_id"]
        location = order["location_id"]
        production_week = order["week"]
        planned = float(order["planned_quantity"])

        if planned < 0:
            raise ValueError(
                f"Negative planned quantity in {order['production_id']}"
            )

        while (
            arrival_index < len(arrival_weeks)
            and arrival_weeks[arrival_index] <= production_week
        ):
            arrival_week = arrival_weeks[arrival_index]

            for key, quantity in arrivals_by_week[arrival_week]:
                stock[key] += quantity
                delivered_quantity += quantity

            arrival_index += 1

        components = components_by_product.get(product, {})
        capacity_key = (location, production_week)

        feasible = 0.0
        shortage_details = []

        if not components:
            status = "NO_ACTIVE_BOM"

        else:
            feasible = planned

            for component, quantity_per_unit in components.items():
                available = max(
                    0.0, stock[(component, location)]
                )

                component_limit = math.floor(
                    (available + 1e-9) / quantity_per_unit
                )

                feasible = min(feasible, component_limit)

                required = planned * quantity_per_unit

                if available + 1e-9 < required:
                    shortage_details.append(
                        f"{component}: need {required:g}, "
                        f"available {available:g}"
                    )

            # Enforce the shared weekly factory capacity.
            if remaining_capacity:
                if capacity_key not in remaining_capacity:
                    feasible = 0.0
                    shortage_details.append(
                        "Missing production capacity record"
                    )
                else:
                    capacity_available = max(
                        0.0, remaining_capacity[capacity_key]
                    )

                    feasible = min(
                        feasible,
                        math.floor(capacity_available + 1e-9),
                    )

                    if capacity_available + 1e-9 < planned:
                        shortage_details.append(
                            "Factory capacity: "
                            f"planned {planned:g}, "
                            f"remaining {capacity_available:g}"
                        )

            feasible = max(0.0, feasible)

            if feasible <= 0 and planned > 0:
                if (
                    remaining_capacity
                    and capacity_key in remaining_capacity
                    and remaining_capacity[capacity_key] <= 0
                ):
                    status = "PRODUCTION_CAPACITY_EXCEEDED"
                elif (
                    remaining_capacity
                    and capacity_key not in remaining_capacity
                ):
                    status = "MISSING_PRODUCTION_CAPACITY"
                else:
                    status = "COMPONENT_SHORTAGE"
            elif feasible < planned:
                status = "PARTIALLY_FEASIBLE"
            else:
                status = "COMPONENT_STOCK_AVAILABLE"

            # Reserve components only for feasible production.
            for component, quantity_per_unit in components.items():
                stock[(component, location)] -= (
                    feasible * quantity_per_unit
                )

            # Reserve factory capacity for the same location and week.
            if capacity_key in remaining_capacity:
                remaining_capacity[capacity_key] -= feasible

        unfulfilled = max(0.0, planned - feasible)

        report.append({
            "production_id": order["production_id"],
            "sku_id": product,
            "location_id": location,
            "week": production_week,
            "planned_quantity": f"{planned:g}",
            "feasible_quantity": f"{feasible:g}",
            "unfulfilled_quantity": f"{unfulfilled:g}",
            "status": status,
            "shortage_details": "; ".join(shortage_details),
        })

    output = folder / "cumulative_bom_report.csv"

    fieldnames = [
        "production_id",
        "sku_id",
        "location_id",
        "week",
        "planned_quantity",
        "feasible_quantity",
        "unfulfilled_quantity",
        "status",
        "shortage_details",
    ]

    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report)

    counts = defaultdict(int)

    total_planned = sum(
        float(row["planned_quantity"]) for row in report
    )
    total_feasible = sum(
        float(row["feasible_quantity"]) for row in report
    )
    total_unfulfilled = sum(
        float(row["unfulfilled_quantity"]) for row in report
    )

    for row in report:
        counts[row["status"]] += 1

    print("Cumulative BOM and capacity feasibility completed.")
    print(f"Production proposals checked: {len(report):,}")

    for status, count in sorted(counts.items()):
        print(f"{status}: {count:,}")

    print(f"Total planned units: {total_planned:g}")
    print(f"Total feasible units: {total_feasible:g}")
    print(f"Total unfulfilled units: {total_unfulfilled:g}")
    print(f"Eligible component deliveries applied: {delivered_quantity:g}")
    print(f"Excluded component purchase orders: {excluded_purchase_orders}")
    print(f"Production capacity records loaded: {len(remaining_capacity)}")
    print(f"Report saved: {output}")

    print(
        "Limitations: Supplier-valid expected deliveries are assumed "
        "to arrive on time. BOM effective dates and component demand "
        "outside production are not modeled."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate BOM and factory-capacity feasibility"
    )
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    validate_cumulative_bom(args.input)
