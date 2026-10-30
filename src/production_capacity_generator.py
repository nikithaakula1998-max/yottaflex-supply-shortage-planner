
import argparse
import csv
from pathlib import Path


def generate_production_capacity(folder, weekly_capacity=100):
    folder = Path(folder)

    production_path = folder / "production_plan.csv"

    with production_path.open(
        "r", newline="", encoding="utf-8"
    ) as file:
        production = list(csv.DictReader(file))

    location_weeks = sorted({
        (row["location_id"], row["week"])
        for row in production
    })

    output_path = folder / "production_capacity.csv"

    with output_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "location_id",
                "week",
                "max_production_units",
            ],
        )

        writer.writeheader()

        for location_id, week in location_weeks:
            writer.writerow({
                "location_id": location_id,
                "week": week,
                "max_production_units": weekly_capacity,
            })

    print("Production capacity dataset generated.")
    print(f"Location-week capacity records: {len(location_weeks)}")
    print(f"Weekly capacity per location: {weekly_capacity}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate synthetic weekly production capacities"
    )

    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--capacity",
        type=int,
        default=100,
        help="Maximum production units per location per week",
    )

    args = parser.parse_args()

    if args.capacity < 0:
        parser.error("--capacity must be zero or greater")

    generate_production_capacity(args.input, args.capacity)
