
# YottaFlex Synthetic Supply Shortage Planner
## Data Dictionary

This document describes the 14 synthetic datasets used by the supply shortage planning system.

The datasets are generated using a fixed random seed (`20261022`) and contain no real customer or supplier information.

### Data conventions

- **PK (Primary Key):** Uniquely identifies a record.
- **FK (Foreign Key):** References a record in another dataset.
- **SKU:** Stock Keeping Unit, representing a product or component.
- **UOM:** Unit of Measure.
- **Week:** ISO week in `YYYYWww` format, such as `2026W02`.
- **Dates:** ISO date format, `YYYY-MM-DD`.
- **Effective dates:** Define when a supplier rule or BOM record is valid.
- **Quantities:** Non-negative numbers unless explicitly representing a signed inventory balance.
- **Statuses:** Describe lifecycle or validation state, not necessarily confirmed execution.

---

## 1. SKU — `sku.csv`

**Purpose:** Master list of products and components.

| Column | Description |
|---|---|
| `sku_id` | PK — unique product identifier |
| `name` | Synthetic product name |
| `uom` | Default unit of measure |
| `unit_cost` | Estimated cost per unit |

## 2. Location — `location.csv`

**Purpose:** Master list of warehouses or production locations.

| Column | Description |
|---|---|
| `location_id` | PK — unique location identifier |
| `name` | Synthetic location name |

## 3. Supplier — `supplier.csv`

**Purpose:** Master list of suppliers and their lifecycle statuses.

| Column | Description |
|---|---|
| `supplier_id` | PK — unique supplier identifier |
| `name` | Synthetic supplier name |
| `status` | Supplier lifecycle status, such as active or inactive |

## 4. Supplier Capacity — `supplier_capacity.csv`

**Purpose:** Defines supplier ordering limits and minimum order quantities.

| Column | Description |
|---|---|
| `capacity_id` | PK — unique capacity rule identifier |
| `supplier_id` | FK → `supplier.supplier_id` |
| `weekly_capacity` | Maximum modeled units the supplier can supply in one week |
| `moq` | Minimum Order Quantity accepted by the supplier |
| `effective_from` | First date the capacity rule is valid |
| `effective_to` | Last date the capacity rule is valid |

**Business rule:** Supplier orders and mitigation proposals must respect the applicable weekly capacity and MOQ.

## 5. Lead Time — `lead_time.csv`

**Purpose:** Defines expected supplier delivery lead times.

| Column | Description |
|---|---|
| `lead_time_id` | PK — unique lead-time rule identifier |
| `supplier_id` | FK → `supplier.supplier_id` |
| `lead_days` | Minimum modeled days between ordering and expected arrival |
| `effective_from` | First valid date |
| `effective_to` | Last valid date |

**Business rule:** An expected arrival earlier than the allowed lead time is flagged as invalid.

## 6. Inventory — `inventory.csv`

**Purpose:** Starting inventory balance for each SKU and location.

| Column | Description |
|---|---|
| `inventory_id` | PK — unique inventory record identifier |
| `sku_id` | FK → `sku.sku_id` |
| `location_id` | FK → `location.location_id` |
| `as_of_date` | Date of the inventory snapshot |
| `on_hand` | Quantity physically available at the snapshot date |
| `uom` | Inventory unit of measure |

## 7. Forecast Demand — `forecast_demand.csv`

**Purpose:** Expected demand for each product, location, and planning week.

| Column | Description |
|---|---|
| `demand_id` | PK — unique forecast record identifier |
| `sku_id` | FK → `sku.sku_id` |
| `location_id` | FK → `location.location_id` |
| `week` | ISO planning week |
| `quantity` | Forecast demand quantity |
| `uom` | Demand unit of measure |

**Scale:** 3,000 SKUs × 50 locations × 52 weeks = 7,800,000 records.

## 8. Purchase Orders — `purchase_order.csv`

**Purpose:** Synthetic inbound supply orders.

| Column | Description |
|---|---|
| `po_id` | PK — unique purchase order identifier |
| `sku_id` | FK → `sku.sku_id` |
| `location_id` | FK → `location.location_id` |
| `supplier_id` | FK → `supplier.supplier_id` |
| `quantity` | Ordered quantity |
| `ordered_on` | Purchase order creation date |
| `expected_arrival` | Modeled delivery date |
| `status` | Purchase order lifecycle status |
| `uom` | Ordered unit of measure |

**Business rules:** Validate supplier status, lead time, weekly capacity, and quantity. Expected arrival is a planning assumption, not proof of delivery.

## 9. Production Capacity — `production_capacity.csv`

**Purpose:** Maximum manufacturing output for each location and week.

| Column | Description |
|---|---|
| `location_id` | FK → `location.location_id` |
| `week` | ISO planning week |
| `max_production_units` | Maximum total production units allowed for that location and week |

**Logical key:** Combination of `location_id` and `week`.

**Business rule:** All production proposals at the same location and week share the capacity limit.

## 10. Production Plan — `production_plan.csv`

**Purpose:** Proposed manufacturing quantities for products.

| Column | Description |
|---|---|
| `production_id` | PK — unique production proposal identifier |
| `sku_id` | FK → `sku.sku_id` |
| `location_id` | FK → `location.location_id` |
| `week` | Proposed production week |
| `planned_quantity` | Proposed number of finished units |
| `status` | Production proposal lifecycle or validation status |
| `uom` | Finished product unit of measure |

**Important:** Production proposals are not automatically feasible. The production validator checks component availability and shared factory capacity.

## 11. Bill of Materials — `bom.csv`

**Purpose:** Defines components needed to manufacture finished products.

| Column | Description |
|---|---|
| `bom_id` | PK — unique BOM record identifier |
| `parent_sku_id` | FK → `sku.sku_id`; finished product |
| `component_sku_id` | FK → `sku.sku_id`; required component |
| `quantity_per_unit` | Component units required per finished unit |
| `uom` | Component unit of measure |
| `effective_from` | First date the BOM relationship is valid |
| `effective_to` | Last date the BOM relationship is valid |
| `status` | BOM lifecycle status |

**Example:** If one finished product needs two components and the plan proposes ten finished products, the component requirement is twenty units.

**Current limitation:** The cumulative production validator checks active BOM status but does not fully enforce BOM effective-date windows.

## 12. Shortage — `shortage.csv`

**Purpose:** Records projected inventory shortages and their planning priority.

| Column | Description |
|---|---|
| `shortage_id` | PK — unique shortage record identifier |
| `sku_id` | FK → `sku.sku_id` |
| `location_id` | FK → `location.location_id` |
| `week` | Week of the projected shortage |
| `opening_balance` | Inventory balance entering the planning calculation |
| `inbound` | Eligible modeled inbound supply |
| `demand` | Forecast demand for the week |
| `projected_balance` | Projected inventory balance after supply and demand |
| `shortage_qty` | Magnitude of the negative projected balance |
| `priority_score` | Numeric score used to prioritize review |
| `status` | Shortage record status |
| `cause` | Generated explanation or classification of the shortage |

**Planning relationship:**

`projected_balance = opening_balance + inbound - demand`

A negative projected balance indicates a shortage.

**Important:** Repeated negative projected balances across consecutive weeks can represent an ongoing deficit. They must not automatically be added together as independent unmet-demand events.

## 13. Mitigation Option — `mitigation_option.csv`

**Purpose:** Candidate actions for reducing a projected shortage.

| Column | Description |
|---|---|
| `mitigation_id` | PK — unique mitigation candidate identifier |
| `shortage_id` | FK → `shortage.shortage_id` |
| `option_type` | Proposed mitigation action, such as expedited supply |
| `quantity` | Requested mitigation quantity |
| `estimated_cost` | Estimated cost associated with the proposal |
| `status` | Candidate or validation lifecycle status |
| `reason` | Generated explanation for the candidate |

**Business rule:** A candidate is not a confirmed solution. Supplier capacity, MOQ, lead time, and available evidence must be checked.

The separate `mitigation_feasibility_report.csv` contains the validation results.

## 14. Ground Truth — `ground_truth.csv`

**Purpose:** Defines the expected results for five deliberately introduced anomaly scenarios.

| Column | Description |
|---|---|
| `case_id` | PK — unique anomaly scenario identifier |
| `issue_type` | Type of anomaly being tested |
| `expected_decision` | Expected validation decision |
| `description` | Explanation of the anomaly scenario |

**Use:** The anomaly validator compares its decisions against these expected outcomes.

---

## Relationships

The main relationships are:

- `inventory.sku_id` → `sku.sku_id`
- `inventory.location_id` → `location.location_id`
- `forecast_demand.sku_id` → `sku.sku_id`
- `forecast_demand.location_id` → `location.location_id`
- `purchase_order.supplier_id` → `supplier.supplier_id`
- `purchase_order.sku_id` → `sku.sku_id`
- `purchase_order.location_id` → `location.location_id`
- `supplier_capacity.supplier_id` → `supplier.supplier_id`
- `lead_time.supplier_id` → `supplier.supplier_id`
- `production_plan.sku_id` → `sku.sku_id`
- `production_plan.location_id` → `location.location_id`
- `production_capacity.location_id` → `location.location_id`
- `bom.parent_sku_id` → `sku.sku_id`
- `bom.component_sku_id` → `sku.sku_id`
- `shortage.sku_id` → `sku.sku_id`
- `shortage.location_id` → `location.location_id`
- `mitigation_option.shortage_id` → `shortage.shortage_id`

These describe logical relationships. The CSV and JSONL formats do not enforce database foreign-key constraints automatically.

## Full-scale dataset counts

| Dataset | Records |
|---|---:|
| sku | 3,000 |
| location | 50 |
| supplier | 500 |
| supplier_capacity | 500 |
| lead_time | 500 |
| inventory | 150,000 |
| forecast_demand | 7,800,000 |
| purchase_order | 10,000 |
| production_capacity | 2,600 |
| production_plan | 7,800,000 |
| bom | 4,800 |
| shortage | 7,065,828 |
| mitigation_option | 7,065,828 |
| ground_truth | 5 |

## Export formats

The project supports:

- **CSV:** Original generated datasets.
- **JSONL:** One JSON object per line for scalable processing.
- **SQLite:** Queryable database containing the generated datasets.
- **SQL schema:** Table definitions exported as `schema.sql`.

The exports are synthetic demonstration data, not live enterprise supply-chain records.

## Known modeling limitations

1. Supplier-valid expected deliveries are assumed to arrive on time.
2. BOM effective-date windows are not fully enforced by the cumulative production validator.
3. Component demand outside production is not modeled by that validator.
4. Production plans are proposals and can exceed available component stock or factory capacity.
5. Supplier-SKU qualification is inferred from observed purchase-order relationships rather than a complete approved-supplier catalog.
6. Mitigation feasibility is provisional and does not guarantee supplier approval or delivery.
7. Consecutive shortage balances may describe the same continuing inventory deficit.

These limitations should be considered when interpreting the reports.
