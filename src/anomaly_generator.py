
import argparse
import csv
from datetime import date, timedelta
from pathlib import Path


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def generate_anomalies(input_folder):
    folder = Path(input_folder)
    output = folder / "anomaly_cases"
    output.mkdir(exist_ok=True)

    orders = read_csv(folder / "purchase_order.csv")
    capacities = read_csv(folder / "supplier_capacity.csv")

    if not orders or not capacities:
        raise ValueError("Purchase orders and supplier capacities are required.")

    po_columns = list(orders[0].keys())
    capacity_columns = list(capacities[0].keys())

    # Case 1: Duplicate inbound purchase order
    duplicate = dict(orders[0])
    duplicate["case_id"] = "CASE-001"
    duplicate["issue_type"] = "INBOUND_DOUBLE_COUNT"

    # Case 3: Order quantity exceeds supplier capacity
    capacity = capacities[0]
    oversized = dict(orders[0])
    oversized["po_id"] = "ANOMALY-CAPACITY-001"
    oversized["supplier_id"] = capacity["supplier_id"]
    oversized["quantity"] = str(int(float(capacity["weekly_capacity"])) + 100)
    oversized["case_id"] = "CASE-003"
    oversized["issue_type"] = "SUPPLIER_CAPACITY_EXCEEDED"

    # Case 4: Arrival before order date
    early = dict(orders[0])
    early["po_id"] = "ANOMALY-LEAD-001"
    early["expected_arrival"] = (
        date.fromisoformat(early["ordered_on"]) - timedelta(days=1)
    ).isoformat()
    early["case_id"] = "CASE-004"
    early["issue_type"] = "LEAD_TIME_IGNORED"

    # Case 5: Inconsistent unit of measure
    wrong_uom = dict(orders[0])
    wrong_uom["po_id"] = "ANOMALY-UOM-001"
    wrong_uom["uom"] = "KG"
    wrong_uom["case_id"] = "CASE-005"
    wrong_uom["issue_type"] = "UOM_MISMATCH"

    # Case 2: Unapproved substitution
    # Separate scenario because purchase_order.csv has no substitute column.
    substitution = [{
        "case_id": "CASE-002",
        "issue_type": "UNAPPROVED_SUBSTITUTE",
        "original_sku_id": orders[0]["sku_id"],
        "substitute_sku_id": "SKU-UNAPPROVED",
        "approved": "False",
        "expected_decision": "FLAG_FOR_REVIEW",
    }]

    scenario_columns = po_columns + ["case_id", "issue_type"]

    write_csv(
        output / "anomaly_purchase_orders.csv",
        [duplicate, oversized, early, wrong_uom],
        scenario_columns,
    )

    write_csv(
        output / "anomaly_substitution.csv",
        substitution,
        list(substitution[0].keys()),
    )

    print("Anomaly test data generated successfully.")
    print("Cases created: 5")
    print(f"Saved in: {output}")
    print("Original baseline files were not modified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    generate_anomalies(args.input)
