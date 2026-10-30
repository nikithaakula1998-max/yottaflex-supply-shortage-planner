
import argparse
import csv
import re
from collections import Counter
from datetime import date
from pathlib import Path


SCHEMAS = {
    "sku.csv": {
        "required": ["sku_id", "name", "uom", "unit_cost"],
        "key": ["sku_id"],
        "nonnegative": ["unit_cost"],
    },
    "location.csv": {
        "required": ["location_id", "name"],
        "key": ["location_id"],
    },
    "supplier.csv": {
        "required": ["supplier_id", "name", "status"],
        "key": ["supplier_id"],
    },
    "inventory.csv": {
        "required": [
            "inventory_id", "sku_id", "location_id",
            "as_of_date", "on_hand", "uom"
        ],
        "key": ["inventory_id"],
        "nonnegative": ["on_hand"],
        "dates": ["as_of_date"],
    },
    "forecast_demand.csv": {
        "required": [
            "demand_id", "sku_id", "location_id",
            "week", "quantity", "uom"
        ],
        "key": ["demand_id"],
        "nonnegative": ["quantity"],
        "weeks": ["week"],
    },
    "purchase_order.csv": {
        "required": [
            "po_id", "sku_id", "location_id", "supplier_id",
            "quantity", "ordered_on", "expected_arrival",
            "status", "uom"
        ],
        "key": ["po_id"],
        "nonnegative": ["quantity"],
        "dates": ["ordered_on", "expected_arrival"],
    },
    "supplier_capacity.csv": {
        "required": [
            "capacity_id", "supplier_id", "weekly_capacity",
            "moq", "effective_from", "effective_to"
        ],
        "key": ["capacity_id"],
        "nonnegative": ["weekly_capacity", "moq"],
        "dates": ["effective_from", "effective_to"],
    },
    "lead_time.csv": {
        "required": [
            "lead_time_id", "supplier_id", "lead_days",
            "effective_from", "effective_to"
        ],
        "key": ["lead_time_id"],
        "nonnegative": ["lead_days"],
        "dates": ["effective_from", "effective_to"],
    },
    "production_plan.csv": {
        "required": [
            "production_id", "sku_id", "location_id",
            "week", "planned_quantity", "status", "uom"
        ],
        "key": ["production_id"],
        "nonnegative": ["planned_quantity"],
        "weeks": ["week"],
    },
    "production_capacity.csv": {
        "required": [
            "location_id", "week", "max_production_units"
        ],
        "key": ["location_id", "week"],
        "nonnegative": ["max_production_units"],
        "weeks": ["week"],
    },
    "bom.csv": {
        "required": [
            "bom_id", "parent_sku_id", "component_sku_id",
            "quantity_per_unit", "uom",
            "effective_from", "effective_to", "status"
        ],
        "key": ["bom_id"],
        "nonnegative": ["quantity_per_unit"],
        "dates": ["effective_from", "effective_to"],
    },
    "shortage.csv": {
        "required": [
            "shortage_id", "sku_id", "location_id", "week",
            "opening_balance", "inbound", "demand",
            "projected_balance", "shortage_qty",
            "priority_score", "status", "cause"
        ],
        "key": ["shortage_id"],
        "nonnegative": [
            "inbound", "demand", "shortage_qty", "priority_score"
        ],
        "weeks": ["week"],
    },
    "mitigation_option.csv": {
        "required": [
            "mitigation_id", "shortage_id", "option_type",
            "quantity", "estimated_cost", "status", "reason"
        ],
        "key": ["mitigation_id"],
        "nonnegative": ["quantity", "estimated_cost"],
    },
    "ground_truth.csv": {
        "required": [
            "case_id", "issue_type",
            "expected_decision", "description"
        ],
        "key": ["case_id"],
    },
}

REFERENCES = {
    "inventory.csv": {
        "sku_id": "sku.csv",
        "location_id": "location.csv",
    },
    "forecast_demand.csv": {
        "sku_id": "sku.csv",
        "location_id": "location.csv",
    },
    "purchase_order.csv": {
        "sku_id": "sku.csv",
        "location_id": "location.csv",
        "supplier_id": "supplier.csv",
    },
    "supplier_capacity.csv": {
        "supplier_id": "supplier.csv",
    },
    "lead_time.csv": {
        "supplier_id": "supplier.csv",
    },
    "production_plan.csv": {
        "sku_id": "sku.csv",
        "location_id": "location.csv",
    },
    "production_capacity.csv": {
        "location_id": "location.csv",
    },
    "bom.csv": {
        "parent_sku_id": "sku.csv",
        "component_sku_id": "sku.csv",
    },
    "shortage.csv": {
        "sku_id": "sku.csv",
        "location_id": "location.csv",
    },
    "mitigation_option.csv": {
        "shortage_id": "shortage.csv",
    },
}


def valid_week(value):
    match = re.fullmatch(r"(\d{4})W(\d{2})", value)

    if not match:
        return False

    try:
        date.fromisocalendar(
            int(match.group(1)),
            int(match.group(2)),
            1,
        )
        return True
    except ValueError:
        return False


def validate_data(folder):
    folder = Path(folder)
    errors = []
    datasets = {}

    def add_error(filename, row_number, column, issue, value=""):
        errors.append({
            "file": filename,
            "row_number": row_number,
            "column": column,
            "issue": issue,
            "value": value,
        })

    for filename, schema in SCHEMAS.items():
        path = folder / filename

        if not path.exists():
            add_error(filename, 0, "", "MISSING_FILE")
            continue

        with path.open(
            "r", newline="", encoding="utf-8-sig"
        ) as file:
            reader = csv.DictReader(file)
            columns = reader.fieldnames or []

            missing_columns = [
                column for column in schema["required"]
                if column not in columns
            ]

            for column in missing_columns:
                add_error(
                    filename, 1, column, "MISSING_COLUMN"
                )

            if missing_columns:
                continue

            rows = list(reader)
            datasets[filename] = rows
            seen_keys = set()

            for row_number, row in enumerate(rows, start=2):
                for column in schema["required"]:
                    value = row.get(column)

                    if value is None or not str(value).strip():
                        add_error(
                            filename, row_number,
                            column, "MISSING_VALUE"
                        )

                key = tuple(
                    row[column] for column in schema["key"]
                )

                if key in seen_keys:
                    add_error(
                        filename, row_number,
                        ",".join(schema["key"]),
                        "DUPLICATE_KEY", str(key)
                    )

                seen_keys.add(key)

                for column in schema.get("nonnegative", []):
                    value = row.get(column, "")

                    try:
                        number = float(value)

                        if not (
                            number >= 0
                            and number < float("inf")
                        ):
                            raise ValueError

                    except (ValueError, TypeError):
                        add_error(
                            filename, row_number,
                            column, "INVALID_QUANTITY", value
                        )

                for column in schema.get("dates", []):
                    value = row.get(column, "")

                    try:
                        date.fromisoformat(value)
                    except (ValueError, TypeError):
                        add_error(
                            filename, row_number,
                            column, "INVALID_DATE", value
                        )

                for column in schema.get("weeks", []):
                    value = row.get(column, "")

                    if not valid_week(value):
                        add_error(
                            filename, row_number,
                            column, "INVALID_WEEK", value
                        )

                if (
                    "effective_from" in schema.get("dates", [])
                    and "effective_to" in schema.get("dates", [])
                ):
                    try:
                        start = date.fromisoformat(
                            row["effective_from"]
                        )
                        end = date.fromisoformat(
                            row["effective_to"]
                        )

                        if start > end:
                            add_error(
                                filename, row_number,
                                "effective_from,effective_to",
                                "INVALID_EFFECTIVE_RANGE"
                            )
                    except (ValueError, TypeError):
                        pass

                if filename == "purchase_order.csv":
                    try:
                        ordered = date.fromisoformat(
                            row["ordered_on"]
                        )
                        arrival = date.fromisoformat(
                            row["expected_arrival"]
                        )

                        if arrival < ordered:
                            add_error(
                                filename, row_number,
                                "expected_arrival",
                                "ARRIVAL_BEFORE_ORDER"
                            )
                    except (ValueError, TypeError):
                        pass

    # Check references only after the required datasets are loaded.
    reference_ids = {}

    for filename, rows in datasets.items():
        schema = SCHEMAS[filename]

        if len(schema["key"]) == 1:
            id_column = schema["key"][0]

            reference_ids[filename] = {
                row[id_column] for row in rows
                if row.get(id_column)
            }

    for filename, references in REFERENCES.items():
        if filename not in datasets:
            continue

        for row_number, row in enumerate(
            datasets[filename], start=2
        ):
            for column, target_file in references.items():
                if target_file not in reference_ids:
                    continue

                value = row.get(column, "")

                if value and value not in reference_ids[target_file]:
                    add_error(
                        filename, row_number,
                        column, "UNKNOWN_REFERENCE", value
                    )

    output = folder / "data_quality_report.csv"

    with output.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "file", "row_number",
                "column", "issue", "value"
            ],
        )

        writer.writeheader()
        writer.writerows(errors)

    print("Data quality validation completed.")
    print(f"Datasets checked: {len(datasets)}")
    print(f"Total issues found: {len(errors)}")

    counts = Counter(
        error["issue"] for error in errors
    )

    for issue, count in sorted(counts.items()):
        print(f"{issue}: {count}")

    print(f"Report saved: {output}")

    if errors:
        print("Review the reported issues before trusting the plan.")
    else:
        print("No issues found in the implemented data-quality checks.")

    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate supply shortage planner CSV data"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Folder containing the generated CSV files",
    )

    args = parser.parse_args()
    validate_data(args.input)
