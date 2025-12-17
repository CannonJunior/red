---
name: data-analysis
description: Analyze data from CSV/JSON files and generate formatted reports with findings. Use when analyzing datasets, creating reports, or summarizing data insights.
---

# Data Analysis & Reporting

## Quick start

Load and analyze CSV data:

```python
import pandas as pd

# Load data
df = pd.read_csv("data.csv")

# Basic analysis
print(f"Rows: {len(df)}")
print(f"Columns: {df.columns.tolist()}")
print(df.describe())
```

## Generate summary report

```python
import pandas as pd

df = pd.read_csv("data.csv")

report = f"""
# Data Analysis Report

## Overview
- Total records: {len(df)}
- Columns: {len(df.columns)}

## Column Summary
{df.describe().to_string()}

## Data Types
{df.dtypes.to_string()}
"""

with open("report.md", "w") as f:
    f.write(report)
```

## Finding trends

```python
import pandas as pd

df = pd.read_csv("data.csv")

# Sort by numeric column
top_values = df.nlargest(5, 'amount')

# Group and aggregate
grouped = df.groupby('category')['value'].sum()

# Calculate growth
df['pct_change'] = df['value'].pct_change()
```

## Export formats

- **CSV**: `df.to_csv("output.csv")`
- **JSON**: `df.to_json("output.json")`
- **Excel**: `df.to_excel("output.xlsx")`
- **Markdown**: Use f-strings to format as markdown tables
