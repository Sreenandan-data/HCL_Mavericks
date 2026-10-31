# Prediction Contract: Next Bill Amount Prediction

**Version:** 0.1-draft  
**Status:** Pending reviewer approval  
**Date:** 2026-10-31  
**Dataset:** `next_bill_amount_prediction_synthetic_dataset.csv`  
**SHA-256:** `1591046b1a25f22bb6da7f5ff18f84281afcfd62bbf3e7afd582607b15c8859f`

---

## 1. Forecast Definition

| Property | Value |
|----------|-------|
| **Forecast horizon** | One calendar month ahead |
| **Target variable** | `next_bill_amount` (the bill the customer will receive in billing_month + 1 month) |
| **Forecast origin** | Immediately after the current `billing_month` closes — all columns for that month are assumed finalized |
| **Forecast target month** | `billing_month` + 1 calendar month |
| **Granularity** | One prediction per customer per forecast origin |
| **Grouping key** | `customer_id` (not a numeric predictor) |

### Operational scenario

At the close of each billing month, the system produces a predicted next-bill amount for every active customer. The prediction uses only information available at that point: the customer's historical records up to and including the just-closed month.

---

## 2. Feature Availability Table

The table below classifies every raw column by its role, availability at the forecast origin, leakage risk, and open questions.

| Column | Role | Available at forecast origin? | Leakage risk | Notes / Open questions |
|--------|------|------------------------------|--------------|----------------------|
| `customer_id` | Grouping key | Yes | None | Used to partition histories. Not a numeric predictor by default. May be encoded as a categorical entity embedding. |
| `billing_month` | Temporal key | Yes (current and past) | **High if future months used** | The current billing_month and all prior months are available. Never use future months. Used to derive calendar features (month-of-year, time index). |
| `plan_type` | Categorical feature | Yes (current month's plan) | Low | Three values: Basic, Standard, Premium. No plan changes observed in this dataset — every customer stays on one plan across all 17 months. If plan changes occurred, only the current-month plan is available. |
| `data_usage_gb` | Numeric feature | Yes (current month) | **High if next month's value used** | Current month's usage is finalized. Next month's usage is unknown and must not be used as a predictor. |
| `voice_calls` | Numeric feature | Yes (current month) | **High if next month's value used** | Same availability constraint as `data_usage_gb`. |
| `sms_count` | Numeric feature | Yes (current month) | **High if next month's value used** | Same availability constraint. |
| `addon_data_gb` | Numeric feature | Yes (current month) | **High if next month's value used** | Only 3 distinct values (0.0, 5.0, 10.0). 84.5% of rows are 0.0. Sparse signal. |
| `plan_fee` | Numeric feature | Yes (current month) | Low | Strongly tied to `plan_type`. Only 3 distinct values (199, 399, 699). Likely stable if plan doesn't change, but contractually available only for the current month. |
| `discount_amount` | Numeric feature | Yes (current month) | Low | 4 distinct values (0, 25, 50, 75). 65.2% are zero. May correlate with plan or tenure. |
| `data_charge` | Numeric / derived | Yes (current month) | Moderate — may be derivable from usage | 60.1% are zero. Appears plan-dependent: charges may only apply when usage exceeds an included allowance. Relationship with `data_usage_gb` should be investigated. |
| `voice_charge` | Numeric / derived | Yes (current month) | Moderate | 73.2% are zero. Similar pattern to `data_charge`. |
| `addon_charge` | Numeric / derived | Yes (current month) | Low | Perfectly correlated with `addon_data_gb` (both zero when no addon). Only 3 values (0, 50, 100). |
| `tax_amount` | Numeric / derived | Yes (current month) | Moderate — likely derived from pre-tax bill | Appears to be a percentage of pre-tax charges. Relationship should be verified. |
| `bill_amount` | Numeric / derived | Yes (current month) | Moderate — using ONLY current/past month is safe | Current month's finalized bill. This is the single strongest predictor in a naive baseline. **The next month's bill_amount is the target itself** — never available as a feature. |
| `next_bill_amount` | **TARGET** | **NEVER available as a feature** | **CRITICAL** | This is the prediction target. It equals the following month's `bill_amount` for all 16,000 verifiable rows. The 1,000 terminal rows (May 2025) carry target values for June 2025 that cannot be verified against observed data. |

### Critical leakage safeguards

1. **`next_bill_amount` must be excluded from all feature sets.** It is the label, never an input.
2. **No future-month data.** When predicting month M+1 from origin month M, only rows with `billing_month <= M` for that customer may contribute features.
3. **Aggregated historical features** (rolling means, lags, trends) must use only records at or before the forecast origin.
4. **Target-derived aggregates are forbidden.** Never compute statistics over `next_bill_amount` and feed them back as features (including global or segment-level averages of the target).

---

## 3. Target Verification

### 3.1 Alignment with observed bills

The audit verified target semantics by matching each row's `next_bill_amount` to the same customer's `bill_amount` in the exact next calendar month:

| Metric | Value |
|--------|-------|
| Total rows | 17,000 |
| Rows with an observed next calendar month | 16,000 |
| Exact matches (absolute diff <= 0.01) | 16,000 (100%) |
| Mismatches | 0 |
| Maximum absolute difference | 0.000000 |
| Rows without observed next month | 1,000 |
| — of which terminal rows (May 2025) | 1,000 |
| — of which mid-history gap rows | 0 |

**Conclusion:** For all 16,000 non-terminal rows, `next_bill_amount` exactly equals the customer's `bill_amount` in the following calendar month. The target column is consistent and usable for retrospective evaluation.

### 3.2 Terminal-row targets (May 2025)

Each customer's May 2025 row carries a `next_bill_amount` value representing June 2025, which is **beyond the dataset boundary**. The supplied data **cannot verify** whether these 1,000 values are:
- Genuinely generated from the same billing model (likely, given the synthetic nature)
- Synthetic placeholders with no corresponding record

**Recommendation:** These terminal targets are usable for test evaluation under the assumption that they were generated by the same synthetic process. This assumption should be stated explicitly in any results report.

### 3.3 Bill component reconciliation

**Tested equation:** `bill_amount = plan_fee - discount_amount + data_charge + voice_charge + addon_charge + tax_amount`

| Statistic | Value |
|-----------|-------|
| Residual mean | 0.000015 |
| Residual std | 0.003134 |
| Residual min | -0.01 |
| Residual max | +0.01 |
| Mean |residual| | 0.000982 |
| Exact matches (within 0.01) | 16,648 / 17,000 (97.9%) |

**Conclusion:** The candidate equation explains `bill_amount` to within floating-point rounding error (max |residual| = 0.01, attributable to cent-level rounding). The 352 non-exact-match rows all have residuals of exactly +/-0.01. This equation is effectively the generation formula, but we state this as strong evidence, not proven fact.

---

## 4. Dataset Properties Summary

| Property | Value |
|----------|-------|
| Rows | 17,000 |
| Columns | 15 |
| Customers | 1,000 |
| Date range | 2024-01-01 to 2025-05-01 |
| Distinct months | 17 |
| Rows per month | Exactly 1,000 |
| History per customer | Exactly 17 months (balanced panel) |
| Missing values | 0 (any column) |
| Duplicate rows | 0 |
| Duplicate (customer, month) keys | 0 |
| Internal gaps | 0 |
| Negative values | 0 (any column) |
| Non-finite values | 0 |
| Plan types | Basic (6,987), Standard (7,038), Premium (2,975) |
| Plan changes | 0 (no customer changes plan) |
| Original sort order | Sorted by (customer_id, billing_month) |

---

## 5. Chronological Evaluation Proposal

### 5.1 Design principles

- **No random splitting.** All partitions respect chronological order.
- **Forecast origin determines the partition.** A row belongs to the partition defined by its billing_month (the origin), not its target month.
- **The final test set is untouched** during model selection, hyperparameter tuning, and threshold calibration.

### 5.2 Proposed partitions

| Partition | Origin months | Target months | Rows | Customers | Purpose |
|-----------|--------------|---------------|------|-----------|---------|
| **Train** | 2024-01 through 2025-02 (14 months) | 2024-02 through 2025-03 | 14,000 | 1,000 | Model fitting and feature engineering |
| **Validation** | 2025-03 (1 month) | 2025-04 | 1,000 | 1,000 | Hyperparameter tuning, threshold calibration, model selection |
| **Test** | 2025-04 (1 month) | 2025-05 | 1,000 | 1,000 | Final held-out evaluation |

> **Note on May 2025 origin rows:** The 1,000 rows with `billing_month = 2025-05` have target month June 2025 (outside the dataset). These can serve as an **additional forward test** if the terminal targets are trusted. They are excluded from the primary three-way split above.

### 5.3 Label availability at each forecast origin

A row originating in month M receives its label only when month M+1 closes.
At a January close, January's next-bill label is not yet available. At a June
close, labels through the May origin are available. At the February 2025 close,
labels through January 2025 are available. The proposed training partition
through February can therefore be fitted at the March 2025 close, when March
bills have finalized, for the validation forecast of April. At the April close,
March-origin validation labels have become available; an optional final refit
must be documented separately from fixed-model evaluation.

### 5.4 Fixed model vs. rolling operational setup

Two distinct evaluation paradigms should be documented:

1. **Fixed model, single-origin evaluation:** Train a model once on training data. Evaluate on the validation origin (2025-03) and test origin (2025-04). Each customer gets exactly one prediction per partition. This is the primary evaluation mode.

2. **Rolling operational simulation:** At each monthly origin from 2025-03 onward, the model could be retrained or updated with newly realized bills. Earlier months from the "test" period become available as historical inputs at later origins. This dataset's balanced panel means rolling evaluation adds limited information (only 2 additional origins), but the concept should be documented for production deployment.

**Recommendation for this hackathon:** Use the fixed-model single-origin evaluation as the primary evaluation, with a note that rolling retraining is the production-realistic approach.

### 5.5 Proposed baselines

| Baseline | Definition | Short-history fallback | Development-set performance |
|----------|-----------|----------------------|---------------------------|
| **Previous bill** | Predict `next_bill_amount = bill_amount` (current month) | Always available (every row has a current bill) | MAE=66.69, RMSE=101.36, WAPE=12.87% |
| **Trailing 3-month mean** | Mean of the customer's last 3 `bill_amount` values | For customers with < 3 months: use available mean (2-month or 1-month) | MAE=57.67, RMSE=85.87, WAPE=11.13% |

> Baseline metrics above are computed on all 16,000 verified rows. Test-set-specific baseline metrics should be computed separately and reported alongside model metrics.

### 5.6 Proposed metrics

| Metric | Formula | Zero-denominator handling |
|--------|---------|--------------------------|
| **MAE** | Mean of |actual - predicted| | Always defined if n > 0 |
| **RMSE** | sqrt(Mean of (actual - predicted)^2) | Always defined if n > 0 |
| **WAPE** | Sum(|actual - predicted|) / Sum(actual) | Report as undefined if Sum(actual) = 0; in this dataset min bill is 146.32 so not a concern |

All metrics should be reported:
- **Overall** on the full test set
- **Segmented** by plan_type, bill-amount quartile, and history length (if variable; here all customers have 17 months)

### 5.7 High-bill flagging proposal

**Definition (to be calibrated on development data only):**

A customer's predicted bill is flagged as "high" if it exceeds their historical baseline by a threshold. Two candidate rules:

1. **Absolute z-score rule:** Flag if predicted bill > customer's trailing-mean + k * trailing-std (e.g., k = 2).
2. **Relative increase rule:** Flag if predicted bill > trailing-mean * (1 + p) (e.g., p = 0.30 for a 30% increase).

**Calibration approach:**
- Compute thresholds on training + validation data
- Evaluate precision and recall of flags against actual high bills in the validation set
- **Do not tune thresholds on the test set**

**Evaluation metrics for flags:**
- Precision: fraction of flagged customers whose actual bill was truly high
- Recall: fraction of truly high bills that were flagged
- A "truly high" bill is defined by the same rule applied to the actual `next_bill_amount`

### 5.8 Uncertainty calibration proposal

- Use prediction intervals (e.g., from quantile regression or conformal prediction) calibrated on the validation set
- Report empirical coverage: fraction of actual bills falling within the predicted interval
- Target 90% coverage interval
- Do not calibrate on the test set

---

## 6. Unresolved Questions and Assumptions

### Assumptions (require explicit acknowledgment)

1. **Availability assumption:** All columns for the current billing month are finalized and available at the forecast origin. In production, some fields (e.g., tax_amount) might be computed later.
2. **Terminal target validity:** The 1,000 May 2025 `next_bill_amount` values are assumed valid despite no corresponding June 2025 records.
3. **Synthetic data:** All findings describe this specific synthetic dataset. They should not be extrapolated to real customer billing without further validation.
4. **Static plans:** No plan changes are observed. The model may not generalize to scenarios with mid-period plan changes.

### Open questions for reviewer

1. **Tax computation:** `tax_amount` appears to be approximately 18% of pre-tax charges (`plan_fee - discount_amount + data_charge + voice_charge + addon_charge`). Should we verify and document this rate? If tax is a deterministic function of other charges, it carries no independent information.

2. **Data-charge structure:** `data_charge` is zero for ~60% of rows and appears to depend on plan type and usage level (suggesting an included-data allowance). Should we reverse-engineer the charging rules, or treat charges as opaque features?

3. **Discount logic:** Only 4 discount values (0, 25, 50, 75) are observed. The assignment mechanism is unclear. Is it tenure-based, promotional, or random?

4. **May 2025 test targets:** Should the 1,000 terminal rows be included in the final test evaluation, or held as an optional forward test?

5. **Production retraining:** Should the evaluation simulate monthly retraining (rolling), or evaluate a single fixed model?

6. **Customer-level explanation method:** SHAP, LIME, or simpler feature-importance approaches — does the reviewer have a preference?

---

## 7. Candidate Feature Engineering Directions

> These are proposed directions only, not implemented features. Listed for reviewer awareness.

- **Lag features:** bill_amount_lag1, bill_amount_lag2, bill_amount_lag3, usage_lag1, etc.
- **Rolling statistics:** 3-month and 6-month rolling mean, std, min, max of bill and usage features
- **Trend features:** Month-over-month bill change, linear trend slope over recent history
- **Calendar features:** Month-of-year (for seasonality), months-since-first-bill
- **Plan-interaction features:** Usage relative to plan tier, overage indicators
- **Cross-component ratios:** data_charge / bill_amount, tax_amount / pre-tax total

---

*This contract is subject to reviewer approval before any modeling work begins.*


## 8. Implemented preprocessing

`notebooks/01_data_preprocessing.ipynb` implements causal lags, trailing means,
bill variability, calendar features, charge indicators and training-only
preprocessing. Model selection and evaluation remain proposed work. Audit
baseline scores in section 5.5 use all verified rows, including holdouts, and
must be treated as descriptive rather than independent development estimates.
