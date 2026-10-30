
import csv
import json
from pathlib import Path

SOURCE = Path("outputs/streaming_full_02")
DESTINATION = Path("sample_outputs")

FILES = [
    "sku.csv",
    "location.csv",
    "supplier.csv",
    "inventory.csv",
    "forecast_demand.csv",
    "purchase_order.csv",
    "shortage.csv",
    "mitigation_option.csv",
    "feasible_shortage_plan.csv",
    "supplier_validation_report.csv",
    "cumulative_bom_report.csv",
    "mitigation_feasibility_report.csv",
    "data_quality_report.csv",
    "ground_truth.csv",
]

MAX_ROWS = 100


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    summary = {}

    for filename in FILES:
        source_file = SOURCE / filename
        output_file = DESTINATION / filename

        if not source_file.exists():
            print(f"SKIPPED: {filename} (not found)")
            continue

        with source_file.open(
            "r", newline="", encoding="utf-8-sig"
        ) as source, output_file.open(
            "w", newline="", encoding="utf-8"
        ) as output:

            reader = csv.reader(source)
            writer = csv.writer(output)

            header = next(reader, None)

            if header is None:
                print(f"SKIPPED: {filename} (empty)")
                output_file.unlink()
                continue

            writer.writerow(header)
            count = 0

            for row in reader:
                if count >= MAX_ROWS:
                    break
                writer.writerow(row)
                count += 1

        summary[filename] = count
        print(f"CREATED: {filename} ({count} sample rows)")

    with (DESTINATION / "sample_manifest.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(
            {
                "source": str(SOURCE),
                "sampling_method": "first_rows",
                "maximum_rows_per_file": MAX_ROWS,
                "files": summary,
                "note": (
                    "These are small previews, not complete datasets. "
                    "They should not be used to calculate full-scale totals."
                ),
            },
            file,
            indent=2,
        )

    print("\nSample outputs created successfully!")


if __name__ == "__main__":
    main()
