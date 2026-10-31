#!/usr/bin/env python3
"""
Dataset Audit Script for HCLTech Next Bill Amount Prediction
=============================================================
Performs a comprehensive, reproducible audit of the raw CSV dataset.
Outputs:
  - reports/data_audit.json   (machine-readable findings)
  - reports/data_audit.md     (human-readable report)

Usage:
    python scripts/audit_data.py

Dependencies: pandas, numpy  (python-docx only needed for docx reading, not here)
"""

import hashlib
import json
import os
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WORKSPACE = Path(__file__).resolve().parent.parent
CSV_PATH = WORKSPACE / "data" / "next_bill_amount_prediction_synthetic_dataset.csv"
REPORT_DIR = WORKSPACE / "reports"
REPORT_DIR.mkdir(exist_ok=True)

EXPECTED_COLUMNS = [
    "customer_id", "billing_month", "plan_type", "data_usage_gb",
    "voice_calls", "sms_count", "addon_data_gb", "plan_fee",
    "discount_amount", "data_charge", "voice_charge", "addon_charge",
    "tax_amount", "bill_amount", "next_bill_amount",
]

ABS_TOL = 0.01  # tolerance for float comparisons

findings = OrderedDict()  # accumulates all audit findings


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ===================================================================
# 1. FILE INTEGRITY
# ===================================================================
print("=" * 70)
print("SECTION 1: File Integrity")
print("=" * 70)

assert CSV_PATH.exists(), f"CSV not found at {CSV_PATH}"
csv_hash = sha256_file(CSV_PATH)
csv_size = CSV_PATH.stat().st_size
print(f"CSV path : {CSV_PATH}")
print(f"SHA-256  : {csv_hash}")
print(f"File size: {csv_size:,} bytes")
findings["file"] = {
    "path": str(CSV_PATH),
    "sha256": csv_hash,
    "size_bytes": csv_size,
}

# ===================================================================
# 2. LOAD AND BASIC SHAPE
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 2: Shape, Columns, Types")
print("=" * 70)

df = pd.read_csv(CSV_PATH)
print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
print(f"Columns: {list(df.columns)}")

# Column verification
missing_cols = [c for c in EXPECTED_COLUMNS if c not in df.columns]
extra_cols = [c for c in df.columns if c not in EXPECTED_COLUMNS]
assert len(missing_cols) == 0, f"Missing expected columns: {missing_cols}"
if extra_cols:
    print(f"  Extra columns (unexpected): {extra_cols}")
print("  All 15 expected columns present: YES")

col_dtypes = {c: str(df[c].dtype) for c in df.columns}
print(f"  Dtypes: {col_dtypes}")

findings["shape"] = {
    "rows": int(df.shape[0]),
    "columns": int(df.shape[1]),
    "column_names": list(df.columns),
    "dtypes": col_dtypes,
    "missing_expected_columns": missing_cols,
    "extra_columns": extra_cols,
}

# ===================================================================
# 3. MISSING VALUES AND UNIQUE COUNTS
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 3: Missing Values and Unique Counts")
print("=" * 70)

missing_counts = df.isnull().sum().to_dict()
unique_counts = df.nunique().to_dict()
for c in df.columns:
    print(f"  {c:30s}  missing={missing_counts[c]:5d}  unique={unique_counts[c]:6d}")

findings["missing"] = {k: int(v) for k, v in missing_counts.items()}
findings["unique"] = {k: int(v) for k, v in unique_counts.items()}
findings["total_missing"] = int(df.isnull().sum().sum())

# ===================================================================
# 4. DATE PARSING AND RANGE
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 4: Date Parsing and Range")
print("=" * 70)

df["billing_month_dt"] = pd.to_datetime(df["billing_month"], errors="coerce")
date_parse_failures = int(df["billing_month_dt"].isnull().sum())
print(f"  Date parse failures: {date_parse_failures}")
assert date_parse_failures == 0, f"{date_parse_failures} dates failed to parse"

min_date = df["billing_month_dt"].min()
max_date = df["billing_month_dt"].max()
distinct_months = sorted(df["billing_month_dt"].unique())
n_distinct_months = len(distinct_months)
print(f"  Date range: {min_date.date()} to {max_date.date()}")
print(f"  Distinct months: {n_distinct_months}")
print(f"  Month list: {[str(d.date()) for d in distinct_months]}")

# Check all dates are 1st of month
non_first = df[df["billing_month_dt"].dt.day != 1]
print(f"  Rows where day != 1: {len(non_first)}")

findings["dates"] = {
    "parse_failures": date_parse_failures,
    "min_date": str(min_date.date()),
    "max_date": str(max_date.date()),
    "distinct_months": n_distinct_months,
    "month_list": [str(d.date()) for d in distinct_months],
    "non_first_of_month_rows": int(len(non_first)),
}

# ===================================================================
# 5. CUSTOMERS
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 5: Customer Analysis")
print("=" * 70)

n_customers = df["customer_id"].nunique()
print(f"  Number of distinct customers: {n_customers}")

# Per-month row counts
month_counts = df.groupby("billing_month").size().to_dict()
print("  Per-month row counts:")
for m, c in sorted(month_counts.items()):
    print(f"    {m}: {c}")

findings["customers"] = {
    "n_customers": int(n_customers),
    "per_month_row_counts": {str(k): int(v) for k, v in sorted(month_counts.items())},
}

# Customer history-length distribution
cust_history = df.groupby("customer_id").size()
hist_dist = cust_history.value_counts().sort_index().to_dict()
print(f"  Customer history-length distribution (months -> count of customers):")
for length, count in sorted(hist_dist.items()):
    print(f"    {length} months: {count} customers")

findings["customers"]["history_length_distribution"] = {
    str(k): int(v) for k, v in sorted(hist_dist.items())
}
findings["customers"]["history_length_stats"] = {
    "min": int(cust_history.min()),
    "max": int(cust_history.max()),
    "mean": round(float(cust_history.mean()), 2),
    "median": int(cust_history.median()),
}

# ===================================================================
# 6. DUPLICATES
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 6: Duplicate Analysis")
print("=" * 70)

# Complete row duplicates
full_dupes = int(df.duplicated().sum())
print(f"  Duplicate complete rows: {full_dupes}")

# Customer-month key duplicates
key_dupes = int(df.duplicated(subset=["customer_id", "billing_month"]).sum())
print(f"  Duplicate (customer_id, billing_month) keys: {key_dupes}")
if key_dupes > 0:
    dupe_examples = df[df.duplicated(subset=["customer_id", "billing_month"], keep=False)]
    print(f"    Examples: {dupe_examples[['customer_id','billing_month']].head(10).to_string()}")

findings["duplicates"] = {
    "complete_row_duplicates": full_dupes,
    "customer_month_key_duplicates": key_dupes,
}

# ===================================================================
# 7. SORT ORDER
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 7: Sort Order Check")
print("=" * 70)

df_sorted = df.sort_values(["customer_id", "billing_month_dt"]).reset_index(drop=True)
is_sorted = df.equals(df_sorted[df.columns])
# More lenient check: compare the key columns
is_sorted_by_key = (
    (df["customer_id"].values == df_sorted["customer_id"].values).all()
    and (df["billing_month_dt"].values == df_sorted["billing_month_dt"].values).all()
)
print(f"  Data sorted by (customer_id, billing_month): {is_sorted_by_key}")

# Use sorted version going forward
df = df_sorted.copy()
findings["sort_order"] = {"sorted_by_customer_month": bool(is_sorted_by_key)}

# ===================================================================
# 8. MISSING MONTHS WITHIN CUSTOMER HISTORIES
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 8: Missing Months Within Customer Histories")
print("=" * 70)

gap_records = []
for cid, grp in df.groupby("customer_id"):
    months = sorted(grp["billing_month_dt"].values)
    for i in range(1, len(months)):
        prev = pd.Timestamp(months[i - 1])
        curr = pd.Timestamp(months[i])
        expected_next = prev + pd.DateOffset(months=1)
        if curr != expected_next:
            gap_records.append({
                "customer_id": str(cid),
                "from_month": str(prev.date()),
                "to_month": str(curr.date()),
                "expected": str(expected_next.date()),
                "gap_months": int((curr.year - prev.year) * 12 + curr.month - prev.month - 1),
            })

print(f"  Total customers with internal gaps: {len(set(r['customer_id'] for r in gap_records))}")
print(f"  Total gap instances: {len(gap_records)}")
if gap_records:
    print(f"  First 5 gaps: {gap_records[:5]}")

findings["internal_gaps"] = {
    "customers_with_gaps": len(set(r["customer_id"] for r in gap_records)),
    "total_gap_instances": len(gap_records),
    "examples": gap_records[:10],
}

# ===================================================================
# 9. NUMERIC SUMMARIES
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 9: Numeric Summaries")
print("=" * 70)

numeric_cols = [
    "data_usage_gb", "voice_calls", "sms_count", "addon_data_gb",
    "plan_fee", "discount_amount", "data_charge", "voice_charge",
    "addon_charge", "tax_amount", "bill_amount", "next_bill_amount",
]

desc = df[numeric_cols].describe().round(4)
print(desc.to_string())

# Zero, negative, nonfinite counts
zero_counts = {}
negative_counts = {}
nonfinite_counts = {}
for c in numeric_cols:
    zero_counts[c] = int((df[c] == 0).sum())
    negative_counts[c] = int((df[c] < 0).sum())
    nonfinite_counts[c] = int((~np.isfinite(df[c].astype(float))).sum())

print("\n  Zero-value counts:")
for c in numeric_cols:
    if zero_counts[c] > 0:
        print(f"    {c}: {zero_counts[c]}")

print("\n  Negative-value counts:")
has_neg = False
for c in numeric_cols:
    if negative_counts[c] > 0:
        print(f"    {c}: {negative_counts[c]}")
        has_neg = True
if not has_neg:
    print("    (none)")

print("\n  Non-finite (inf/NaN) counts:")
has_nonfinite = False
for c in numeric_cols:
    if nonfinite_counts[c] > 0:
        print(f"    {c}: {nonfinite_counts[c]}")
        has_nonfinite = True
if not has_nonfinite:
    print("    (none)")

findings["numeric_summary"] = {
    "describe": {c: desc[c].to_dict() for c in numeric_cols},
    "zero_counts": zero_counts,
    "negative_counts": negative_counts,
    "nonfinite_counts": nonfinite_counts,
}

# ===================================================================
# 10. PLAN CATEGORIES AND PLAN CHANGES
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 10: Plan Categories and Changes")
print("=" * 70)

plan_values = df["plan_type"].value_counts().to_dict()
print(f"  Plan types: {plan_values}")

# Plan changes within customers
plan_changes = []
for cid, grp in df.groupby("customer_id"):
    plans = grp.sort_values("billing_month_dt")["plan_type"].values
    for i in range(1, len(plans)):
        if plans[i] != plans[i - 1]:
            plan_changes.append({
                "customer_id": str(cid),
                "from_plan": str(plans[i - 1]),
                "to_plan": str(plans[i]),
                "month_index": i,
            })

customers_with_changes = len(set(r["customer_id"] for r in plan_changes))
print(f"  Total plan-change events: {len(plan_changes)}")
print(f"  Customers with at least one plan change: {customers_with_changes}")

# Transition matrix
if plan_changes:
    transitions = {}
    for pc in plan_changes:
        key = f"{pc['from_plan']} -> {pc['to_plan']}"
        transitions[key] = transitions.get(key, 0) + 1
    print(f"  Plan transitions: {transitions}")
    findings["plan_analysis"] = {
        "plan_value_counts": {str(k): int(v) for k, v in plan_values.items()},
        "total_plan_changes": len(plan_changes),
        "customers_with_changes": customers_with_changes,
        "transition_counts": transitions,
        "examples": plan_changes[:10],
    }
else:
    findings["plan_analysis"] = {
        "plan_value_counts": {str(k): int(v) for k, v in plan_values.items()},
        "total_plan_changes": 0,
        "customers_with_changes": 0,
    }

# ===================================================================
# 11. SUSPICIOUS EXTREME VALUES
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 11: Suspicious Extreme Values")
print("=" * 70)

extremes = {}
for c in numeric_cols:
    q1 = df[c].quantile(0.01)
    q99 = df[c].quantile(0.99)
    iqr = df[c].quantile(0.75) - df[c].quantile(0.25)
    lower = df[c].quantile(0.25) - 3.0 * iqr
    upper = df[c].quantile(0.75) + 3.0 * iqr
    n_low = int((df[c] < lower).sum())
    n_high = int((df[c] > upper).sum())
    extremes[c] = {
        "p01": round(float(q1), 4),
        "p99": round(float(q99), 4),
        "iqr": round(float(iqr), 4),
        "lower_3iqr": round(float(lower), 4),
        "upper_3iqr": round(float(upper), 4),
        "n_below_lower": n_low,
        "n_above_upper": n_high,
        "min": round(float(df[c].min()), 4),
        "max": round(float(df[c].max()), 4),
    }
    if n_low > 0 or n_high > 0:
        print(f"  {c}: {n_low} below 3×IQR ({lower:.2f}), {n_high} above 3×IQR ({upper:.2f}), range [{df[c].min():.2f}, {df[c].max():.2f}]")

findings["extreme_values"] = extremes

# ===================================================================
# 12. TARGET SEMANTICS: next_bill_amount vs next month's bill_amount
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 12: Target Alignment (next_bill_amount verification)")
print("=" * 70)

df = df.sort_values(["customer_id", "billing_month_dt"]).reset_index(drop=True)

# Build a lookup: (customer_id, month) -> bill_amount
bill_lookup = {}
for _, row in df.iterrows():
    key = (row["customer_id"], row["billing_month_dt"])
    bill_lookup[key] = row["bill_amount"]

# For each row, find the EXACT next calendar month for that customer
matched = 0
mismatched = 0
mismatch_examples = []
no_next_month = 0
no_next_month_examples = []
max_abs_diff = 0.0
abs_diffs = []

for idx, row in df.iterrows():
    cid = row["customer_id"]
    current_month = row["billing_month_dt"]
    target = row["next_bill_amount"]
    exact_next = current_month + pd.DateOffset(months=1)

    next_bill = bill_lookup.get((cid, exact_next))

    if next_bill is not None:
        diff = abs(target - next_bill)
        abs_diffs.append(diff)
        if diff > max_abs_diff:
            max_abs_diff = diff
        if diff <= ABS_TOL:
            matched += 1
        else:
            mismatched += 1
            if len(mismatch_examples) < 10:
                mismatch_examples.append({
                    "customer_id": str(cid),
                    "billing_month": str(current_month.date()),
                    "next_bill_amount": round(float(target), 4),
                    "actual_next_bill": round(float(next_bill), 4),
                    "abs_diff": round(float(diff), 4),
                })
    else:
        no_next_month += 1
        if len(no_next_month_examples) < 10:
            no_next_month_examples.append({
                "customer_id": str(cid),
                "billing_month": str(current_month.date()),
                "next_bill_amount": round(float(target), 4),
                "expected_next_month": str(exact_next.date()),
            })

total_with_next = matched + mismatched
print(f"  Rows with an observed exact next calendar month: {total_with_next}")
print(f"  Matched (|diff| <= {ABS_TOL}): {matched}")
print(f"  Mismatched: {mismatched}")
print(f"  Max absolute difference: {max_abs_diff:.6f}")
if abs_diffs:
    print(f"  Mean absolute difference: {np.mean(abs_diffs):.6f}")
    print(f"  Median absolute difference: {np.median(abs_diffs):.6f}")
print(f"  Rows WITHOUT observed next calendar month: {no_next_month}")

if mismatch_examples:
    print(f"  Mismatch examples:")
    for ex in mismatch_examples[:5]:
        print(f"    {ex}")

if no_next_month_examples:
    print(f"  No-next-month examples (first 5):")
    for ex in no_next_month_examples[:5]:
        print(f"    {ex}")

# Categorize no-next-month rows
terminal_rows = df.groupby("customer_id")["billing_month_dt"].max().reset_index()
terminal_rows.columns = ["customer_id", "last_month"]
terminal_set = set(zip(terminal_rows["customer_id"], terminal_rows["last_month"]))

terminal_count = 0
gap_count = 0
for ex_idx, row in df.iterrows():
    cid = row["customer_id"]
    current_month = row["billing_month_dt"]
    exact_next = current_month + pd.DateOffset(months=1)
    if (cid, exact_next) not in bill_lookup:
        if (cid, current_month) in terminal_set:
            terminal_count += 1
        else:
            gap_count += 1

print(f"\n  No-next-month breakdown:")
print(f"    Terminal rows (customer's last month): {terminal_count}")
print(f"    Gap rows (mid-history missing next): {gap_count}")

findings["target_alignment"] = {
    "total_rows": int(df.shape[0]),
    "rows_with_next_month": total_with_next,
    "matched": matched,
    "mismatched": mismatched,
    "max_abs_diff": round(float(max_abs_diff), 6),
    "mean_abs_diff": round(float(np.mean(abs_diffs)), 6) if abs_diffs else None,
    "rows_without_next_month": no_next_month,
    "terminal_rows": terminal_count,
    "gap_rows": gap_count,
    "mismatch_examples": mismatch_examples,
    "no_next_month_examples": no_next_month_examples[:5],
    "tolerance_used": ABS_TOL,
}

# ===================================================================
# 13. BILL COMPONENT RECONCILIATION
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 13: Bill Component Reconciliation")
print("=" * 70)

# Candidate equation: bill_amount = plan_fee - discount_amount + data_charge + voice_charge + addon_charge + tax_amount
df["recon_bill"] = (
    df["plan_fee"]
    - df["discount_amount"]
    + df["data_charge"]
    + df["voice_charge"]
    + df["addon_charge"]
    + df["tax_amount"]
)
df["recon_residual"] = df["bill_amount"] - df["recon_bill"]

recon_stats = {
    "candidate_equation": "bill_amount = plan_fee - discount_amount + data_charge + voice_charge + addon_charge + tax_amount",
    "residual_mean": round(float(df["recon_residual"].mean()), 6),
    "residual_std": round(float(df["recon_residual"].std()), 6),
    "residual_min": round(float(df["recon_residual"].min()), 6),
    "residual_max": round(float(df["recon_residual"].max()), 6),
    "residual_median": round(float(df["recon_residual"].median()), 6),
    "residual_abs_mean": round(float(df["recon_residual"].abs().mean()), 6),
    "exact_match_count": int((df["recon_residual"].abs() <= ABS_TOL).sum()),
    "total_rows": int(df.shape[0]),
}

print(f"  Candidate equation: {recon_stats['candidate_equation']}")
print(f"  Residual mean:   {recon_stats['residual_mean']}")
print(f"  Residual std:    {recon_stats['residual_std']}")
print(f"  Residual min:    {recon_stats['residual_min']}")
print(f"  Residual max:    {recon_stats['residual_max']}")
print(f"  Residual median: {recon_stats['residual_median']}")
print(f"  Mean |residual|: {recon_stats['residual_abs_mean']}")
print(f"  Exact matches (|res| <= {ABS_TOL}): {recon_stats['exact_match_count']} / {recon_stats['total_rows']}")

if recon_stats["exact_match_count"] < recon_stats["total_rows"]:
    bad_recon = df[df["recon_residual"].abs() > ABS_TOL].head(5)
    print("  Non-matching examples:")
    for _, r in bad_recon.iterrows():
        print(f"    cust={r['customer_id']} month={r['billing_month']} "
              f"bill={r['bill_amount']:.2f} recon={r['recon_bill']:.2f} "
              f"residual={r['recon_residual']:.4f}")

findings["bill_reconciliation"] = recon_stats

# ===================================================================
# 14. CHRONOLOGICAL SPLIT PROPOSAL
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 14: Chronological Split Proposal")
print("=" * 70)

all_months = sorted(df["billing_month_dt"].unique())
n_months_total = len(all_months)
print(f"  Total distinct months: {n_months_total}")
print(f"  Months: {[str(pd.Timestamp(m).date()) for m in all_months]}")

# Propose split based on actual months
# We need enough history for training and a clean test period
# Typical: last 2 months for test, 1-2 months for validation, rest for training
# But this depends on actual month count

# Compute row/customer counts per month
month_info = []
for m in all_months:
    mask = df["billing_month_dt"] == m
    month_info.append({
        "month": str(pd.Timestamp(m).date()),
        "rows": int(mask.sum()),
        "customers": int(df.loc[mask, "customer_id"].nunique()),
    })

# Split proposal
if n_months_total >= 6:
    # Train: all but last 3 months, Val: 2nd-to-last and 3rd-to-last target months, Test: last target month
    # For a 1-month-ahead prediction:
    #   - To predict month M, we need features up to month M-1
    #   - Training labels are next_bill_amount for training months
    #   - The "test target month" is the last month
    #   - The "test origin month" is the second-to-last month
    test_target_month = all_months[-1]
    test_origin_month = all_months[-2]
    val_target_month = all_months[-2]
    val_origin_month = all_months[-3]
    train_months = all_months[:-2]  # features months; labels from next_bill_amount
    train_label_months = all_months[:-2]  # rows whose next_bill_amount is used for training

    # Actually, let's be more precise:
    # Train set: rows from months[0] to months[-3] (their next_bill_amount is the label, target months are months[1] to months[-2])
    # Val set: rows from month[-3] (origin), predicting month[-2] target
    # Test set: rows from month[-2] (origin), predicting month[-1] target

    train_origin_months = all_months[:-3]
    val_origin_months_list = [all_months[-3]]
    test_origin_months_list = [all_months[-2]]

    train_mask = df["billing_month_dt"].isin(train_origin_months)
    val_mask = df["billing_month_dt"] == val_origin_months_list[0]
    test_mask = df["billing_month_dt"] == test_origin_months_list[0]

    split_info = {
        "train": {
            "origin_months": [str(pd.Timestamp(m).date()) for m in train_origin_months],
            "target_months": [str((pd.Timestamp(m) + pd.DateOffset(months=1)).date()) for m in train_origin_months],
            "rows": int(train_mask.sum()),
            "customers": int(df.loc[train_mask, "customer_id"].nunique()),
        },
        "validation": {
            "origin_month": str(pd.Timestamp(val_origin_months_list[0]).date()),
            "target_month": str(pd.Timestamp(val_target_month).date()),
            "rows": int(val_mask.sum()),
            "customers": int(df.loc[val_mask, "customer_id"].nunique()),
        },
        "test": {
            "origin_month": str(pd.Timestamp(test_origin_months_list[0]).date()),
            "target_month": str(pd.Timestamp(test_target_month).date()),
            "rows": int(test_mask.sum()),
            "customers": int(df.loc[test_mask, "customer_id"].nunique()),
        },
    }
else:
    split_info = {"error": f"Only {n_months_total} months available; manual split design needed."}

print(f"  Proposed split:")
print(json.dumps(split_info, indent=4))

findings["chronological_split"] = split_info
findings["month_detail"] = month_info

# ===================================================================
# 15. BASELINE ESTIMATES
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 15: Baseline Feasibility Check")
print("=" * 70)

# Previous-bill baseline: next_bill_amount ≈ bill_amount
# Trailing 3-bill mean baseline
# Only compute on rows that have a verified next month

eval_mask = df["recon_residual"].notna()  # all rows
# For baseline evaluation, use rows where next_bill_amount can be verified
# i.e., rows that have a matching next calendar month

verified_indices = []
for idx, row in df.iterrows():
    cid = row["customer_id"]
    exact_next = row["billing_month_dt"] + pd.DateOffset(months=1)
    if (cid, exact_next) in bill_lookup:
        verified_indices.append(idx)

df_verified = df.loc[verified_indices].copy()
print(f"  Verified rows for baseline computation: {len(df_verified)}")

if len(df_verified) > 0:
    # Previous-bill baseline
    prev_bill_errors = (df_verified["next_bill_amount"] - df_verified["bill_amount"]).abs()
    prev_mae = float(prev_bill_errors.mean())
    prev_rmse = float(np.sqrt((prev_bill_errors ** 2).mean()))
    total_actual = float(df_verified["next_bill_amount"].sum())
    prev_wape = float(prev_bill_errors.sum() / total_actual) if total_actual != 0 else float("nan")

    print(f"  Previous-bill baseline:")
    print(f"    MAE:  {prev_mae:.4f}")
    print(f"    RMSE: {prev_rmse:.4f}")
    print(f"    WAPE: {prev_wape:.4f}")

    # Trailing 3-month mean baseline
    df["bill_lag1"] = df.groupby("customer_id")["bill_amount"].shift(0)  # current
    df["bill_lag2"] = df.groupby("customer_id")["bill_amount"].shift(1)  # previous
    df["bill_lag3"] = df.groupby("customer_id")["bill_amount"].shift(2)  # 2 months ago

    df["trail3_mean"] = df[["bill_lag1", "bill_lag2", "bill_lag3"]].mean(axis=1, skipna=True)

    df_v2 = df.loc[verified_indices].copy()
    trail_valid = df_v2["trail3_mean"].notna()
    if trail_valid.sum() > 0:
        trail_errors = (df_v2.loc[trail_valid, "next_bill_amount"] - df_v2.loc[trail_valid, "trail3_mean"]).abs()
        trail_mae = float(trail_errors.mean())
        trail_rmse = float(np.sqrt((trail_errors ** 2).mean()))
        trail_total = float(df_v2.loc[trail_valid, "next_bill_amount"].sum())
        trail_wape = float(trail_errors.sum() / trail_total) if trail_total != 0 else float("nan")

        print(f"  Trailing 3-month mean baseline:")
        print(f"    MAE:  {trail_mae:.4f}")
        print(f"    RMSE: {trail_rmse:.4f}")
        print(f"    WAPE: {trail_wape:.4f}")
        print(f"    Rows with trail3 available: {int(trail_valid.sum())}")
    else:
        trail_mae = trail_rmse = trail_wape = None
        print("  Trailing 3-month mean: insufficient data")

    findings["baselines"] = {
        "verified_rows": len(df_verified),
        "previous_bill": {"MAE": round(prev_mae, 4), "RMSE": round(prev_rmse, 4), "WAPE": round(prev_wape, 4)},
        "trailing_3month_mean": {
            "MAE": round(trail_mae, 4) if trail_mae else None,
            "RMSE": round(trail_rmse, 4) if trail_rmse else None,
            "WAPE": round(trail_wape, 4) if trail_wape else None,
            "valid_rows": int(trail_valid.sum()) if trail_valid is not None else 0,
        },
    }

# ===================================================================
# 16. FINAL HASH CHECK
# ===================================================================
print("\n" + "=" * 70)
print("SECTION 16: Final Integrity Check")
print("=" * 70)

final_hash = sha256_file(CSV_PATH)
hash_match = final_hash == csv_hash
print(f"  Original SHA-256: {csv_hash}")
print(f"  Final SHA-256:    {final_hash}")
print(f"  Hash unchanged:   {hash_match}")
assert hash_match, "CSV file was modified during audit!"

findings["final_integrity"] = {
    "hash_unchanged": hash_match,
    "original_hash": csv_hash,
    "final_hash": final_hash,
}

# ===================================================================
# WRITE OUTPUTS
# ===================================================================
print("\n" + "=" * 70)
print("Writing outputs...")
print("=" * 70)

# --- JSON Report ---
json_path = REPORT_DIR / "data_audit.json"
# Convert any numpy types for JSON serialization
def convert_types(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return str(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj

def deep_convert(obj):
    if isinstance(obj, dict):
        return {k: deep_convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_convert(v) for v in obj]
    else:
        return convert_types(obj)

findings_clean = deep_convert(findings)
findings_clean["audit_timestamp"] = datetime.now().isoformat()
findings_clean["script"] = "scripts/audit_data.py"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(findings_clean, f, indent=2, default=str)
print(f"  Written: {json_path}")

# --- Markdown Report ---
md_path = REPORT_DIR / "data_audit.md"
with open(md_path, "w", encoding="utf-8") as f:
    f.write("# Data Audit Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}  \n")
    f.write(f"**Script:** `scripts/audit_data.py`  \n")
    f.write(f"**CSV:** `{CSV_PATH.name}`  \n")
    f.write(f"**SHA-256:** `{csv_hash}`  \n\n")

    f.write("## 1. Dataset Shape\n\n")
    f.write(f"- **Rows:** {findings['shape']['rows']:,}\n")
    f.write(f"- **Columns:** {findings['shape']['columns']}\n")
    f.write(f"- **Expected columns present:** All 15 ✓\n")
    f.write(f"- **Extra columns:** {findings['shape']['extra_columns'] or 'None'}\n\n")

    f.write("| Column | Dtype | Missing | Unique |\n")
    f.write("|--------|-------|---------|--------|\n")
    for c in EXPECTED_COLUMNS:
        f.write(f"| `{c}` | {findings['shape']['dtypes'][c]} | {findings['missing'][c]} | {findings['unique'][c]} |\n")
    f.write("\n")

    f.write("## 2. Date Range and Months\n\n")
    f.write(f"- **Range:** {findings['dates']['min_date']} to {findings['dates']['max_date']}\n")
    f.write(f"- **Distinct months:** {findings['dates']['distinct_months']}\n")
    f.write(f"- **Date parse failures:** {findings['dates']['parse_failures']}\n")
    f.write(f"- **Non-first-of-month rows:** {findings['dates']['non_first_of_month_rows']}\n\n")

    f.write("### Per-Month Row Counts\n\n")
    f.write("| Month | Rows |\n")
    f.write("|-------|------|\n")
    for m, c in sorted(findings["customers"]["per_month_row_counts"].items()):
        f.write(f"| {m} | {c} |\n")
    f.write("\n")

    f.write("## 3. Customers\n\n")
    f.write(f"- **Distinct customers:** {findings['customers']['n_customers']}\n")
    cstats = findings['customers']['history_length_stats']
    f.write(f"- **History length:** min={cstats['min']}, max={cstats['max']}, mean={cstats['mean']}, median={cstats['median']}\n\n")
    f.write("| History Length (months) | Customer Count |\n")
    f.write("|------------------------|----------------|\n")
    for length, count in sorted(findings["customers"]["history_length_distribution"].items(), key=lambda x: int(x[0])):
        f.write(f"| {length} | {count} |\n")
    f.write("\n")

    f.write("## 4. Duplicates\n\n")
    f.write(f"- **Complete row duplicates:** {findings['duplicates']['complete_row_duplicates']}\n")
    f.write(f"- **Customer-month key duplicates:** {findings['duplicates']['customer_month_key_duplicates']}\n\n")

    f.write("## 5. Sort Order\n\n")
    f.write(f"- **Sorted by (customer_id, billing_month):** {findings['sort_order']['sorted_by_customer_month']}\n\n")

    f.write("## 6. Internal Gaps\n\n")
    f.write(f"- **Customers with gaps:** {findings['internal_gaps']['customers_with_gaps']}\n")
    f.write(f"- **Total gap instances:** {findings['internal_gaps']['total_gap_instances']}\n\n")

    f.write("## 7. Numeric Summaries\n\n")
    f.write("See `data_audit.json` for full descriptive statistics.\n\n")
    f.write("### Zero-Value Counts (notable)\n\n")
    f.write("| Column | Zero Count |\n")
    f.write("|--------|------------|\n")
    for c in numeric_cols:
        if findings["numeric_summary"]["zero_counts"][c] > 0:
            f.write(f"| `{c}` | {findings['numeric_summary']['zero_counts'][c]} |\n")
    f.write("\n")

    f.write("### Negative / Non-finite Values\n\n")
    any_neg = any(v > 0 for v in findings["numeric_summary"]["negative_counts"].values())
    any_nonf = any(v > 0 for v in findings["numeric_summary"]["nonfinite_counts"].values())
    f.write(f"- **Negative values found:** {'Yes' if any_neg else 'None'}\n")
    f.write(f"- **Non-finite values found:** {'Yes' if any_nonf else 'None'}\n\n")

    f.write("## 8. Extreme Values (3×IQR)\n\n")
    f.write("| Column | Below Lower | Above Upper | Min | Max |\n")
    f.write("|--------|-------------|-------------|-----|-----|\n")
    for c in numeric_cols:
        ev = findings["extreme_values"][c]
        if ev["n_below_lower"] > 0 or ev["n_above_upper"] > 0:
            f.write(f"| `{c}` | {ev['n_below_lower']} | {ev['n_above_upper']} | {ev['min']} | {ev['max']} |\n")
    f.write("\n")

    f.write("## 9. Plan Analysis\n\n")
    f.write("| Plan Type | Count |\n")
    f.write("|-----------|-------|\n")
    for p, c in findings["plan_analysis"]["plan_value_counts"].items():
        f.write(f"| {p} | {c} |\n")
    f.write(f"\n- **Plan changes:** {findings['plan_analysis']['total_plan_changes']}\n")
    f.write(f"- **Customers with changes:** {findings['plan_analysis']['customers_with_changes']}\n\n")
    if findings["plan_analysis"].get("transition_counts"):
        f.write("| Transition | Count |\n")
        f.write("|------------|-------|\n")
        for t, c in findings["plan_analysis"]["transition_counts"].items():
            f.write(f"| {t} | {c} |\n")
        f.write("\n")

    f.write("## 10. Target Alignment\n\n")
    ta = findings["target_alignment"]
    f.write(f"- **Total rows:** {ta['total_rows']:,}\n")
    f.write(f"- **Rows with observed next calendar month:** {ta['rows_with_next_month']:,}\n")
    f.write(f"- **Matched (|diff| ≤ {ta['tolerance_used']}):** {ta['matched']:,}\n")
    f.write(f"- **Mismatched:** {ta['mismatched']}\n")
    f.write(f"- **Max absolute difference:** {ta['max_abs_diff']}\n")
    f.write(f"- **Rows without next calendar month:** {ta['rows_without_next_month']:,}\n")
    f.write(f"  - Terminal rows: {ta['terminal_rows']}\n")
    f.write(f"  - Gap rows: {ta['gap_rows']}\n\n")

    if ta["mismatch_examples"]:
        f.write("### Mismatch Examples\n\n")
        f.write("| Customer | Month | next_bill_amount | Actual Next Bill | Diff |\n")
        f.write("|----------|-------|------------------|------------------|------|\n")
        for ex in ta["mismatch_examples"][:5]:
            f.write(f"| {ex['customer_id']} | {ex['billing_month']} | {ex['next_bill_amount']} | {ex['actual_next_bill']} | {ex['abs_diff']} |\n")
        f.write("\n")

    f.write("> **Note:** Rows without an observed next calendar month include each customer's terminal row.\n")
    f.write("> The supplied `next_bill_amount` for terminal rows cannot be verified against observed data.\n")
    f.write("> These targets may be valid (representing a future month beyond the dataset) or may be synthetic placeholders.\n\n")

    f.write("## 11. Bill Component Reconciliation\n\n")
    br = findings["bill_reconciliation"]
    f.write(f"**Candidate equation:** `{br['candidate_equation']}`\n\n")
    f.write(f"| Statistic | Value |\n")
    f.write(f"|-----------|-------|\n")
    f.write(f"| Mean residual | {br['residual_mean']} |\n")
    f.write(f"| Std residual | {br['residual_std']} |\n")
    f.write(f"| Min residual | {br['residual_min']} |\n")
    f.write(f"| Max residual | {br['residual_max']} |\n")
    f.write(f"| Median residual | {br['residual_median']} |\n")
    f.write(f"| Mean |residual| | {br['residual_abs_mean']} |\n")
    f.write(f"| Exact matches (±{ABS_TOL}) | {br['exact_match_count']} / {br['total_rows']} |\n")
    f.write("\n")

    f.write("## 12. Baseline Estimates (All Verified Rows; Descriptive Only)\n\n")
    if "baselines" in findings:
        bl = findings["baselines"]
        f.write(f"- **Verified rows used:** {bl['verified_rows']:,}\n\n")
        f.write("| Baseline | MAE | RMSE | WAPE |\n")
        f.write("|----------|-----|------|------|\n")
        pb = bl["previous_bill"]
        f.write(f"| Previous bill | {pb['MAE']} | {pb['RMSE']} | {pb['WAPE']} |\n")
        t3 = bl["trailing_3month_mean"]
        if t3["MAE"] is not None:
            f.write(f"| Trailing 3-month mean | {t3['MAE']} | {t3['RMSE']} | {t3['WAPE']} |\n")
        f.write("\n")

    f.write("## 13. Proposed Chronological Split\n\n")
    if "error" not in findings["chronological_split"]:
        cs = findings["chronological_split"]
        f.write("| Partition | Origin Month(s) | Target Month | Rows | Customers |\n")
        f.write("|-----------|-----------------|--------------|------|-----------|\n")
        tr = cs["train"]
        f.write(f"| Train | {tr['origin_months'][0]} – {tr['origin_months'][-1]} | {tr['target_months'][0]} – {tr['target_months'][-1]} | {tr['rows']} | {tr['customers']} |\n")
        vl = cs["validation"]
        f.write(f"| Validation | {vl['origin_month']} | {vl['target_month']} | {vl['rows']} | {vl['customers']} |\n")
        te = cs["test"]
        f.write(f"| Test | {te['origin_month']} | {te['target_month']} | {te['rows']} | {te['customers']} |\n")
        f.write("\n")
    else:
        f.write(f"> {findings['chronological_split']['error']}\n\n")

    f.write("## 14. File Integrity\n\n")
    f.write(f"- **CSV hash unchanged after audit:** {findings['final_integrity']['hash_unchanged']} ✓\n\n")

    f.write("---\n*End of audit report.*\n")

print(f"  Written: {md_path}")
print("\n[OK] Audit complete.")
