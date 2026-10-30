
from collections import defaultdict
from datetime import date


def validate_purchase_orders(purchase_orders, capacities, lead_times):
    """Find supplier capacity and lead-time violations."""
    issues = []

    capacity_by_supplier = {
        row["supplier_id"]: int(row["weekly_capacity"])
        for row in capacities
    }

    lead_by_supplier = {
        row["supplier_id"]: int(row["lead_days"])
        for row in lead_times
    }

    weekly_orders = defaultdict(int)

    for order in purchase_orders:
        supplier_id = order["supplier_id"]
        ordered_on = date.fromisoformat(order["ordered_on"])
        arrival = date.fromisoformat(order["expected_arrival"])
        quantity = int(order["quantity"])

        actual_days = (arrival - ordered_on).days
        required_days = lead_by_supplier.get(supplier_id)

        if required_days is None:
            issues.append({
                "po_id": order["po_id"],
                "issue": "MISSING_LEAD_TIME"
            })
        elif actual_days < required_days:
            issues.append({
                "po_id": order["po_id"],
                "issue": "LEAD_TIME_VIOLATION"
            })

        if supplier_id not in capacity_by_supplier:
            issues.append({
                "po_id": order["po_id"],
                "issue": "MISSING_CAPACITY"
            })

        year, week, _ = arrival.isocalendar()
        weekly_orders[(supplier_id, year, week)] += quantity

    for (supplier_id, year, week), total in weekly_orders.items():
        capacity = capacity_by_supplier.get(supplier_id)

        if capacity is not None and total > capacity:
            issues.append({
                "supplier_id": supplier_id,
                "week": f"{year}W{week:02d}",
                "issue": "SUPPLIER_CAPACITY_EXCEEDED",
                "ordered_quantity": total,
                "weekly_capacity": capacity
            })

    return issues
