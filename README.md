# Customer Engagement & Retention Analytics Dashboard
The European Central Bank

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
The app expects `European_Bank.csv` in the same folder (included).

## What's inside
- **Engagement vs Churn Overview** — activity status, geography, engagement-profile churn breakdown
- **Product Utilization Impact** — churn by product count, product tiers, geography
- **High-Value Disengaged Customer Detector** — adjustable balance/salary percentile thresholds, downloadable at-risk customer list
- **Retention Strength Scoring** — composite 0–100 relationship-strength index, tenure stability, credit-card stickiness

## Filters (sidebar)
Geography, engagement profile, activity status, product-count slider, balance/salary/age range sliders — all update every module live.
