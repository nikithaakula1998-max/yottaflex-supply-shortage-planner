
import csv
import tempfile
import unittest
from pathlib import Path

from src.mitigation_validator import evaluate_mitigations


class MitigationFeasibilityTests(unittest.TestCase):

    def write_csv(self, folder, filename, columns, rows):
        with (folder / filename).open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def create_data(
        self,
        folder,
        requested=20,
        capacity=100,
        moq=10,
        lead_days=7,
        existing_order=10,
        two_mitigations=False,
    ):
        # Earlier shortage establishes the simulated planning date.
        # No mitigation is created for this record.
        shortages = [
            {
                "shortage_id": "SHORT-PLANNING-START",
                "sku_id": "SKU-OTHER",
                "location_id": "LOC-001",
                "week": "2026W02",
                "shortage_qty": "1",
                "priority_score": "0",
            },
            {
                "shortage_id": "SHORT-001",
                "sku_id": "SKU-001",
                "location_id": "LOC-001",
                "week": "2026W06",
                "shortage_qty": "50",
                "priority_score": "100",
            },
        ]

        mitigations = [
            {
                "mitigation_id": "MIT-001",
                "shortage_id": "SHORT-001",
                "option_type": "EXPEDITE_SUPPLY",
                "quantity": str(requested),
                "estimated_cost": "200",
            }
        ]

        if two_mitigations:
            shortages.append(
                {
                    "shortage_id": "SHORT-002",
                    "sku_id": "SKU-001",
                    "location_id": "LOC-001",
                    "week": "2026W06",
                    "shortage_qty": "50",
                    "priority_score": "90",
                }
            )

            mitigations.append(
                {
                    "mitigation_id": "MIT-002",
                    "shortage_id": "SHORT-002",
                    "option_type": "EXPEDITE_SUPPLY",
                    "quantity": str(requested),
                    "estimated_cost": "200",
                }
            )

        self.write_csv(
            folder,
            "shortage.csv",
            [
                "shortage_id",
                "sku_id",
                "location_id",
                "week",
                "shortage_qty",
                "priority_score",
            ],
            shortages,
        )

        self.write_csv(
            folder,
            "mitigation_option.csv",
            [
                "mitigation_id",
                "shortage_id",
                "option_type",
                "quantity",
                "estimated_cost",
            ],
            mitigations,
        )

        self.write_csv(
            folder,
            "supplier.csv",
            ["supplier_id", "status"],
            [
                {
                    "supplier_id": "SUP-001",
                    "status": "ACTIVE",
                }
            ],
        )

        self.write_csv(
            folder,
            "purchase_order.csv",
            [
                "po_id",
                "sku_id",
                "supplier_id",
                "quantity",
                "ordered_on",
                "status",
            ],
            [
                {
                    "po_id": "PO-001",
                    "sku_id": "SKU-001",
                    "supplier_id": "SUP-001",
                    "quantity": str(existing_order),
                    "ordered_on": "2026-01-05",
                    "status": "OPEN",
                }
            ],
        )

        self.write_csv(
            folder,
            "supplier_capacity.csv",
            [
                "supplier_id",
                "weekly_capacity",
                "moq",
                "effective_from",
                "effective_to",
            ],
            [
                {
                    "supplier_id": "SUP-001",
                    "weekly_capacity": str(capacity),
                    "moq": str(moq),
                    "effective_from": "2026-01-01",
                    "effective_to": "2026-12-31",
                }
            ],
        )

        self.write_csv(
            folder,
            "lead_time.csv",
            [
                "supplier_id",
                "lead_days",
                "effective_from",
                "effective_to",
            ],
            [
                {
                    "supplier_id": "SUP-001",
                    "lead_days": str(lead_days),
                    "effective_from": "2026-01-01",
                    "effective_to": "2026-12-31",
                }
            ],
        )

    def test_normal_feasible_mitigation(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.create_data(folder)

            results = evaluate_mitigations(folder)

            self.assertEqual(
                results[0]["status"],
                "POTENTIALLY_FEASIBLE_UNCONFIRMED",
            )
            self.assertEqual(
                results[0]["potential_quantity"],
                20,
            )
            self.assertEqual(
                results[0]["remaining_quantity"],
                0,
            )

    def test_lead_time_blocks_mitigation(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.create_data(
                folder,
                lead_days=30,
            )

            results = evaluate_mitigations(folder)

            self.assertEqual(
                results[0]["status"],
                "FLAG_FOR_REVIEW",
            )
            self.assertEqual(
                results[0]["potential_quantity"],
                0,
            )

    def test_moq_blocks_small_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.create_data(
                folder,
                requested=5,
                moq=10,
            )

            results = evaluate_mitigations(folder)

            self.assertEqual(
                results[0]["status"],
                "FLAG_FOR_REVIEW",
            )

    def test_capacity_limits_quantity(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.create_data(
                folder,
                requested=50,
                capacity=30,
                existing_order=10,
            )

            results = evaluate_mitigations(folder)

            # Capacity 30 minus existing order 10 = 20.
            self.assertEqual(
                results[0]["potential_quantity"],
                20,
            )
            self.assertEqual(
                results[0]["remaining_quantity"],
                30,
            )

    def test_capacity_reserved_across_mitigations(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.create_data(
                folder,
                requested=20,
                capacity=40,
                existing_order=10,
                two_mitigations=True,
            )

            results = evaluate_mitigations(folder)

            # Capacity 40 minus existing order 10 = 30.
            # First mitigation gets 20, second gets 10.
            self.assertEqual(
                sum(
                    row["potential_quantity"]
                    for row in results
                ),
                30,
            )
            self.assertEqual(
                results[0]["potential_quantity"],
                20,
            )
            self.assertEqual(
                results[1]["potential_quantity"],
                10,
            )


if __name__ == "__main__":
    unittest.main()
