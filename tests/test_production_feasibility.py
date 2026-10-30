
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

    def read_report(self, folder):
        with (folder / "cumulative_bom_report.csv").open(
            newline="", encoding="utf-8"
        ) as file:
            return list(csv.DictReader(file))

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
            report = self.read_report(folder)

            self.assertEqual(len(report), 2)

            self.assertEqual(
                report[0]["status"], "PARTIALLY_FEASIBLE"
            )
            self.assertEqual(
                float(report[0]["feasible_quantity"]), 6
            )
            self.assertEqual(
                float(report[0]["unfulfilled_quantity"]), 4
            )

            self.assertEqual(
                report[1]["status"], "COMPONENT_SHORTAGE"
            )
            self.assertEqual(
                float(report[1]["feasible_quantity"]), 0
            )
            self.assertEqual(
                float(report[1]["unfulfilled_quantity"]), 5
            )

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

    def test_delivery_arrives_after_first_production(self):
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
                        "on_hand": "0",
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
                        "planned_quantity": "5",
                    },
                    {
                        "production_id": "PROD-002",
                        "sku_id": "PRODUCT-001",
                        "location_id": "LOC-001",
                        "week": "2026W02",
                        "planned_quantity": "5",
                    },
                    {
                        "production_id": "PROD-003",
                        "sku_id": "PRODUCT-001",
                        "location_id": "LOC-001",
                        "week": "2026W03",
                        "planned_quantity": "5",
                    },
                ],
            )

            self.write_csv(
                folder,
                "purchase_order.csv",
                [
                    "po_id",
                    "sku_id",
                    "location_id",
                    "supplier_id",
                    "quantity",
                    "ordered_on",
                    "expected_arrival",
                    "status",
                    "uom",
                ],
                [
                    {
                        "po_id": "PO-001",
                        "sku_id": "COMP-001",
                        "location_id": "LOC-001",
                        "supplier_id": "SUP-001",
                        "quantity": "10",
                        "ordered_on": "2025-12-22",
                        "expected_arrival": "2026-01-05",
                        "status": "OPEN",
                        "uom": "EA",
                    }
                ],
            )

            self.write_csv(
                folder,
                "supplier_capacity.csv",
                ["supplier_id", "weekly_capacity"],
                [
                    {
                        "supplier_id": "SUP-001",
                        "weekly_capacity": "100",
                    }
                ],
            )

            self.write_csv(
                folder,
                "lead_time.csv",
                ["supplier_id", "lead_days"],
                [
                    {
                        "supplier_id": "SUP-001",
                        "lead_days": "7",
                    }
                ],
            )

            validate_cumulative_bom(folder)
            report = self.read_report(folder)

            self.assertEqual(len(report), 3)

            # Week 1: components have not arrived yet.
            self.assertEqual(
                float(report[0]["feasible_quantity"]), 0
            )

            # Week 2: delivery supports five finished units.
            self.assertEqual(
                float(report[1]["feasible_quantity"]), 5
            )

            # Week 3: delivered stock has already been consumed.
            self.assertEqual(
                float(report[2]["feasible_quantity"]), 0
            )

    def test_shared_weekly_factory_capacity(self):
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
                        "on_hand": "500",
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
                        "quantity_per_unit": "1",
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
                        "planned_quantity": "70",
                    },
                    {
                        "production_id": "PROD-002",
                        "sku_id": "PRODUCT-001",
                        "location_id": "LOC-001",
                        "week": "2026W01",
                        "planned_quantity": "70",
                    },
                ],
            )

            self.write_csv(
                folder,
                "production_capacity.csv",
                [
                    "location_id",
                    "week",
                    "max_production_units",
                ],
                [
                    {
                        "location_id": "LOC-001",
                        "week": "2026W01",
                        "max_production_units": "100",
                    }
                ],
            )

            validate_cumulative_bom(folder)
            report = self.read_report(folder)

            self.assertEqual(len(report), 2)

            # First order uses 70 of the 100 available units.
            self.assertEqual(
                float(report[0]["feasible_quantity"]), 70
            )

            # Second order can use only the remaining 30.
            self.assertEqual(
                float(report[1]["feasible_quantity"]), 30
            )

            self.assertEqual(
                report[1]["status"], "PARTIALLY_FEASIBLE"
            )

            total_feasible = sum(
                float(row["feasible_quantity"]) for row in report
            )

            self.assertEqual(total_feasible, 100)

            total_planned = sum(
                float(row["planned_quantity"]) for row in report
            )
            total_unfulfilled = sum(
                float(row["unfulfilled_quantity"]) for row in report
            )

            self.assertEqual(total_planned, 140)
            self.assertEqual(total_unfulfilled, 40)
            self.assertEqual(
                total_planned,
                total_feasible + total_unfulfilled,
            )


if __name__ == "__main__":
    unittest.main()
