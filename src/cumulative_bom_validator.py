
import argparse
import csv
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

    components_by_product = defaultdict(list)

    for row in bom:
        if row["status"] != "ACTIVE":
            continue

        components_by_product[row["parent_sku_id"]].append(
            (
                row["component_sku_id"],
                float(row["quantity_per_unit"]),
            )
        )

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
        quantity = float(order["planned_quantity"])

        components = components_by_product.get(product, [])

        if not components:
            report.append({
                "production_id": order["production_id"],
                "sku_id": product,
                "location_id": location,
                "week": order["week"],
                "status": "NO_ACTIVE_BOM",
                "shortage_details": "",
            })
            continue

        shortages = []

        for component, quantity_per_unit in components:
            required = quantity * quantity_per_unit
            available = stock[(component, location)]

            if available < required:
                shortages.append(
                    f"{component}: need {required:g}, "
                    f"available {available:g}"
                )

        if shortages:
            status = "COMPONENT_SHORTAGE"
        else:
            status = "COMPONENT_STOCK_AVAILABLE"

            for component, quantity_per_unit in components:
                stock[(component, location)] -= (
                    quantity * quantity_per_unit
                )

        report.append({
            "production_id": order["production_id"],
            "sku_id": product,
            "location_id": location,
            "week": order["week"],
            "status": status,
            "shortage_details": "; ".join(shortages),
        })

    output = folder / "cumulative_bom_report.csv"

    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "production_id",
                "sku_id",
                "location_id",
                "week",
                "status",
                "shortage_details",
            ],
        )
        writer.writeheader()
        writer.writerows(report)

    counts = defaultdict(int)

    for row in report:
        counts[row["status"]] += 1

    print("Cumulative BOM validation completed.")
    print(f"Production proposals checked: {len(report):,}")

    for status, count in sorted(counts.items()):
        print(f"{status}: {count:,}")

    print(f"Report saved: {output}")
    print(
        "Note: Initial component stock only; "
        "no inbound replenishment or production capacity validation."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    validate_cumulative_bom(args.input)
