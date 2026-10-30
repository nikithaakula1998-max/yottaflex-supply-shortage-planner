
# YottaFlex Supply Shortage Planner

A Python-based synthetic supply-chain planning and validation project developed for the YottaFlex Associate AI Forward Deployed Engineer hiring challenge.

## Project Status

Working nine-step end-to-end pipeline at the demonstrated small scale, with automated validation, shortage planning, production feasibility checks, mitigation evaluation, and controlled anomaly testing.

The implementation is partial relative to the full challenge scope. Full-scale end-to-end execution, comprehensive policy enforcement, and optimization are not yet demonstrated.

## Objective

Generate reproducible synthetic supply-chain data, identify potential shortages, evaluate supplier and production constraints, and distinguish feasible planning actions from decisions that require further review.

## Technology

- Python 3.10+
- Python standard library
- CSV and JSON
- Git and GitHub
- unittest

No third-party Python packages are required.

## Implemented Features

### 1. Synthetic Supply-Chain Data

The main generator creates:

- SKUs and locations
- Suppliers and supplier capacities
- Supplier lead times
- Weekly demand forecasts
- Initial inventory
- Purchase orders
- Shortage records
- Mitigation candidates
- A generation manifest

The generator uses deterministic seeded randomness.

The demonstrated baseline configuration contains:

| Dataset | Records |
|---|---:|
| SKUs | 30 |
| Locations | 5 |
| Suppliers | 10 |
| Forecast demand | 1,200 |
| Inventory | 150 |
| Purchase orders | 100 |
| Shortages | 406 |
| Mitigation candidates | 406 |

### 2. Large-Scale Streaming Demand Generation

A separate streaming generator produced:

- 3,000 SKUs
- 50 locations
- 52 weeks
- 7,800,000 weekly demand records

The streaming approach avoids retaining all generated demand records in memory.

This is a demand-generation scalability demonstration, not proof that the complete planning pipeline operates at this scale.

### 3. Data Quality Validation

The data-quality validator checks supported datasets for issues including:

- Missing required files and columns
- Duplicate identifiers
- Invalid quantities
- Invalid dates and ISO weeks
- Invalid effective-date ranges
- Selected foreign-key relationships

The demonstrated pipeline checked 14 datasets and reported zero issues.

These checks are not a complete enforcement of every possible business rule or unit-of-measure constraint.

### 4. Supplier and Shortage Feasibility

The supplier validation and feasible planning modules check modeled purchase orders against:

- Supplier weekly capacity
- Supplier lead time
- Availability of required supplier constraint records

The feasible shortage planner excludes purchase orders that fail implemented supplier validation checks when calculating feasible inbound supply.

The demonstrated baseline checked 100 purchase orders and produced 1,200 planning rows with zero supplier validation issues.

Supplier-SKU qualification, complete effective-date enforcement, and all purchasing policies remain incomplete.

### 5. Production Planning

The production planner creates proposed production quantities from forecast demand.

The demonstrated run produced 1,200 production proposals.

Proposals are initially labeled `PROPOSED_UNVERIFIED`. Their feasibility must be assessed separately.

### 6. Bill of Materials and Production Feasibility

The project generates a bill of materials and evaluates production proposals against modeled component and factory constraints.

The cumulative validator supports:

- Component requirements from BOM relationships
- Initial component inventory
- Cumulative component reservation
- Partial production feasibility
- Eligible inbound component replenishment
- Shared weekly production capacity by location

Results from the demonstrated pipeline:

| Production result | Count |
|---|---:|
| Component shortage | 579 |
| Component stock available | 228 |
| No active BOM | 240 |
| Partially feasible | 41 |
| Production capacity exceeded | 112 |
| Total proposals evaluated | 1,200 |

The run reported:

- Proposed production units: 9,642
- Feasible production units: 1,840
- Unfulfilled production units: 7,802
- Eligible component deliveries applied: 842
- Weekly factory capacity records: 40

Important limitations:

- Supplier-valid expected deliveries are assumed to arrive on time.
- Full BOM effective-date filtering is incomplete.
- Component demand outside modeled production is not included.
- The results do not represent a fully optimized production schedule.

### 7. Mitigation Feasibility Evaluation

The mitigation validator evaluates generated `EXPEDITE_SUPPLY` candidates using modeled:

- Supplier activity status
- Supplier associations inferred from purchase orders
- Lead times
- Minimum order quantities
- Remaining weekly supplier capacity
- Capacity reservations across evaluated mitigation options

Each candidate is classified as either:

- `POTENTIALLY_FEASIBLE_UNCONFIRMED`
- `FLAG_FOR_REVIEW`

Results from the demonstrated run:

| Mitigation result | Count |
|---|---:|
| Options evaluated | 406 |
| Potentially feasible, unconfirmed | 22 |
| Flagged for review | 384 |

Potential feasibility does not establish supplier approval, confirmed delivery, or full supplier-SKU qualification.

The current validator uses the earliest shortage week as a simulated planning date. This assumption can affect feasibility results and should not be interpreted as an actual procurement date.

Mitigation recommendations are not yet optimized across cost, service level, and all downstream inventory effects. Separate shortage records may also represent overlapping needs across weeks.

### 8. Controlled Anomaly Scenarios

Five synthetic scenarios are supported:

1. Inbound double counting
2. Unapproved substitution
3. Supplier capacity exceeded
4. Lead time ignored
5. Unit-of-measure mismatch

The anomaly generator creates isolated scenario records without modifying the baseline datasets.

All five scenarios matched their expected review decisions in the latest demonstrated run.

These tests are scenario-specific, not comprehensive anomaly detection over all generated records.

## Running the Complete Pipeline

Open PowerShell in the project root.

Run:

```powershell
py -m src.run_pipeline --out outputs/pipeline_run --capacity 100
```

The output directory must be new or empty. Use a different directory name for subsequent runs.

The pipeline executes nine steps:

1. Generate synthetic supply-chain data.
2. Generate production proposals.
3. Generate BOM relationships.
4. Generate weekly factory capacity.
5. Validate source data quality.
6. Validate suppliers and calculate feasible shortage balances.
7. Check cumulative BOM and production capacity.
8. Evaluate shortage mitigation feasibility.
9. Run automated tests.

If a step fails, the pipeline stops with an error.

## Important Output Reports

The complete pipeline generates reports including:

- `data_quality_report.csv`
- `supplier_validation_report.csv`
- `feasible_shortage_plan.csv`
- `cumulative_bom_report.csv`
- `mitigation_feasibility_report.csv`

These reports are stored inside the selected output folder.

Generated output folders are excluded from Git tracking.

## Automated Tests

Run:

```powershell
py -m unittest discover -s tests -v
```

Latest verified local result:

```text
Ran 16 tests

OK
```

The automated tests cover:

- Deterministic data generation
- Inventory balance reconciliation
- Supplier capacity and lead-time violations
- Five controlled anomaly scenarios
- Duplicate identifiers, invalid weeks, and negative inventory
- Component delivery timing
- Partial production and cumulative stock reservation
- Shared factory production capacity
- Mitigation lead time, MOQ, supplier capacity, and reservation behavior

Passing these tests confirms the tested cases, not correctness under every possible supply-chain condition.

## Supplier Constraint Experiment

A controlled negative test was performed on a separate copy of the baseline dataset.

- Original purchase order quantity: 72 units
- Modified purchase order quantity: 1,000,000 units
- Purchase orders checked: 100
- Validation issues detected: 1
- Planning rows evaluated: 1,200
- Planning rows with changed projected balances: 5

The infeasible purchase order was excluded from the feasible supply calculation.

For SKU-000025 at LOC-0004, the projected balance in week 2026W04 changed from 999,944 units to -56 units, revealing a shortage of 56 units.

This demonstrates the impact of supplier validation on projected shortages.

## Known Limitations and Future Work

- Full-scale end-to-end execution is not yet demonstrated.
- The complete generator is not streaming at the target scale.
- Supplier-SKU qualification and complete purchasing policy enforcement are incomplete.
- Mitigation feasibility depends on a simulated planning date and does not guarantee delivery.
- Mitigation quantities are not globally optimized across overlapping weekly shortages.
- Complete BOM effective-date and external component-demand modeling remain incomplete.
- Comprehensive unit-of-measure conversion and lifecycle validation remain incomplete.
- SQL exports, a complete data dictionary, and formal evaluation metrics are not yet delivered.
- The generation manifest records initial file hashes; downstream modifications may make some original hashes stale.
- Controlled anomaly scenarios are isolated from baseline data.

## Reproducibility

Synthetic data generation uses deterministic seeded randomness.

The initial generator writes a manifest containing configuration, row counts, and file hashes.

Because downstream modules may modify or create files, the initial manifest should not be treated as a final integrity manifest for every pipeline output.

## Data Provenance

All generated supply-chain records are synthetic. No third-party dataset is used.

## AI Assistance Disclosure

AI assistance was used for code generation, debugging, documentation, and test design.

Development notes and recorded prompts are maintained in:

`prompts/prompt_history.md`

The prompt history should not be described as a complete verbatim record unless every required interaction has been captured.

## Repository

https://github.com/nikithaakula1998-max/yottaflex-supply-shortage-planner
