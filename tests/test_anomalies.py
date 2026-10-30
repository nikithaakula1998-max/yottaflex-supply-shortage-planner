
import csv
import tempfile
import unittest
from pathlib import Path

from src.anomaly_generator import generate_anomalies
from src.anomaly_validator import validate


class AnomalyTests(unittest.TestCase):

    def test_five_anomaly_scenarios(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)

            def write_csv(filename, columns, rows):
                with (folder / filename).open(
                    "w", newline="", encoding="utf-8"
                ) as f:
                    writer = csv.DictWriter(f, fieldnames=columns)
                    writer.writeheader()
                    writer.writerows(rows)

            write_csv(
                "purchase_order.csv",
                [
                    "po_id", "sku_id", "location_id",
                    "supplier_id", "quantity", "ordered_on",
                    "expected_arrival", "status", "uom"
                ],
                [{
                    "po_id": "PO-001",
                    "sku_id": "SKU-001",
                    "location_id": "LOC-001",
                    "supplier_id": "SUP-001",
                    "quantity": "20",
                    "ordered_on": "2026-01-01",
                    "expected_arrival": "2026-01-15",
                    "status": "OPEN",
                    "uom": "EA",
                }],
            )

            write_csv(
                "supplier_capacity.csv",
                [
                    "capacity_id", "supplier_id", "weekly_capacity",
                    "moq", "effective_from", "effective_to"
                ],
                [{
                    "capacity_id": "CAP-001",
                    "supplier_id": "SUP-001",
                    "weekly_capacity": "100",
                    "moq": "10",
                    "effective_from": "2026-01-01",
                    "effective_to": "2027-01-01",
                }],
            )

            issue_types = [
                "INBOUND_DOUBLE_COUNT",
                "UNAPPROVED_SUBSTITUTE",
                "SUPPLIER_CAPACITY_EXCEEDED",
                "LEAD_TIME_IGNORED",
                "UOM_MISMATCH",
            ]

            write_csv(
                "ground_truth.csv",
                [
                    "case_id", "issue_type",
                    "expected_decision", "description"
                ],
                [
                    {
                        "case_id": f"CASE-{i:03d}",
                        "issue_type": issue,
                        "expected_decision": "FLAG_FOR_REVIEW",
                        "description": "Synthetic test case",
                    }
                    for i, issue in enumerate(issue_types, start=1)
                ],
            )

            generate_anomalies(folder)
            validate(folder)

            report_path = (
                folder / "anomaly_cases"
                / "anomaly_validation_report.csv"
            )

            with report_path.open(
                "r", newline="", encoding="utf-8"
            ) as f:
                results = list(csv.DictReader(f))

            self.assertEqual(len(results), 5)
            self.assertEqual(
                {r["issue_type"] for r in results},
                set(issue_types),
            )

            for result in results:
                self.assertEqual(
                    result["actual_decision"],
                    "FLAG_FOR_REVIEW",
                )
                self.assertEqual(result["match"], "True")


if __name__ == "__main__":
    unittest.main()
