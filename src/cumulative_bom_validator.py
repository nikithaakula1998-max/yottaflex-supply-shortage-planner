
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


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

    production.sort(
        key=lambda row: (
            row["week"],
            row["location_id"],
            row["production_id"],
        )
    )

    report = []

    for order in production:
        product = order["sku_id"]
        location = order["location_id"]
        planned = float(order["planned_quantity"])

        if planned < 0:
            raise ValueError(
                f"Negative planned quantity in {order['production_id']}"
            )

        components = components_by_product.get(product, {})

        feasible = 0.0
        shortage_details = []

        if not components:
            status = "NO_ACTIVE_BOM"

        else:
            feasible = planned

            for component, quantity_per_unit in components.items():
                available = max(0.0, stock[(component, location)])

                # Finished production units are treated as whole units.
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

            feasible = max(0.0, feasible)

            if feasible <= 0 and planned > 0:
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

        unfulfilled = max(0.0, planned - feasible)

        report.append({
            "production_id": order["production_id"],
            "sku_id": product,
            "location_id": location,
            "week": order["week"],
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

    total_planned = 0.0
    total_feasible = 0.0
    total_unfulfilled = 0.0

    for row in report:
        counts[row["status"]] += 1
        total_planned += float(row["planned_quantity"])
        total_feasible += float(row["feasible_quantity"])
        total_unfulfilled += float(row["unfulfilled_quantity"])

    print("Cumulative BOM feasibility completed.")
    print(f"Production proposals checked: {len(report):,}")

    for status, count in sorted(counts.items()):
        print(f"{status}: {count:,}")

    print(f"Total planned units: {total_planned:g}")
    print(f"Total feasible units: {total_feasible:g}")
    print(f"Total unfulfilled units: {total_unfulfilled:g}")
    print(f"Report saved: {output}")

    print(
        "Limitations: Uses initial component stock only. "
        "Does not include incoming component deliveries, "
        "production capacity, or BOM effective dates."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate feasible production from cumulative BOM stock"
    )

    parser.add_argument("--input", required=True)

    args = parser.parse_args()

    validate_cumulative_bom(args.input)
