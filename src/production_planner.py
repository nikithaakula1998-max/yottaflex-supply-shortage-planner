
import argparse
import csv
from pathlib import Path


def create_production_plan(folder):
    folder = Path(folder)

    demand_path = folder / "forecast_demand.csv"
    output_path = folder / "production_plan.csv"

    count = 0

    with demand_path.open(
        "r", newline="", encoding="utf-8"
    ) as source, output_path.open(
        "w", newline="", encoding="utf-8"
    ) as destination:

        reader = csv.DictReader(source)

        columns = [
            "production_id",
            "sku_id",
            "location_id",
            "week",
            "planned_quantity",
            "status",
            "uom"
        ]

        writer = csv.DictWriter(
            destination,
            fieldnames=columns
        )

        writer.writeheader()

        for row in reader:
            # Plan production for 20% of forecast demand.
            quantity = round(int(row["quantity"]) * 0.20)

            if quantity <= 0:
                continue

            count += 1

            writer.writerow({
                "production_id": f"PROD-{count:08d}",
                "sku_id": row["sku_id"],
                "location_id": row["location_id"],
                "week": row["week"],
                "planned_quantity": quantity,
                "status": "PROPOSED_UNVERIFIED",
                "uom": row["uom"]
            })

    print(f"Production plan rows: {count:,}")
    print(f"Saved to: {output_path}")
    print("Status: PROPOSED_UNVERIFIED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="outputs/my_first_run"
    )
    args = parser.parse_args()

    create_production_plan(args.input)
