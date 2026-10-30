
# YottaFlex Supply Shortage Planner

A Python-based synthetic supply-chain planning project developed for the YottaFlex Associate AI Forward Deployed Engineer hiring challenge.

## Project Status

Partial implementation with working data generation, validation, BOM checks, production proposals, and controlled anomaly scenarios.

The project does not yet satisfy every challenge requirement.

## Objective

Generate realistic synthetic supply-chain data, identify inventory shortages, evaluate planning constraints, and demonstrate how invalid supply decisions can be detected.

## Technology

- Python 3.10+
- Python standard library
- CSV and JSON
- Git and GitHub
- unittest

No third-party Python packages are required for the current implementation.

## Implemented Features

### 1. Synthetic Data Generation

The main generator produces supply-chain records including:

- SKUs and locations
- Suppliers
- Supplier capacities
- Lead times
- Forecast demand
- Inventory
- Purchase orders
- Shortages
- Mitigation candidates

The data is generated using a deterministic random seed.

### 2. Large-Scale Demand Generation

A separate streaming generator supports producing weekly demand rows without keeping the entire dataset in memory.

A run covering 3,000 SKUs, 50 locations, and 52 weeks generated 7,800,000 demand records.

This does not mean the entire supply-chain dataset has been generated and validated at that scale.

### 3. Supplier Validation

The supplier validation logic includes checks for:

- Lead-time violations
- Supplier capacity violations

Additional supplier eligibility, lifecycle, and effective-date constraints require further work.

### 4. Production Planning

The production planner creates proposed production quantities based on forecast demand.

These proposals are marked PROPOSED_UNVERIFIED and should not be interpreted as fully executable production schedules.

### 5. Bill of Materials (BOM)

The project includes BOM generation and validation.

The cumulative BOM validator checks component availability across successive production proposals, deducting component stock for proposals that pass its checks.

Example results from the starter dataset:

- Production proposals checked: 1,200
- Component shortages: 744
- Component stock available: 216
- No active BOM: 240

The cumulative validator uses initial component inventory only. It does not currently incorporate inbound replenishment, external component demand, production capacity, or all BOM effective-date constraints.

### 6. Anomaly Scenarios

Five controlled synthetic scenarios are supported:

1. Inbound double counting
2. Unapproved substitution
3. Supplier capacity exceeded
4. Lead time ignored
5. Unit-of-measure mismatch

The anomaly generator creates separate test records without modifying baseline supply-chain tables.

The anomaly validator checks these controlled scenarios against expected decisions.

All five generated scenarios matched their ground-truth decisions in the latest local run.

These checks are scenario-specific and do not constitute comprehensive anomaly detection across all production data.

## Running the Project

Open PowerShell in the project root.

Generate a small dataset:

```powershell
py -m src.main --out outputs/sample
```

Run automated tests:

```powershell
py -m unittest discover -s tests -v
```

Generate controlled anomaly scenarios for an existing dataset:

```powershell
py -m src.anomaly_generator --input outputs/my_first_run
```

Validate those scenarios:

```powershell
py -m src.anomaly_validator --input outputs/my_first_run
```

Run cumulative BOM validation after the required inventory, BOM, and production-plan files have been generated:

```powershell
py -m src.cumulative_bom_validator --input outputs/my_first_run
```

Note: The `outputs/my_first_run` folder is a local example. Replace it with the path to your own generated dataset.

Do not run the original in-memory generator at the full 3,000-SKU scale on memory-constrained machines.

## Testing

Run:

```powershell
py -m unittest discover -s tests -v
```

Latest verified local result:

- 5 automated tests passed
- 5 controlled anomaly scenarios matched expected decisions

## Known Limitations

- Full-scale end-to-end supply-chain generation is not yet demonstrated.
- Mitigation candidates are not fully validated or policy-approved.
- Production proposals are not capacity-verified.
- Cumulative BOM validation does not account for inbound component replenishment.
- Supplier-specific SKU eligibility and complete lifecycle enforcement are incomplete.
- Comprehensive PK/FK, duplicate, and UOM validation is incomplete.
- Complete SQL exports, data dictionary, and evaluation metrics are not yet delivered.
- Controlled anomaly scenarios are separate from baseline data.

## Reproducibility

The generator uses deterministic seeded randomness.

Repeated runs with the same configuration can be checked using the output manifest and generated data.

## Data Provenance

All generated data is synthetic. No third-party dataset is used.

## AI Assistance Disclosure

AI assistance was used during development for code generation, debugging, documentation, and test design.

Development prompts and interactions should be documented in `prompts/prompt_history.md`.

The project should be reviewed and tested before submission.

## Repository

https://github.com/nikithaakula1998-max/yottaflex-supply-shortage-planner


## Supplier Constraint Experiment

A controlled negative test was performed using a separate copy of the generated dataset.

- Baseline purchase order quantity: 72 units.
- Modified test purchase order quantity: 1,000,000 units.
- Purchase orders checked: 100.
- Validation issues detected: 1.
- Planning rows evaluated: 1,200.
- Planning rows with changed projected balances: 5.

The infeasible purchase order was excluded from the feasible supply calculation. For SKU-000025 at LOC-0004, the projected balance in week 2026W04 changed from 999,944 units to -56 units, revealing a shortage of 56 units.

This experiment demonstrates supplier constraint detection and its effect on shortage calculations. It does not establish full production feasibility or end-to-end planning at the challenge's target scale.
