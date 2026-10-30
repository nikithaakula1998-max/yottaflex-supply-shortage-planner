
# YottaFlex Supply Shortage Planner
## Validation Summary

### 1. Project overview

This project generates synthetic supply-chain data and evaluates potential supply shortages, purchase-order constraints, production feasibility, and mitigation options.

The full-scale dataset was generated using a fixed random seed (`20261022`) to support reproducible testing.

All results below refer to the full-scale dataset in:

`outputs/streaming_full_02/`

The generated outputs are synthetic and do not represent real business transactions.

---

### 2. Dataset generation results

| Dataset | Records |
|---|---:|
| SKU | 3,000 |
| Location | 50 |
| Supplier | 500 |
| Supplier Capacity | 500 |
| Lead Time | 500 |
| Inventory | 150,000 |
| Forecast Demand | 7,800,000 |
| Purchase Order | 10,000 |
| Production Capacity | 2,600 |
| Production Plan | 7,800,000 |
| Bill of Materials | 4,800 |
| Shortage | 7,065,828 |
| Mitigation Option | 7,065,828 |
| Ground Truth | 5 |

Total datasets: **14**

Full-scale generation completed in approximately **123 seconds** in the tested environment.

---

### 3. Automated unit tests

Command:

`py -m unittest discover -s tests -v`

Verified result:

- Tests executed: 16
- Tests passed: 16
- Errors: 0
- Failures: 0

This confirms that the implemented test cases passed. It does not guarantee that every possible real-world scenario is covered.

---

### 4. Data quality validation

Command:

`py -m src.data_quality_validator --input outputs/streaming_full_02`

Verified result:

- Datasets checked: 14
- Reported issues: 0

Report:

`outputs/streaming_full_02/data_quality_report.csv`

The data-quality checks passed for the generated dataset. These checks are separate from business feasibility validation.

---

### 5. Supplier and purchase-order validation

Command:

`py -m src.feasible_planner --input outputs/streaming_full_02`

Verified result:

- Purchase orders evaluated: 10,000
- Supplier constraint issues reported: 0
- Planning rows processed: 7,800,000

Report:

`outputs/streaming_full_02/supplier_validation_report.csv`

Supplier checks include modeled lead-time, capacity, and ordering constraints.

A valid purchase order is not proof that the supplier will deliver on time.

---

### 6. Cumulative production and BOM feasibility

Command:

`py -m src.cumulative_bom_validator --input outputs/streaming_full_02`

Verified results:

| Metric | Result |
|---|---:|
| Production proposals checked | 7,800,000 |
| Planned production units | Approximately 60,214,200 |
| Feasible production units | 260,000 |
| Unfulfilled production units | Approximately 59,954,200 |
| Feasible share of planned units | Approximately 0.43% |
| Component shortage findings | 93,047 |
| Component stock available findings | 31,821 |
| No active BOM findings | 1,560,000 |
| Partially feasible findings | 4,900 |
| Production capacity exceeded findings | 6,110,232 |
| Production capacity records | 2,600 |
| Eligible component deliveries | 87,363 |
| Excluded component purchase orders | 0 |

Report:

`outputs/streaming_full_02/cumulative_bom_report.csv`

#### Interpretation

The production plans are generated as proposals, not approved manufacturing schedules.

Most proposed units are not feasible under the modeled constraints. This is expected to be exposed by validation rather than hidden.

The feasibility check considers cumulative component availability and shared production capacity. It does not assume every production proposal can be executed.

#### Known limitations

- Supplier-valid inbound deliveries are assumed to arrive as scheduled.
- BOM effective-date windows are not fully enforced.
- External demand for components is not modeled by this validator.
- Results depend on the synthetic assumptions and the order in which production proposals are evaluated.

---

### 7. Mitigation feasibility validation

Command:

`py -m src.mitigation_validator --input outputs/streaming_full_02`

Verified results:

| Metric | Result |
|---|---:|
| Mitigation candidates processed | 7,065,828 |
| Potentially feasible, unconfirmed | 500 |
| Flagged for review | 7,065,328 |

Report:

`outputs/streaming_full_02/mitigation_feasibility_report.csv`

#### Interpretation

The validator uses a disk-backed SQLite approach to process millions of mitigation candidates without loading all records into memory.

A `POTENTIALLY_FEASIBLE_UNCONFIRMED` result means that a candidate passes the implemented preliminary checks. It is not a confirmed supply commitment.

A `FLAG_FOR_REVIEW` result indicates that the candidate cannot be accepted automatically under the available evidence and modeled rules.

---

### 8. Ground-truth anomaly checks

The generated data includes five ground-truth anomaly scenarios.

Verified result:

- Scenarios checked: 5
- Expected decisions matched: 5

These scenarios test specific known issues. They are not an exhaustive evaluation of every possible anomaly.

---

### 9. Export validation

Export command:

`py -m src.export_data --input outputs/streaming_full_02 --out outputs/export_full_01`

Verified results:

- CSV source datasets: 14
- JSONL datasets exported: 14
- SQLite database generated: Yes
- SQL schema generated: Yes
- Export counts verified against source generation counts: Yes

Export files include:

- `outputs/export_full_01/yottaflex.sqlite3`
- `outputs/export_full_01/schema.sql`
- `outputs/export_full_01/export_counts.json`
- Fourteen `.jsonl` files

The exported database is intended for demonstration and analysis. Logical dataset relationships should not be interpreted as automatically enforced foreign-key constraints.

---

### 10. Key limitations and responsible interpretation

1. Synthetic data does not establish real-world forecast accuracy.
2. Projected shortages can represent continuing negative balances across several weeks.
3. Shortage quantities from consecutive weeks should not automatically be summed as independent shortages.
4. Production proposals can exceed component inventory and manufacturing capacity.
5. Supplier-valid deliveries are assumed to arrive on time.
6. BOM effective-date windows and external component consumption are not fully modeled.
7. Mitigation results are provisional and do not guarantee execution.
8. Passing unit tests and data-quality checks does not prove that all generated plans are feasible.

---

### 11. Overall conclusion

The project successfully generated and exported the full-scale synthetic datasets and completed the implemented validation workflows.

The automated test suite passed all 16 tests. Data-quality and supplier checks reported no issues for the generated full-scale dataset.

Production validation identified substantial infeasibility in the proposed manufacturing schedule, while mitigation validation flagged most candidates for review.

These findings demonstrate why supply-chain planning requires explicit feasibility checks rather than treating generated recommendations as executable decisions.
