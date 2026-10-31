# Data Audit Report

**Generated:** 2026-10-31T12:31:21.392679  
**Script:** `scripts/audit_data.py`  
**CSV:** `next_bill_amount_prediction_synthetic_dataset.csv`  
**SHA-256:** `1591046b1a25f22bb6da7f5ff18f84281afcfd62bbf3e7afd582607b15c8859f`  

## 1. Dataset Shape

- **Rows:** 17,000
- **Columns:** 15
- **Expected columns present:** All 15 ✓
- **Extra columns:** None

| Column | Dtype | Missing | Unique |
|--------|-------|---------|--------|
| `customer_id` | str | 0 | 1000 |
| `billing_month` | str | 0 | 17 |
| `plan_type` | str | 0 | 3 |
| `data_usage_gb` | float64 | 0 | 3495 |
| `voice_calls` | int64 | 0 | 476 |
| `sms_count` | int64 | 0 | 231 |
| `addon_data_gb` | float64 | 0 | 3 |
| `plan_fee` | int64 | 0 | 3 |
| `discount_amount` | float64 | 0 | 4 |
| `data_charge` | float64 | 0 | 6183 |
| `voice_charge` | float64 | 0 | 183 |
| `addon_charge` | float64 | 0 | 3 |
| `tax_amount` | float64 | 0 | 5281 |
| `bill_amount` | float64 | 0 | 7127 |
| `next_bill_amount` | float64 | 0 | 7158 |

## 2. Date Range and Months

- **Range:** 2024-01-01 to 2025-05-01
- **Distinct months:** 17
- **Date parse failures:** 0
- **Non-first-of-month rows:** 0

### Per-Month Row Counts

| Month | Rows |
|-------|------|
| 2024-01-01 | 1000 |
| 2024-02-01 | 1000 |
| 2024-03-01 | 1000 |
| 2024-04-01 | 1000 |
| 2024-05-01 | 1000 |
| 2024-06-01 | 1000 |
| 2024-07-01 | 1000 |
| 2024-08-01 | 1000 |
| 2024-09-01 | 1000 |
| 2024-10-01 | 1000 |
| 2024-11-01 | 1000 |
| 2024-12-01 | 1000 |
| 2025-01-01 | 1000 |
| 2025-02-01 | 1000 |
| 2025-03-01 | 1000 |
| 2025-04-01 | 1000 |
| 2025-05-01 | 1000 |

## 3. Customers

- **Distinct customers:** 1000
- **History length:** min=17, max=17, mean=17.0, median=17

| History Length (months) | Customer Count |
|------------------------|----------------|
| 17 | 1000 |

## 4. Duplicates

- **Complete row duplicates:** 0
- **Customer-month key duplicates:** 0

## 5. Sort Order

- **Sorted by (customer_id, billing_month):** True

## 6. Internal Gaps

- **Customers with gaps:** 0
- **Total gap instances:** 0

## 7. Numeric Summaries

See `data_audit.json` for full descriptive statistics.

### Zero-Value Counts (notable)

| Column | Zero Count |
|--------|------------|
| `voice_calls` | 11 |
| `sms_count` | 219 |
| `addon_data_gb` | 14364 |
| `discount_amount` | 11092 |
| `data_charge` | 10223 |
| `voice_charge` | 12447 |
| `addon_charge` | 14364 |

### Negative / Non-finite Values

- **Negative values found:** None
- **Non-finite values found:** None

## 8. Extreme Values (3×IQR)

| Column | Below Lower | Above Upper | Min | Max |
|--------|-------------|-------------|-----|-----|
| `data_usage_gb` | 0 | 80 | 1.0 | 73.65 |
| `addon_data_gb` | 0 | 2636 | 0.0 | 10.0 |
| `data_charge` | 0 | 562 | 0.0 | 1013.26 |
| `voice_charge` | 0 | 3420 | 0.0 | 109.0 |
| `addon_charge` | 0 | 2636 | 0.0 | 100.0 |
| `tax_amount` | 0 | 16 | 22.32 | 222.71 |
| `bill_amount` | 0 | 16 | 146.32 | 1459.97 |
| `next_bill_amount` | 0 | 15 | 146.32 | 1459.97 |

## 9. Plan Analysis

| Plan Type | Count |
|-----------|-------|
| Standard | 7038 |
| Basic | 6987 |
| Premium | 2975 |

- **Plan changes:** 0
- **Customers with changes:** 0

## 10. Target Alignment

- **Total rows:** 17,000
- **Rows with observed next calendar month:** 16,000
- **Matched (|diff| ≤ 0.01):** 16,000
- **Mismatched:** 0
- **Max absolute difference:** 0.0
- **Rows without next calendar month:** 1,000
  - Terminal rows: 1000
  - Gap rows: 0

> **Note:** Rows without an observed next calendar month include each customer's terminal row.
> The supplied `next_bill_amount` for terminal rows cannot be verified against observed data.
> These targets may be valid (representing a future month beyond the dataset) or may be synthetic placeholders.

## 11. Bill Component Reconciliation

**Candidate equation:** `bill_amount = plan_fee - discount_amount + data_charge + voice_charge + addon_charge + tax_amount`

| Statistic | Value |
|-----------|-------|
| Mean residual | 1.5e-05 |
| Std residual | 0.003134 |
| Min residual | -0.01 |
| Max residual | 0.01 |
| Median residual | 0.0 |
| Mean |residual| | 0.000982 |
| Exact matches (±0.01) | 16648 / 17000 |

## 12. Baseline Estimates (All Verified Rows; Descriptive Only)

- **Verified rows used:** 16,000

| Baseline | MAE | RMSE | WAPE |
|----------|-----|------|------|
| Previous bill | 66.6935 | 101.3642 | 0.1287 |
| Trailing 3-month mean | 57.6655 | 85.8695 | 0.1113 |

## 13. Proposed Chronological Split

| Partition | Origin Month(s) | Target Month | Rows | Customers |
|-----------|-----------------|--------------|------|-----------|
| Train | 2024-01-01 – 2025-02-01 | 2024-02-01 – 2025-03-01 | 14000 | 1000 |
| Validation | 2025-03-01 | 2025-04-01 | 1000 | 1000 |
| Test | 2025-04-01 | 2025-05-01 | 1000 | 1000 |

## 14. File Integrity

- **CSV hash unchanged after audit:** True ✓

---
*End of audit report.*
