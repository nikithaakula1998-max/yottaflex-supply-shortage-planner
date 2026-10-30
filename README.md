
# YottaFlex Supply Shortage Planner

A Python-based synthetic supply-chain planning and validation project developed for the YottaFlex Associate AI Forward Deployed Engineer hiring challenge.

The project generates reproducible supply-chain data, detects projected inventory shortages, checks supplier and production constraints, evaluates proposed mitigation actions, and exports data for further analysis.

## 1. Project Status

The project has successfully demonstrated full-scale synthetic data generation, supplier and data-quality validation, cumulative production and BOM feasibility checks, mitigation feasibility evaluation, and multi-format data export.

### Verified full-scale results

| Metric | Result |
|---|---:|
| SKUs | 3,000 |
| Locations | 50 |
| Suppliers | 500 |
| Planning weeks | 52 |
| Forecast demand records | 7,800,000 |
| Production proposals | 7,800,000 |
| Purchase orders | 10,000 |
| Shortage records | 7,065,828 |
| Mitigation candidates | 7,065,828 |
| Synthetic source datasets | 14 |
| Automated tests passed | 16 / 16 |
| Ground-truth scenarios matched | 5 / 5 |

**Important:** Completing the validation workflow does not mean all generated plans are executable. The production validator identified substantial infeasibility, and most mitigation candidates require further review.

This is a synthetic planning demonstration, not a production-ready procurement or optimization platform.

## 2. Objective

Supply-chain planners need to understand where shortages may occur and whether proposed actions can realistically address them.

This project aims to:

1. Generate consistent, reproducible synthetic supply-chain datasets.
2. Forecast potential shortages using inventory, inbound supply, and demand.
3. Validate supplier capacity, minimum order quantities, and lead-time constraints.
4. Evaluate manufacturing proposals against BOM component requirements and shared production capacity.
5. Flag mitigation candidates that cannot be automatically confirmed.
6. Demonstrate controlled anomaly detection.
7. Export the data into formats suitable for downstream analysis.

The system separates generated proposals from validated business decisions.

## 3. Technology Stack

- Python 3.10+ (developed and tested in a Python 3.14 environment)
- Python standard library
- CSV
- JSON and JSON Lines (JSONL)
- SQLite
- SQL schema export
- `unittest`
- Git and GitHub

No third-party Python packages are required for the documented modules.

## 4. Project Architecture

The full-scale workflow follows this structure:

```text
Synthetic Data Generator
         |
         v
14 Source CSV Datasets
         |
         +------------------------+
         |                        |
         v                        v
Data Quality Validator     Supplier / PO Validator
         |                        |
         +------------+-----------+
                      |
                      v
             Shortage Planning
                      |
                      v
           Production / BOM Validator
                      |
                      v
           Mitigation Feasibility
                      |
                      v
             Validation Reports
                      |
                      v
           CSV / JSONL / SQLite
```

The validation modules are separate so that data quality, supplier constraints, production feasibility, and mitigation decisions can be evaluated independently.

## 5. Synthetic Datasets

The full-scale generator produces 14 datasets.

| Dataset | Description | Records |
|---|---|---:|
| `sku.csv` | Product and component master data | 3,000 |
| `location.csv` | Warehouse and production locations | 50 |
| `supplier.csv` | Supplier master data | 500 |
| `supplier_capacity.csv` | Weekly supplier capacity and MOQ | 500 |
| `lead_time.csv` | Supplier lead-time rules | 500 |
| `inventory.csv` | Initial SKU-location inventory | 150,000 |
| `forecast_demand.csv` | Weekly SKU-location demand | 7,800,000 |
| `purchase_order.csv` | Inbound purchase orders | 10,000 |
| `production_capacity.csv` | Weekly location production capacity | 2,600 |
| `production_plan.csv` | Proposed production quantities | 7,800,000 |
| `bom.csv` | Bill-of-materials component relationships | 4,800 |
| `shortage.csv` | Projected shortage records | 7,065,828 |
| `mitigation_option.csv` | Proposed shortage mitigation actions | 7,065,828 |
| `ground_truth.csv` | Controlled anomaly scenarios | 5 |

For the complete field definitions, see [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

### Reproducibility

The full-scale streaming generator uses the fixed random seed:

`20261022`

The full-scale generation completed in approximately 123 seconds in the tested environment. Performance will vary by machine and disk speed.

## 6. Implemented Features

### 6.1 Streaming synthetic data generation

The streaming generator creates millions of records without holding all demand rows in memory.

It models products, suppliers, locations, inventory, demand, purchase orders, manufacturing proposals, shortages, and mitigation candidates.

Generated production plans have an unverified proposal status. Mitigation options are also candidates rather than approved actions.

### 6.2 Data-quality validation

The data-quality validator checks supported datasets for structural and consistency issues, including required files, required columns, invalid values, and selected relationships.

Full-scale result:

- 14 datasets checked
- 0 reported data-quality issues

### 6.3 Supplier constraint validation

The supplier validation workflow evaluates purchase orders against modeled supplier constraints, including ordering and delivery rules.

Full-scale result:

- 10,000 purchase orders evaluated
- 0 reported supplier constraint issues
- 7,800,000 planning rows processed

A supplier-valid purchase order is not proof of actual delivery.

### 6.4 Shortage planning

Shortages are projected using inventory, inbound supply, and forecast demand.

The basic relationship is:

`projected_balance = opening_balance + inbound - demand`

A negative projected balance indicates a shortage.

The shortage dataset records projected balances, shortage quantities, priority scores, statuses, and causes.

**Interpretation note:** A continuing negative inventory balance across multiple weeks may represent the same ongoing deficit. Such balances should not automatically be summed as independent shortages.

### 6.5 Production capacity and BOM feasibility

The production feasibility validator evaluates manufacturing proposals using component availability and shared location-week production capacity.

Full-scale results:

| Metric | Result |
|---|---:|
| Production proposals checked | 7,800,000 |
| Planned production units | Approximately 60.21 million |
| Feasible production units | 260,000 |
| Unfulfilled production units | Approximately 59.95 million |
| Feasible share of planned units | Approximately 0.43% |
| Component shortage findings | 93,047 |
| No active BOM findings | 1,560,000 |
| Production capacity exceeded findings | 6,110,232 |

These findings demonstrate that generated manufacturing proposals must be checked before being treated as executable plans.

The current validator does not fully enforce BOM effective-date windows or model external consumption of components.

### 6.6 Mitigation feasibility evaluation

The mitigation validator uses a disk-backed SQLite approach to process millions of mitigation candidates.

Full-scale results:

| Decision | Count |
|---|---:|
| `POTENTIALLY_FEASIBLE_UNCONFIRMED` | 500 |
| `FLAG_FOR_REVIEW` | 7,065,328 |
| Total candidates evaluated | 7,065,828 |

Potential feasibility does not constitute supplier approval, confirmed availability, or guaranteed delivery.

### 6.7 Controlled anomaly scenarios

The project includes five ground-truth anomaly scenarios.

The implemented checks matched all five expected decisions during testing.

These scenarios provide targeted validation examples, not exhaustive real-world anomaly coverage.

### 6.8 Multi-format data export

The export module converts generated source CSV datasets into:

- JSON Lines (`.jsonl`)
- SQLite database (`.sqlite3`)
- SQL table schema (`.sql`)
- Dataset count manifest (`export_counts.json`)

The full-scale export was completed and all 14 dataset counts were verified.

## 7. Getting Started

### Prerequisites

Install Python 3.10 or later and Git.

Clone the repository:

```bash
git clone https://github.com/nikithaakula1998-max/yottaflex-supply-shortage-planner.git
cd yottaflex-supply-shortage-planner
```

The documented commands use the Windows Python launcher (`py`). On systems without that launcher, replace `py` with `python`.

No additional Python packages are required for the documented standard-library modules.

### Generate the full-scale datasets

```bash
py -m src.streaming_generator --out outputs/streaming_full_02
```

The generated data is written to the specified output folder.

### Validate supplier constraints

```bash
py -m src.feasible_planner --input outputs/streaming_full_02
```

### Validate data quality

```bash
py -m src.data_quality_validator --input outputs/streaming_full_02
```

### Validate cumulative production and BOM feasibility

```bash
py -m src.cumulative_bom_validator --input outputs/streaming_full_02
```

### Validate mitigation candidates

```bash
py -m src.mitigation_validator --input outputs/streaming_full_02
```

### Export the generated datasets

```bash
py -m src.export_data --input outputs/streaming_full_02 --out outputs/export_full_01
```

### Run the automated tests

```bash
py -m unittest discover -s tests -v
```

The verified local test run completed with 16 passing tests and no failures or errors.

## 8. Important Output Reports

After running the relevant modules, the full-scale output directory contains reports including:

| File | Purpose |
|---|---|
| `data_quality_report.csv` | Structural and data-quality findings |
| `supplier_validation_report.csv` | Supplier and purchase-order constraint results |
| `feasible_shortage_plan.csv` | Planning results from supplier feasibility workflow |
| `cumulative_bom_report.csv` | Production, component, and capacity feasibility |
| `mitigation_feasibility_report.csv` | Preliminary mitigation feasibility decisions |

The export directory contains:

```text
outputs/export_full_01/
    yottaflex.sqlite3
    schema.sql
    export_counts.json
    *.jsonl
```

The `outputs/` directory is excluded from Git to avoid committing very large generated files. Reviewers can reproduce the outputs using the commands above.

For detailed verified results, see [VALIDATION_SUMMARY.md](VALIDATION_SUMMARY.md).

## 9. Automated Testing

The test suite covers implemented planning and validation behavior, including production feasibility, mitigation evaluation, and controlled anomaly scenarios.

Run:

```bash
py -m unittest discover -s tests -v
```

Verified local result:

```text
Ran 16 tests
OK
```

Passing tests demonstrate that the implemented test cases behave as expected. They do not establish complete business-policy coverage.

## 10. Known Limitations

The project intentionally distinguishes demonstrated behavior from unimplemented enterprise capabilities.

Current limitations include:

1. All datasets are synthetic; real-world forecasting accuracy is not established.
2. Supplier-valid deliveries are assumed to arrive on their modeled dates.
3. BOM effective-date windows are not fully enforced in cumulative production validation.
4. External component demand is not fully modeled by the production validator.
5. Production proposals may greatly exceed available manufacturing capacity.
6. Mitigation feasibility is preliminary and does not represent confirmed execution.
7. Supplier-SKU qualification is inferred from available purchase-order relationships rather than a comprehensive approved-supplier catalog.
8. Continuing negative inventory balances may appear as shortages in consecutive weeks.
9. The system is not a globally optimized procurement or production scheduler.
10. The exported SQLite database is an analytical artifact; logical relationships are not necessarily enforced as database foreign keys.

## 11. Future Improvements

Potential next steps include:

- Enforcing BOM effective-date rules during production feasibility evaluation.
- Modeling additional component demand and competing consumption.
- Introducing explicit supplier-SKU approval relationships.
- Improving mitigation allocation and prioritization across competing shortages.
- Adding optimization techniques for supplier selection and production scheduling.
- Extending automated tests for larger and more varied edge cases.
- Building an interactive planning dashboard.
- Adding operational monitoring and execution confirmation.

These are proposed improvements, not implemented features.

## 12. Documentation

The repository includes:

- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) — definitions of the 14 source datasets, columns, and relationships.
- [VALIDATION_SUMMARY.md](VALIDATION_SUMMARY.md) — verified test results, full-scale validation metrics, and limitations.
- `prompts/prompt_history.md` — available record of AI-assisted development prompts and decisions.

## 13. Data Provenance

All business records in this project are artificially generated.

The dataset does not contain real customer information, real supplier transactions, or confidential enterprise records.

A fixed random seed supports repeatable generation. Different Python environments and code revisions should be considered when comparing outputs.

## 14. AI Assistance Disclosure

AI assistance was used during project development for explanations, implementation guidance, code drafting, debugging support, documentation, and test-planning suggestions.

Generated code and recommendations were checked through local execution, test runs, and validation reports.

The project includes an available prompt-history record to support transparency about AI-assisted development.

AI assistance does not replace independent verification of business rules, correctness, or production readiness.

## 15. Repository

GitHub:

https://github.com/nikithaakula1998-max/yottaflex-supply-shortage-planner

This repository demonstrates a reproducible synthetic supply-chain planning workflow with explicit validation of supplier constraints, production feasibility, and mitigation candidates.
