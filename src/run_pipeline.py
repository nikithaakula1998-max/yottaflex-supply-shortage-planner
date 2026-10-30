
import argparse
import csv
import subprocess
import sys
from pathlib import Path


def run_step(title, command):
    print("\n" + "=" * 60, flush=True)
    print(title, flush=True)
    print("=" * 60, flush=True)
    print("Command:", " ".join(command), flush=True)

    subprocess.run(
        command,
        check=True,
    )


def check_data_quality(folder):
    quality_report = folder / "data_quality_report.csv"

    if not quality_report.exists():
        raise RuntimeError(
            f"Data quality report was not created: {quality_report}"
        )

    with quality_report.open(
        "r", newline="", encoding="utf-8"
    ) as file:
        issues = list(csv.DictReader(file))

    if issues:
        raise RuntimeError(
            f"Data quality validation found {len(issues)} issues. "
            f"Review {quality_report}."
        )

    print("Data quality verification: PASSED", flush=True)


def check_mitigation_report(folder):
    report = folder / "mitigation_feasibility_report.csv"
    source = folder / "mitigation_option.csv"

    if not report.exists():
        raise RuntimeError(
            f"Mitigation feasibility report was not created: {report}"
        )

    with source.open(
        "r", newline="", encoding="utf-8"
    ) as file:
        source_options = list(csv.DictReader(file))

    with report.open(
        "r", newline="", encoding="utf-8"
    ) as file:
        results = list(csv.DictReader(file))

    if len(results) != len(source_options):
        raise RuntimeError(
            "Mitigation report row count does not match "
            "the number of generated mitigation options."
        )

    allowed_statuses = {
        "FLAG_FOR_REVIEW",
        "POTENTIALLY_FEASIBLE_UNCONFIRMED",
    }

    for row in results:
        if row["status"] not in allowed_statuses:
            raise RuntimeError(
                "Unexpected mitigation status for "
                f"{row['mitigation_id']}: {row['status']}"
            )

        requested = float(row["requested_quantity"])
        potential = float(row["potential_quantity"])
        remaining = float(row["remaining_quantity"])

        if requested < 0 or potential < 0 or remaining < 0:
            raise RuntimeError(
                "Negative mitigation quantity found for "
                f"{row['mitigation_id']}"
            )

        if abs((potential + remaining) - requested) > 0.0001:
            raise RuntimeError(
                "Mitigation quantities do not reconcile for "
                f"{row['mitigation_id']}"
            )

        if (
            row["status"] == "FLAG_FOR_REVIEW"
            and potential > 0
        ):
            raise RuntimeError(
                "A flagged mitigation has potential quantity "
                f"greater than zero: {row['mitigation_id']}"
            )

    potentially_feasible = sum(
        row["status"] == "POTENTIALLY_FEASIBLE_UNCONFIRMED"
        for row in results
    )

    flagged = sum(
        row["status"] == "FLAG_FOR_REVIEW"
        for row in results
    )

    print("\nMitigation report verification: PASSED")
    print(f"Mitigation options checked: {len(results)}")
    print(f"Potentially feasible (unconfirmed): {potentially_feasible}")
    print(f"Flagged for review: {flagged}")
    print(
        "Note: Potential feasibility does not guarantee "
        "supplier approval or delivery."
    )


def run_pipeline(output_folder, capacity):
    folder = Path(output_folder)

    if folder.exists() and any(folder.iterdir()):
        raise ValueError(
            f"Output folder is not empty: {folder}\n"
            "Choose a new folder to avoid overwriting existing data."
        )

    folder.mkdir(parents=True, exist_ok=True)

    python = sys.executable
    output = str(folder)

    steps = [
        (
            "STEP 1: Generate synthetic supply-chain data",
            [
                python, "-m", "src.main",
                "--out", output,
            ],
        ),
        (
            "STEP 2: Generate production proposals",
            [
                python, "-m", "src.production_planner",
                "--input", output,
            ],
        ),
        (
            "STEP 3: Generate bill of materials",
            [
                python, "-m", "src.bom_generator",
                "--input", output,
            ],
        ),
        (
            "STEP 4: Generate weekly factory capacity",
            [
                python, "-m", "src.production_capacity_generator",
                "--input", output,
                "--capacity", str(capacity),
            ],
        ),
        (
            "STEP 5: Validate source data quality",
            [
                python, "-m", "src.data_quality_validator",
                "--input", output,
            ],
        ),
        (
            "STEP 6: Validate suppliers and calculate shortages",
            [
                python, "-m", "src.feasible_planner",
                "--input", output,
            ],
        ),
        (
            "STEP 7: Check cumulative BOM and factory capacity",
            [
                python, "-m", "src.cumulative_bom_validator",
                "--input", output,
            ],
        ),
        (
            "STEP 8: Evaluate shortage mitigation feasibility",
            [
                python, "-m", "src.mitigation_validator",
                "--input", output,
            ],
        ),
        (
            "STEP 9: Run automated tests",
            [
                python, "-m", "unittest",
                "discover", "-s", "tests", "-v",
            ],
        ),
    ]

    for step_number, (title, command) in enumerate(
        steps, start=1
    ):
        run_step(title, command)

        if step_number == 5:
            check_data_quality(folder)

        if step_number == 8:
            check_mitigation_report(folder)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)

    print(f"Output folder: {folder}")
    print("Data quality checks: PASSED")
    print("Supplier and shortage planning: COMPLETED")
    print("BOM and production capacity checks: COMPLETED")
    print("Mitigation feasibility evaluation: COMPLETED")
    print("Automated tests: PASSED")
    print(
        "Important: Mitigation candidates remain "
        "unconfirmed until supplier verification."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Run the YottaFlex supply shortage planning pipeline"
        )
    )

    parser.add_argument(
        "--out",
        default="outputs/pipeline_run",
        help="New output folder for this run",
    )

    parser.add_argument(
        "--capacity",
        type=int,
        default=100,
        help="Weekly production capacity per location",
    )

    args = parser.parse_args()

    if args.capacity < 0:
        parser.error("--capacity must be zero or greater")

    try:
        run_pipeline(args.out, args.capacity)

    except (
        RuntimeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as error:
        print(
            f"\nPIPELINE FAILED: {error}",
            file=sys.stderr,
        )
        sys.exit(1)
