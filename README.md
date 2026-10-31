# HCL_Mavericks — Next Bill Amount Prediction

HCLTech Future Ready Data Science Hackathon: Use Case 2.

## Problem Statement

Predict each customer's next monthly bill amount using historical billing and usage data.
See [`data/NextBillAmountPrediction_DS_Usecase2.docx`](data/NextBillAmountPrediction_DS_Usecase2.docx) for the full brief.

## Dataset

- **File:** `data/next_bill_amount_prediction_synthetic_dataset.csv`
- **SHA-256:** `1591046b1a25f22bb6da7f5ff18f84281afcfd62bbf3e7afd582607b15c8859f`
- **Shape:** 17,000 rows × 15 columns
- **Customers:** 1,000 | **Months:** 17 (Jan 2024 – May 2025)

## Project Structure

```
HCL_Mavericks/
├── data/
│   ├── next_bill_amount_prediction_synthetic_dataset.csv   # Raw data (do not modify)
│   └── NextBillAmountPrediction_DS_Usecase2.docx           # Problem statement
├── scripts/
│   └── audit_data.py          # Dataset audit script
├── reports/
│   ├── data_audit.json        # Machine-readable audit results
│   └── data_audit.md          # Human-readable audit report
├── docs/
│   └── prediction_contract.md # Prediction contract and evaluation proposal
└── README.md                  # This file
```

## Setup

### Prerequisites

- Python 3.10+
- pip

### Dependencies

```
pandas>=2.0
numpy>=1.24
python-docx>=1.0    # only needed for reading the problem statement docx
```

Install with:

```bash
pip install pandas numpy python-docx
```

### Running the Data Audit

```bash
cd HCL_Mavericks
python scripts/audit_data.py
```

This produces:
- `reports/data_audit.json` — full machine-readable audit
- `reports/data_audit.md` — human-readable summary report

The script:
1. Verifies the CSV SHA-256 hash before and after processing
2. Validates all 15 expected columns are present
3. Checks for missing values, duplicates, date parsing, sort order
4. Verifies target alignment (next_bill_amount = next month's bill_amount)
5. Tests bill component reconciliation
6. Proposes chronological train/validation/test split
7. Computes baseline performance estimates

**The raw CSV is never modified.**

## Current Stage

**Stage 0 — Data Audit and Prediction Contract** (complete)

Key findings:
- Perfectly balanced panel: 1,000 customers × 17 months, no missing values or gaps
- Target verified: 100% match between `next_bill_amount` and next month's `bill_amount`
- Bill decomposition confirmed: `bill_amount ≈ plan_fee - discount + charges + tax` (within ±0.01 rounding)
- Baseline: trailing 3-month mean achieves MAE=57.67, WAPE=11.1%

See [`docs/prediction_contract.md`](docs/prediction_contract.md) for the full evaluation proposal.

## Next Steps (pending reviewer approval)

1. Exploratory analysis and cost-driver investigation
2. Feature engineering with temporal safeguards
3. Model training with chronological validation
4. Customer-level prediction explanations
5. High-bill flagging and uncertainty calibration
6. Final test evaluation and documentation

## Preprocessing notebook

Open [`notebooks/01_data_preprocessing.ipynb`](notebooks/01_data_preprocessing.ipynb).
It covers schema/integrity checks, training-only exploration, customer history
features, chronological splitting, leakage checks, and training-fitted encoding,
imputation and scaling. No predictive model is trained or test score computed.

```bash
python -m pip install -r requirements.txt
python -m jupyterlab notebooks/01_data_preprocessing.ipynb
```

Run all cells in order. Expected partitions: 14,000 train, 1,000 validation,
1,000 test, and 1,000 optional forward rows. Processed exports are opt-in and
ignored by Git; the raw CSV remains unchanged. The notebook retains executed
outputs so its validation results can be reviewed directly on GitHub.

Review notes: audit baseline scores cover all verified rows, including eventual
holdouts, and are descriptive rather than independent development scores.
February-origin labels become available at the March close; use the proposed
training partition for a March-close forecast, not a February-close forecast.
Model training, high-bill flags and uncertainty calibration remain future work.
