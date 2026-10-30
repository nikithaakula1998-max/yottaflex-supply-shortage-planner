
import csv
import tempfile
import unittest
from pathlib import Path

from src.cumulative_bom_validator import validate_cumulative_bom


class ProductionFeasibilityTests(unittest.TestCase):

    def write_csv(self, folder, filename, fieldnames, rows):
        path = folder / filename

        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_partial_production_and_stock_reservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)

            self.write_csv(
                folder,
                "inventory.csv",
                ["sku_id", "location_id", "on_hand"],
                [
                    {
                        "sku_id": "COMP-001",
                        "location_id": "LOC-001",
                        "on_hand": "12",
                    }
                ],
            )

            self.write_csv(
                folder,
                "bom.csv",
                [
                    "parent_sku_id",
                    "component_sku_id",
                    "quantity_per_unit",
                    "status",
                ],
                [
                    {
                        "parent_sku_id": "PRODUCT-001",
                        "component_sku_id": "COMP-001",
                        "quantity_per_unit": "2",
                        "status": "ACTIVE",
                    }
                ],
            )

            self.write_csv(
                folder,
                "production_plan.csv",
                [
                    "production_id",
                    "sku_id",
                    "location_id",
                    "week",
                    "planned_quantity",
                ],
                [
                    {
                        "production_id": "PROD-001",
                        "sku_id": "PRODUCT-001",
                        "location_id": "LOC-001",
                        "week": "2026W01",
                        "planned_quantity": "10",
                    },
                    {
                        "production_id": "PROD-002",
                        "sku_id": "PRODUCT-001",
                        "location_id": "LOC-001",
                        "week": "2026W02",
                        "planned_quantity": "5",
                    },
                ],
            )

            validate_cumulative_bom(folder)

            with (folder / "cumulative_bom_report.csv").open(
                newline="", encoding="utf-8"
            ) as file:
                report = list(csv.DictReader(file))

            self.assertEqual(len(report), 2)

            first = report[0]
            self.assertEqual(first["status"], "PARTIALLY_FEASIBLE")
            self.assertEqual(float(first["feasible_quantity"]), 6)
            self.assertEqual(float(first["unfulfilled_quantity"]), 4)

            second = report[1]
            self.assertEqual(second["status"], "COMPONENT_SHORTAGE")
            self.assertEqual(float(second["feasible_quantity"]), 0)
            self.assertEqual(float(second["unfulfilled_quantity"]), 5)

            total_planned = sum(
                float(row["planned_quantity"]) for row in report
            )
            total_feasible = sum(
                float(row["feasible_quantity"]) for row in report
            )
            total_unfulfilled = sum(
                float(row["unfulfilled_quantity"]) for row in report
            )

            self.assertEqual(
                total_planned,
                total_feasible + total_unfulfilled,
            )


if __name__ == "__main__":
    unittest.main()
