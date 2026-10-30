
import argparse
import csv
import sqlite3
import tempfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


REPORT_COLUMNS = [
    "mitigation_id",
    "shortage_id",
    "sku_id",
    "location_id",
    "shortage_week",
    "supplier_id",
    "requested_quantity",
    "potential_quantity",
    "remaining_quantity",
    "estimated_potential_cost",
    "status",
    "reason",
]


def read_csv(folder, filename):
    path = Path(folder) / filename
    with path.open(
        "r", newline="", encoding="utf-8"
    ) as handle:
        return list(csv.DictReader(handle))


def week_start(value):
    year = int(value[:4])
    week = int(value[-2:])
    return date.fromisocalendar(year, week, 1)


def week_key(value):
    year, week, _ = value.isocalendar()
    return f"{year}W{week:02d}"


def is_active(row, on_date):
    return (
        date.fromisoformat(row["effective_from"])
        <= on_date
        <= date.fromisoformat(row["effective_to"])
    )


def load_rules(folder):
    suppliers = {
        row["supplier_id"]: row
        for row in read_csv(folder, "supplier.csv")
    }

    capacities = defaultdict(list)
    leads = defaultdict(list)

    for row in read_csv(folder, "supplier_capacity.csv"):
        capacities[row["supplier_id"]].append(row)

    for row in read_csv(folder, "lead_time.csv"):
        leads[row["supplier_id"]].append(row)

    supplier_skus = defaultdict(set)
    commitments = defaultdict(float)
    legacy_orders = False

    for po in read_csv(folder, "purchase_order.csv"):
        if po["status"].strip().upper() not in {
            "OPEN", "CONFIRMED"
        }:
            continue

        supplier_id = po["supplier_id"]
        supplier_skus[po["sku_id"]].add(supplier_id)

        if not po.get("expected_arrival"):
            legacy_orders = True

        arrival = (
            po.get("expected_arrival")
            or po["ordered_on"]
        )

        delivery_week = week_key(
            date.fromisoformat(arrival)
        )

        commitments[
            (supplier_id, delivery_week)
        ] += float(po["quantity"])

    return (
        suppliers,
        capacities,
        leads,
        supplier_skus,
        commitments,
        legacy_orders,
    )


def assess(
    mitigation,
    shortage,
    planning_start,
    rules,
    reserved,
):
    (
        suppliers,
        capacities,
        leads,
        supplier_skus,
        committed,
        legacy_orders,
    ) = rules

    requested = float(mitigation["quantity"])

    result = {
        "mitigation_id": mitigation["mitigation_id"],
        "shortage_id": mitigation["shortage_id"],
        "sku_id": "",
        "location_id": "",
        "shortage_week": "",
        "supplier_id": "",
        "requested_quantity": requested,
        "potential_quantity": 0,
        "remaining_quantity": requested,
        "estimated_potential_cost": 0,
        "status": "FLAG_FOR_REVIEW",
        "reason": "",
    }

    if shortage is None:
        result["reason"] = "Unknown shortage reference"
        return result

    sku_id = shortage["sku_id"]

    result["sku_id"] = sku_id
    result["location_id"] = shortage["location_id"]
    result["shortage_week"] = shortage["week"]

    if mitigation["option_type"] != "EXPEDITE_SUPPLY":
        result["reason"] = "Unsupported mitigation type"
        return result

    if requested <= 0:
        result["reason"] = "Invalid requested quantity"
        return result

    deadline = week_start(shortage["week"])
    candidates = []

    for supplier_id in sorted(
        supplier_skus.get(sku_id, ())
    ):
        supplier = suppliers.get(supplier_id)

        if not supplier:
            continue

        if supplier["status"].upper() not in {
            "ACTIVE", "APPROVED"
        }:
            continue

        active_capacities = [
            row
            for row in capacities[supplier_id]
            if is_active(row, planning_start)
        ]

        active_leads = [
            row
            for row in leads[supplier_id]
            if is_active(row, planning_start)
        ]

        if len(active_capacities) != 1:
            continue

        if len(active_leads) != 1:
            continue

        capacity = active_capacities[0]
        lead = active_leads[0]

        arrival = planning_start + timedelta(
            days=int(lead["lead_days"])
        )

        if arrival > deadline:
            continue

        # Use delivery-week capacity for modern data.
        # Older test fixtures have no arrival date.
        if legacy_orders:
            reservation_date = planning_start
        else:
            reservation_date = arrival

        key = (
            supplier_id,
            week_key(reservation_date),
        )

        available = max(
            0.0,
            float(capacity["weekly_capacity"])
            - committed[key]
            - reserved[key],
        )

        quantity = min(
            requested,
            float(shortage["shortage_qty"]),
            available,
        )

        moq = float(capacity["moq"])

        if quantity < moq or quantity <= 0:
            continue

        candidates.append(
            (quantity, supplier_id, key)
        )

    if not candidates:
        result["reason"] = (
            "No evidenced active supplier can meet "
            "normal lead time, MOQ and remaining "
            "weekly capacity; expediting requires "
            "separate confirmation"
        )
        return result

    quantity, supplier_id, key = sorted(
        candidates,
        key=lambda item: (-item[0], item[1]),
    )[0]

    reserved[key] += quantity

    result["supplier_id"] = supplier_id
    result["potential_quantity"] = round(
        quantity, 4
    )
    result["remaining_quantity"] = round(
        max(0, requested - quantity), 4
    )

    unit_cost = (
        float(mitigation["estimated_cost"])
        / requested
    )

    result["estimated_potential_cost"] = round(
        unit_cost * quantity, 2
    )

    result["status"] = (
        "POTENTIALLY_FEASIBLE_UNCONFIRMED"
    )

    result["reason"] = (
        "Passes modeled supplier capacity, MOQ "
        "and normal lead-time checks; supplier-SKU "
        "qualification and delivery still "
        "require confirmation"
    )

    return result


def evaluate_to_file(
    folder,
    output,
    batch_size=20000,
):
    folder = Path(folder)
    rules = load_rules(folder)

    reserved = defaultdict(float)
    counts = defaultdict(int)

    with tempfile.TemporaryDirectory(
        prefix="mitigation_sqlite_"
    ) as temporary:
        database_path = (
            Path(temporary) / "mitigations.sqlite3"
        )

        db = sqlite3.connect(str(database_path))

        try:
            db.execute("PRAGMA journal_mode=OFF")
            db.execute("PRAGMA synchronous=OFF")

            db.execute(
                """
                CREATE TABLE shortages (
                    id TEXT PRIMARY KEY,
                    sku TEXT,
                    location TEXT,
                    week TEXT,
                    qty TEXT,
                    priority REAL
                )
                """
            )

            db.execute(
                """
                CREATE TABLE mitigations (
                    id TEXT PRIMARY KEY,
                    shortage_id TEXT,
                    type TEXT,
                    qty TEXT,
                    cost TEXT
                )
                """
            )

            earliest = None
            batch = []

            with (
                folder / "shortage.csv"
            ).open(
                "r",
                newline="",
                encoding="utf-8",
            ) as handle:
                reader = csv.DictReader(handle)

                for row in reader:
                    current = week_start(row["week"])

                    if earliest is None or current < earliest:
                        earliest = current

                    batch.append(
                        (
                            row["shortage_id"],
                            row["sku_id"],
                            row["location_id"],
                            row["week"],
                            row["shortage_qty"],
                            float(
                                row.get("priority_score")
                                or 0
                            ),
                        )
                    )

                    if len(batch) >= batch_size:
                        db.executemany(
                            """
                            INSERT INTO shortages
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            batch,
                        )
                        batch.clear()

                if batch:
                    db.executemany(
                        """
                        INSERT INTO shortages
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        batch,
                    )

            if earliest is None:
                raise ValueError(
                    "shortage.csv has no shortage records"
                )

            print(
                "Shortage records indexed.",
                flush=True,
            )

            batch.clear()

            with (
                folder / "mitigation_option.csv"
            ).open(
                "r",
                newline="",
                encoding="utf-8",
            ) as handle:
                reader = csv.DictReader(handle)

                for row in reader:
                    batch.append(
                        (
                            row["mitigation_id"],
                            row["shortage_id"],
                            row["option_type"],
                            row["quantity"],
                            row["estimated_cost"],
                        )
                    )

                    if len(batch) >= batch_size:
                        db.executemany(
                            """
                            INSERT INTO mitigations
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            batch,
                        )
                        batch.clear()

                if batch:
                    db.executemany(
                        """
                        INSERT INTO mitigations
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        batch,
                    )

            db.execute(
                """
                CREATE INDEX mitigation_shortage_idx
                ON mitigations(shortage_id)
                """
            )

            db.commit()

            print(
                "Mitigation records indexed. "
                "Starting feasibility checks...",
                flush=True,
            )

            query = """
                SELECT
                    m.id,
                    m.shortage_id,
                    m.type,
                    m.qty,
                    m.cost,
                    s.sku,
                    s.location,
                    s.week,
                    s.qty,
                    s.priority
                FROM mitigations m
                LEFT JOIN shortages s
                    ON s.id = m.shortage_id
                ORDER BY
                    COALESCE(s.priority, 0) DESC,
                    m.id ASC
            """

            with Path(output).open(
                "w",
                newline="",
                encoding="utf-8",
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=REPORT_COLUMNS,
                )
                writer.writeheader()

                for index, values in enumerate(
                    db.execute(query),
                    start=1,
                ):
                    (
                        mitigation_id,
                        shortage_id,
                        option_type,
                        quantity,
                        estimated_cost,
                        sku,
                        location,
                        week,
                        shortage_qty,
                        priority,
                    ) = values

                    mitigation = {
                        "mitigation_id": mitigation_id,
                        "shortage_id": shortage_id,
                        "option_type": option_type,
                        "quantity": quantity,
                        "estimated_cost": estimated_cost,
                    }

                    shortage = None

                    if sku is not None:
                        shortage = {
                            "sku_id": sku,
                            "location_id": location,
                            "week": week,
                            "shortage_qty": shortage_qty,
                            "priority_score": priority,
                        }

                    result = assess(
                        mitigation,
                        shortage,
                        earliest,
                        rules,
                        reserved,
                    )

                    writer.writerow(result)
                    counts[result["status"]] += 1

                    if index % 1000000 == 0:
                        print(
                            "Mitigation options processed: "
                            f"{index:,}",
                            flush=True,
                        )
        finally:
            db.close()

    return counts


def evaluate_mitigations(folder):
    # Preserve the existing function used by
    # the five mitigation unit tests.
    with tempfile.TemporaryDirectory(
        prefix="mitigation_test_"
    ) as temporary:
        output = Path(temporary) / "report.csv"

        evaluate_to_file(folder, output)

        with output.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as handle:
            results = list(csv.DictReader(handle))

        numeric_fields = (
            "requested_quantity",
            "potential_quantity",
            "remaining_quantity",
            "estimated_potential_cost",
        )

        for row in results:
            for field in numeric_fields:
                row[field] = float(row[field])

        return sorted(
            results,
            key=lambda row: row["mitigation_id"],
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate shortage mitigation feasibility"
        )
    )

    parser.add_argument(
        "--input",
        default="outputs/pipeline_test_01",
        help="Folder containing generated CSV files",
    )

    args = parser.parse_args()

    folder = Path(args.input)
    report = folder / "mitigation_feasibility_report.csv"

    counts = evaluate_to_file(folder, report)

    print(
        "Mitigation feasibility evaluation completed."
    )
    print(
        f"Options checked: {sum(counts.values()):,}"
    )

    for status, count in sorted(counts.items()):
        print(f"{status}: {count:,}")

    print(f"Report saved: {report}")

    print(
        "Important: Potential feasibility is not "
        "supplier approval or a guaranteed delivery."
    )


if __name__ == "__main__":
    main()
