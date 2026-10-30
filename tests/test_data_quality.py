
import csv
import tempfile
import unittest
from pathlib import Path

from src.data_quality_validator import validate_data


class DataQualityTests(unittest.TestCase):

    def write_csv(self, folder, filename, columns, rows):
        with (folder / filename).open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def test_detects_duplicate_sku(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)

            self.write_csv(
                folder,
                "sku.csv",
                ["sku_id", "name", "uom", "unit_cost"],
                [
                    {
                        "sku_id": "SKU-001",
                        "name": "Product A",
                        "uom": "EA",
                        "unit_cost": "10",
                    },
                    {
                        "sku_id": "SKU-001",
                        "name": "Product B",
                        "uom": "EA",
                        "unit_cost": "20",
                    },
                ],
            )

            errors = validate_data(folder)

            self.assertTrue(
                any(
                    error["file"] == "sku.csv"
                    and error["issue"] == "DUPLICATE_KEY"
                    for error in errors
                )
            )

    def test_detects_negative_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)

            self.write_csv(
                folder,
                "inventory.csv",
                [
                    "inventory_id",
                    "sku_id",
                    "location_id",
                    "as_of_date",
                    "on_hand",
                    "uom",
                ],
                [
                    {
                        "inventory_id": "INV-001",
                        "sku_id": "SKU-001",
                        "location_id": "LOC-001",
                        "as_of_date": "2026-01-01",
                        "on_hand": "-50",
                        "uom": "EA",
                    }
                ],
            )

            errors = validate_data(folder)

            self.assertTrue(
                any(
                    error["file"] == "inventory.csv"
                    and error["issue"] == "INVALID_QUANTITY"
                    for error in errors
                )
            )

    def test_detects_invalid_week(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)

            self.write_csv(
                folder,
                "forecast_demand.csv",
                [
                    "demand_id",
                    "sku_id",
                    "location_id",
                    "week",
                    "quantity",
                    "uom",
                ],
                [
                    {
                        "demand_id": "DEM-001",
                        "sku_id": "SKU-001",
                        "location_id": "LOC-001",
                        "week": "2026W99",
                        "quantity": "10",
                        "uom": "EA",
                    }
                ],
            )

            errors = validate_data(folder)

            self.assertTrue(
                any(
                    error["file"] == "forecast_demand.csv"
                    and error["issue"] == "INVALID_WEEK"
                    for error in errors
                )
            )


if __name__ == "__main__":
    unittest.main()
