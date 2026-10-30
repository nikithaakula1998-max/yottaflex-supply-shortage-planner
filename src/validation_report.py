
import argparse
import csv
from pathlib import Path

from src.validators import validate_purchase_orders


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def generate_report(output_dir):
    output_dir = Path(output_dir)

    purchase_orders = read_csv(output_dir / "purchase_order.csv")
    capacities = read_csv(output_dir / "supplier_capacity.csv")
    lead_times = read_csv(output_dir / "lead_time.csv")

    issues = validate_purchase_orders(
        purchase_orders,
        capacities,
        lead_times
    )

    report_path = output_dir / "supplier_validation_report.csv"

    columns = [
        "po_id",
        "supplier_id",
        "week",
        "issue",
        "ordered_quantity",
        "weekly_capacity"
    ]

    with report_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(issues)

    print(f"Purchase orders checked: {len(purchase_orders)}")
    print(f"Validation issues found: {len(issues)}")
    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="outputs/my_first_run"
    )

    args = parser.parse_args()
    generate_report(args.input)
