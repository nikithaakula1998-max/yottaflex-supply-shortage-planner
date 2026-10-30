# AI Prompt History — YottaFlex Supply Shortage Planner

## 1. AI Tool Used

**Tool:** ChatGPT (OpenAI)

**Development period:** October 2026

**Project:** YottaFlex Supply Shortage Planner

**Purpose:** ChatGPT was used as a development assistant to understand requirements, plan the implementation, draft and debug Python code, create tests, review terminal output, and prepare documentation.

All generated code and suggested commands were reviewed or executed locally. AI-generated suggestions were not treated as automatically correct.

## 2. AI-Assisted Development Activities

### 2.1 Synthetic Data Generation

**Task:** Create a synthetic supply-chain dataset with connected business entities.

**Implementation:**
- Generated SKU, location, supplier, supplier-capacity, lead-time, forecast-demand, inventory, and purchase-order records.
- Used consistent identifiers to connect related tables.
- Added deterministic random generation using seed `20261022`.
- Generated shortage and mitigation-candidate records.

**Verification:** Executed the main generator on a small dataset and checked its generated CSV files and manifest.

### 2.2 Large-Scale Forecast Generation

**Task:** Generate demand records for 3,000 SKUs across 50 locations and 52 weeks without holding the entire dataset in memory.

**Implementation:** Developed a streaming forecast-demand generator.

**Verification:** Generated 7,800,000 forecast-demand rows in a separate scale test.

**Limitation:** This was a forecast-demand generation test, not a successful full-scale end-to-end planning run.

### 2.3 Shortage Calculation

**Task:** Identify projected inventory shortages using opening inventory, incoming purchase orders, and forecast demand.

**Implementation:**
- Calculated projected inventory balances by SKU, location, and week.
- Generated shortage records when projected balances became negative.
- Assigned shortage-priority scores.
- Generated unverified mitigation candidates.

**Verification:** Executed inventory reconciliation tests.

**Limitation:** Mitigation candidates are not guaranteed to be executable.

### 2.4 Bill of Materials (BOM)

**Task:** Model component relationships and evaluate material availability for proposed production.

**Implementation:**
- Generated synthetic BOM relationships.
- Created proposed production-plan rows.
- Implemented snapshot BOM checks.
- Added a cumulative validator that reserves initial component inventory across successive production proposals.

**Verification:**
- Checked 1,200 production proposals.
- Reported 744 `COMPONENT_SHORTAGE` results.
- Reported 216 `COMPONENT_STOCK_AVAILABLE` results.
- Reported 240 `NO_ACTIVE_BOM` results.

**Limitations:** Cumulative checks use initial component stock only and do not fully model replenishment, production capacity, or all component demand.

### 2.5 Supplier Feasibility

**Task:** Evaluate supplier constraints before treating purchase-order quantities as feasible inbound supply.

**Implementation:**
- Added supplier lead-time and capacity validation.
- Created a feasible shortage-planning report.
- Compared original projected balances with balances calculated using feasible inbound supply.

**Verification:** Tested a deliberately invalid purchase order in a separate copy of the dataset.

### 2.6 Controlled Anomaly Scenarios

**Task:** Create synthetic anomalies with known expected decisions.

**Scenarios:**
1. `INBOUND_DOUBLE_COUNT`
2. `UNAPPROVED_SUBSTITUTE`
3. `SUPPLIER_CAPACITY_EXCEEDED`
4. `LEAD_TIME_IGNORED`
5. `UOM_MISMATCH`

**Implementation:** Created separate anomaly-generation and anomaly-validation modules.

**Verification:** All five controlled scenarios matched their expected `FLAG_FOR_REVIEW` decisions.

**Limitation:** These are controlled test cases, not proof of comprehensive anomaly detection across arbitrary supply-chain datasets.

### 2.7 Automated Testing

**Task:** Test important data-generation and validation behavior.

**Implementation:** Used Python's `unittest` framework.

**Verified tests:**
- `test_five_anomaly_scenarios`
- `test_balance_reconciles`
- `test_repeatable`
- `test_lead_time_violation`
- `test_supplier_capacity_violation`

**Latest verified result:**

`Ran 5 tests in 0.112s — OK`

### 2.8 Debugging and Version Control

**Task:** Resolve local Python execution issues and maintain a working GitHub repository.

**Work performed:**
- Reviewed terminal errors and module-execution commands.
- Restored the main generator after an accidental edit.
- Verified that the working `src/main.py` matched the committed version.
- Used Git to commit and push tested code and documentation.
- Preserved local backup files without adding them to the repository.

### 2.9 Documentation

**Task:** Explain the project, setup instructions, tested features, and known limitations.

**Work performed:**
- Updated `README.md`.
- Documented the supplier-constraint experiment.
- Recorded AI assistance and verification steps.
- Clearly identified incomplete challenge requirements.

## 3. Supplier Constraint Experiment

A controlled negative test was performed on a copy of the generated dataset.

**Test setup:**
- Original purchase-order quantity: 72 units
- Modified purchase-order quantity: 1,000,000 units
- Orders checked: 100
- Validation issues detected: 1
- Planning rows evaluated: 1,200
- Planning rows with changed projected balances: 5

**Affected SKU:** `SKU-000025`

**Affected location:** `LOC-0004`

| Week | Original Projected Balance | Feasible Projected Balance | Feasible Shortage |
|---|---:|---:|---:|
| 2026W04 | 999944 | -56 | 56 |
| 2026W05 | 999901 | -99 | 99 |
| 2026W06 | 999873 | -127 | 127 |
| 2026W07 | 999848 | -152 | 152 |
| 2026W08 | 999823 | -177 | 177 |

**Conclusion:** The planner detected an invalid supplier order and excluded its quantity from the feasible supply calculation, changing five projected inventory balances.

This demonstrates a specific supplier-constraint behavior, not complete planning feasibility.

## 4. Verbatim Prompt Record — Available Messages

The following user messages are reproduced from the development conversation available when this document was prepared.

**AI tool:** ChatGPT (OpenAI)

**Context:** GitHub verification and AI prompt-history documentation, October 2026.

### Prompt 1

> can ylu directy cannot give me as i am using friends chat gpt because her is plus so i am using hers

**Purpose:** Asked whether the AI assistance document could be prepared directly without exporting another person's ChatGPT account history.

**Result:** ChatGPT explained the distinction between an assistance summary and an exact prompt transcript.

### Prompt 2

> yes

**Purpose:** Confirmed the request to prepare a copy-ready prompt-history document.

**Result:** ChatGPT prepared this structured document.

**Historical prompt limitation:** Earlier development requests for data generation, BOM modeling, supplier validation, and testing are summarized in Section 2. Their original verbatim wording and individual timestamps are not available in this record. They have not been fabricated or presented as exact quotations.

## 5. Commands and Verification Evidence

The following commands were used during local development and verification:

```powershell
py -m src.main --out outputs/final_verification
py -m src.production_planner --input outputs/final_verification
py -m src.bom_generator --input outputs/final_verification
py -m src.bom_validator --input outputs/final_verification
py -m src.cumulative_bom_validator --input outputs/final_verification
py -m src.feasible_planner --input outputs/final_verification
py -m src.anomaly_generator --input outputs/my_first_run
py -m src.anomaly_validator --input outputs/my_first_run
py -m src.feasible_planner --input outputs/supplier_constraint_test
py -m unittest discover -s tests -v
```

**GitHub repository:**

https://github.com/nikithaakula1998-max/yottaflex-supply-shortage-planner

**Latest verified pushed commit at the time of writing:** `fe88cac`

## 6. Known Limitations

This project remains a partial implementation.

- Full-scale end-to-end generation and planning have not been completed.
- Large-scale streaming was demonstrated for forecast demand only.
- Supplier feasibility validation is limited.
- Production proposals are not fully validated for all real-world constraints.
- Mitigation feasibility and cost-versus-service optimization remain incomplete.
- Comprehensive data validation and some requested export formats remain incomplete.
- The complete verbatim history of earlier AI prompts is unavailable.

## 7. AI Assistance Disclosure

ChatGPT assisted with technical explanations, implementation planning, code drafts, debugging, automated testing, command-line guidance, and documentation.

The developer executed commands locally, inspected generated results, and committed changes to GitHub.

Passing tests demonstrate the behavior of the tested scenarios only. They do not establish full compliance with all challenge requirements.

This document records the available evidence accurately and distinguishes verified work from incomplete functionality and unavailable historical prompts.
