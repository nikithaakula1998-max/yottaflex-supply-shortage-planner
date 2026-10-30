
import unittest

from src.validators import validate_purchase_orders


class SupplierValidationTests(unittest.TestCase):

    def test_lead_time_violation(self):
        orders = [{
            "po_id": "PO-001",
            "supplier_id": "SUP-001",
            "ordered_on": "2026-10-01",
            "expected_arrival": "2026-10-05",
            "quantity": 50
        }]

        capacities = [{
            "supplier_id": "SUP-001",
            "weekly_capacity": 100
        }]

        lead_times = [{
            "supplier_id": "SUP-001",
            "lead_days": 14
        }]

        issues = validate_purchase_orders(
            orders, capacities, lead_times
        )

        self.assertTrue(
            any(
                issue["issue"] == "LEAD_TIME_VIOLATION"
                for issue in issues
            )
        )

    def test_supplier_capacity_violation(self):
        orders = [{
            "po_id": "PO-002",
            "supplier_id": "SUP-001",
            "ordered_on": "2026-10-01",
            "expected_arrival": "2026-10-20",
            "quantity": 150
        }]

        capacities = [{
            "supplier_id": "SUP-001",
            "weekly_capacity": 100
        }]

        lead_times = [{
            "supplier_id": "SUP-001",
            "lead_days": 14
        }]

        issues = validate_purchase_orders(
            orders, capacities, lead_times
        )

        self.assertTrue(
            any(
                issue["issue"] == "SUPPLIER_CAPACITY_EXCEEDED"
                for issue in issues
            )
        )


if __name__ == "__main__":
    unittest.main()
