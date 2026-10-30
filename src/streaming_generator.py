
import argparse
import csv
import random
import time
from pathlib import Path


def generate_streaming(out, skus, locations, weeks, seed):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    random_generator = random.Random(seed)

    file_path = out / "forecast_demand.csv"

    count = 0
    start = time.perf_counter()

    with file_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "demand_id",
            "sku_id",
            "location_id",
            "week",
            "quantity",
            "uom"
        ])

        for sku_number in range(1, skus + 1):
            sku_id = f"SKU-{sku_number:06d}"

            for location_number in range(1, locations + 1):
                location_id = f"LOC-{location_number:04d}"

                for week in range(1, weeks + 1):
                    quantity = random_generator.randint(15, 65)

                    demand_id = (
                        f"DEM-{sku_id}-{location_id}-"
                        f"2026W{week:02d}"
                    )

                    writer.writerow([
                        demand_id,
                        sku_id,
                        location_id,
                        f"2026W{week:02d}",
                        quantity,
                        "EA"
                    ])

                    count += 1

    elapsed = time.perf_counter() - start

    print(f"Demand rows generated: {count:,}")
    print(f"Time taken: {elapsed:.2f} seconds")
    print(f"Output file: {file_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--out", default="outputs/streaming_test")
    parser.add_argument("--skus", type=int, default=300)
    parser.add_argument("--locations", type=int, default=10)
    parser.add_argument("--weeks", type=int, default=52)
    parser.add_argument("--seed", type=int, default=20261022)

    args = parser.parse_args()

    generate_streaming(
        args.out,
        args.skus,
        args.locations,
        args.weeks,
        args.seed
    )
