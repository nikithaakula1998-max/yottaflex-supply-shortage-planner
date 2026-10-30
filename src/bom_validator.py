
import argparse
import csv
from collections import defaultdict
from pathlib import Path


def load_csv(path):
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def validate_bom(folder):
    folder = Path(folder)

    bom = load_csv(folder / "bom.csv")
    production = load_csv(folder / "production_plan.csv")
    inventory = load_csv(folder / "inventory.csv")

    # Components needed for each finished product.
    components = defaultdict(list)

    for row in bom:
        components[row["parent_sku_id"]].append(
            (
                row["component_sku_id"],
                float(row["quantity_per_unit"])
            )
        )

    # Initial inventory available at each location.
    available = defaultdict(float)

    for row in inventory:
        key = (row["sku_id"], row["location_id"])
        available[key] += float(row["on_hand"])

    output_path = folder / "bom_validation_report.csv"
    count = 0

    with output_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        columns = [
            "production_id",
            "parent_sku_id",
            "location_id",
            "week",
            "component_sku_id",
            "required_quantity",
            "available_quantity",
            "shortfall_quantity",
            "status"
        ]

        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()

        for plan in production:
            parent = plan["sku_id"]
            location = plan["location_id"]
            quantity = float(plan["planned_quantity"])

            for component_id, units_per_product in components.get(
                parent, []
            ):
                required = quantity * units_per_product
                stock = available[(component_id, location)]
                shortfall = max(0, required - stock)

                status = (
                    "COMPONENT_SHORTAGE"
                    if shortfall > 0
                    else "SUFFICIENT_AT_CHECK"
                )

                writer.writerow({
                    "production_id": plan["production_id"],
                    "parent_sku_id": parent,
                    "location_id": location,
                    "week": plan["week"],
                    "component_sku_id": component_id,
                    "required_quantity": required,
                    "available_quantity": stock,
                    "shortfall_quantity": shortfall,
                    "status": status
                })

                count += 1

    print(f"BOM checks completed: {count:,}")
    print(f"Report saved: {output_path}")
    print("Note: Snapshot checks only; stock is not reserved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default="outputs/my_first_run"
    )

    args = parser.parse_args()
    validate_bom(args.input)
