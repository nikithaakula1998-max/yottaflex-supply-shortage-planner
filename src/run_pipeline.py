
import argparse
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
            "STEP 8: Run automated tests",
            [
                python, "-m", "unittest",
                "discover", "-s", "tests", "-v",
            ],
        ),
    ]

    for title, command in steps:
        run_step(title, command)

        if title.startswith("STEP 5"):
            quality_report = folder / "data_quality_report.csv"

            with quality_report.open(
                "r", encoding="utf-8"
            ) as file:
                # Header-only report means zero detected issues.
                import csv

                issues = list(csv.DictReader(file))

            if issues:
                raise RuntimeError(
                    f"Data quality validation found "
                    f"{len(issues)} issues. "
                    f"Review {quality_report}."
                )

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"Output folder: {folder}")
    print("Data quality checks: PASSED")
    print("Planning modules: COMPLETED")
    print("Automated tests: PASSED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the YottaFlex supply shortage planning pipeline"
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
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"\nPIPELINE FAILED: {error}", file=sys.stderr)
        sys.exit(1)
