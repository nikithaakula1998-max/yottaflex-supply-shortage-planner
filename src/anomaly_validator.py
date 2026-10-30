
import argparse
import csv
from datetime import date
from pathlib import Path


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate(input_folder):
    folder = Path(input_folder)
    cases_folder = folder / "anomaly_cases"

    baseline = read_csv(folder / "purchase_order.csv")
    capacities = read_csv(folder / "supplier_capacity.csv")
    anomalies = read_csv(cases_folder / "anomaly_purchase_orders.csv")
    substitutions = read_csv(cases_folder / "anomaly_substitution.csv")
    ground_truth = read_csv(folder / "ground_truth.csv")

    existing_ids = {row["po_id"] for row in baseline}
    baseline_uom = {
        row["sku_id"]: row["uom"] for row in baseline
    }
    capacity_by_supplier = {
        row["supplier_id"]: float(row["weekly_capacity"])
        for row in capacities
    }

    results = []

    for row in anomalies:
        issue = row["issue_type"]
        detected = False
        reason = ""

        if issue == "INBOUND_DOUBLE_COUNT":
            detected = row["po_id"] in existing_ids
            reason = "Purchase order ID already exists in baseline"

        elif issue == "SUPPLIER_CAPACITY_EXCEEDED":
            limit = capacity_by_supplier.get(row["supplier_id"])
            detected = (
                limit is not None
                and float(row["quantity"]) > limit
            )
            reason = "Order quantity exceeds supplier weekly capacity"

        elif issue == "LEAD_TIME_IGNORED":
            detected = (
                date.fromisoformat(row["expected_arrival"])
                < date.fromisoformat(row["ordered_on"])
            )
            reason = "Expected arrival is before the order date"

        elif issue == "UOM_MISMATCH":
            expected_uom = baseline_uom.get(row["sku_id"])
            detected = (
                expected_uom is not None
                and row["uom"] != expected_uom
            )
            reason = "Purchase order UOM differs from baseline SKU UOM"

        results.append({
            "case_id": row["case_id"],
            "issue_type": issue,
            "actual_decision": (
                "FLAG_FOR_REVIEW" if detected else "NOT_DETECTED"
            ),
            "reason": reason if detected else "No violation detected",
        })

    for row in substitutions:
        detected = row["approved"].lower() == "false"
        results.append({
            "case_id": row["case_id"],
            "issue_type": row["issue_type"],
            "actual_decision": (
                "FLAG_FOR_REVIEW" if detected else "NOT_DETECTED"
            ),
            "reason": (
                "Substitution not approved"
                if detected else "No violation detected"
            ),
        })

    expected = {
        row["case_id"]: row["expected_decision"]
        for row in ground_truth
    }

    for row in results:
        row["expected_decision"] = expected.get(
            row["case_id"], "UNKNOWN"
        )
        row["match"] = (
            row["actual_decision"] == row["expected_decision"]
        )

    output = cases_folder / "anomaly_validation_report.csv"

    columns = [
        "case_id", "issue_type", "actual_decision",
        "expected_decision", "match", "reason",
    ]

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)

    matched = sum(row["match"] for row in results)

    print("Anomaly validation completed.")
    print(f"Cases checked: {len(results)}")
    print(f"Ground truth matches: {matched}/{len(results)}")

    for row in sorted(results, key=lambda r: r["case_id"]):
        print(
            f'{row["case_id"]}: {row["actual_decision"]} '
            f'| Match: {row["match"]}'
        )

    print(f"Report saved: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    validate(args.input)
