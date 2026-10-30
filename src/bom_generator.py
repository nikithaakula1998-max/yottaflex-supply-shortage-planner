
import argparse
import csv
from pathlib import Path


def generate_bom(folder):
    folder = Path(folder)

    sku_path = folder / "sku.csv"
    bom_path = folder / "bom.csv"

    with sku_path.open(
        "r", newline="", encoding="utf-8"
    ) as file:
        skus = list(csv.DictReader(file))

    # Reserve the first 20% of SKUs as components.
    component_count = max(1, len(skus) // 5)
    components = skus[:component_count]
    finished_products = skus[component_count:]

    count = 0

    with bom_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        columns = [
            "bom_id",
            "parent_sku_id",
            "component_sku_id",
            "quantity_per_unit",
            "uom",
            "effective_from",
            "effective_to",
            "status"
        ]

        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()

        for index, product in enumerate(finished_products):
            # Assign two component types to each finished SKU.
            first = components[index % len(components)]
            second = components[(index + 1) % len(components)]

            for component, quantity in [
                (first, 1),
                (second, 2)
            ]:
                count += 1

                writer.writerow({
                    "bom_id": f"BOM-{count:06d}",
                    "parent_sku_id": product["sku_id"],
                    "component_sku_id": component["sku_id"],
                    "quantity_per_unit": quantity,
                    "uom": "EA",
                    "effective_from": "2026-01-01",
                    "effective_to": "2027-01-01",
                    "status": "ACTIVE"
                })

    print(f"BOM relationships created: {count}")
    print(f"Saved to: {bom_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default="outputs/my_first_run"
    )

    args = parser.parse_args()
    generate_bom(args.input)
