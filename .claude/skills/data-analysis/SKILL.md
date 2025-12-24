---
name: data-analysis
description: "Comprehensive data analysis toolkit for Python using pandas, numpy, and visualization libraries. When Claude needs to: (1) Load and explore datasets from CSV, JSON, Excel, or databases, (2) Perform statistical analysis and identify trends, (3) Clean and transform messy data, (4) Generate formatted reports with visualizations, or (5) Detect outliers, missing data, and data quality issues. Use for data exploration and insight generation, not for machine learning model building."
---

# Data Analysis & Reporting

## Overview

This skill provides comprehensive data analysis capabilities including data loading, statistical analysis, visualization, data cleaning, and automated report generation. It includes executable scripts and detailed analysis patterns.

## Quick Start

### Complete Data Analysis Example

```python
#!/usr/bin/env python3
"""
Example of comprehensive data analysis following best practices.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

def load_and_analyze(data_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load and analyze dataset with error handling.

    Args:
        data_path: Path to data file (CSV, JSON, or Excel)

    Returns:
        Dictionary with analysis results or None if analysis fails

    Raises:
        FileNotFoundError: If data file doesn't exist
        ValueError: If data format is invalid
    """
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    try:
        # Load data based on file extension
        if data_path.suffix == '.csv':
            df = pd.read_csv(data_path)
        elif data_path.suffix == '.json':
            df = pd.read_json(data_path)
        elif data_path.suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(data_path)
        else:
            raise ValueError(f"Unsupported file format: {data_path.suffix}")

        # Basic validation
        if df.empty:
            raise ValueError("Dataset is empty")

        # Perform analysis
        analysis = {
            'shape': df.shape,
            'columns': df.columns.tolist(),
            'dtypes': df.dtypes.to_dict(),
            'missing_values': df.isnull().sum().to_dict(),
            'numeric_summary': df.describe().to_dict(),
            'memory_usage': df.memory_usage(deep=True).sum()
        }

        return analysis

    except pd.errors.EmptyDataError:
        print(f"Error: Empty data file: {data_path}", file=sys.stderr)
        return None
    except pd.errors.ParserError as e:
        print(f"Error: Could not parse file: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error analyzing data: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze.py <data_file>", file=sys.stderr)
        sys.exit(1)

    data_path = Path(sys.argv[1])
    result = load_and_analyze(data_path)

    if result:
        print(f"✅ Analysis complete:")
        print(f"  Rows: {result['shape'][0]}")
        print(f"  Columns: {result['shape'][1]}")
        print(f"  Memory: {result['memory_usage'] / 1024:.2f} KB")
```

## Automated Analysis Tools

### Using Analysis Scripts

Run the automated data analysis script (see [scripts/generate_summary.py](scripts/generate_summary.py)):

```bash
python scripts/generate_summary.py data.csv
```

This generates:
- **Statistical summary**: Mean, median, std dev for numeric columns
- **Missing data report**: Percentage of missing values per column
- **Data quality checks**: Duplicate rows, outliers, data type issues
- **Formatted markdown report**: Ready-to-share analysis report

## Data Analysis Checklist

### 1. Data Loading
- [ ] Handle multiple file formats (CSV, JSON, Excel, SQL)
- [ ] Validate data structure and content
- [ ] Check for encoding issues
- [ ] Handle large datasets efficiently

### 2. Data Cleaning
- [ ] Identify and handle missing values
- [ ] Remove or flag duplicate rows
- [ ] Detect and handle outliers
- [ ] Standardize data types and formats

### 3. Statistical Analysis
- [ ] Calculate descriptive statistics
- [ ] Identify distributions and patterns
- [ ] Perform correlation analysis
- [ ] Test statistical significance

### 4. Visualization
- [ ] Create appropriate chart types
- [ ] Use clear labels and titles
- [ ] Apply consistent styling
- [ ] Export in multiple formats

### 5. Reporting
- [ ] Structure findings clearly
- [ ] Include relevant visualizations
- [ ] Provide actionable insights
- [ ] Export in shareable format

## Quick Reference

| Task | pandas Method | Example |
|------|---------------|---------|
| Load CSV | `read_csv()` | `df = pd.read_csv("data.csv")` |
| Load JSON | `read_json()` | `df = pd.read_json("data.json")` |
| Load Excel | `read_excel()` | `df = pd.read_excel("data.xlsx")` |
| Summary stats | `describe()` | `df.describe()` |
| Missing values | `isnull().sum()` | `df.isnull().sum()` |
| Group by | `groupby()` | `df.groupby('category')['value'].sum()` |
| Filter rows | Boolean indexing | `df[df['value'] > 100]` |
| Sort | `sort_values()` | `df.sort_values('date', ascending=False)` |
| Export CSV | `to_csv()` | `df.to_csv("output.csv", index=False)` |
| Export Excel | `to_excel()` | `df.to_excel("output.xlsx", index=False)` |

## Common Issues & Fixes

### Issue: Loading Fails with Encoding Error

❌ **Bad:**
```python
def load_data(path):
    return pd.read_csv(path)
```

✅ **Good:**
```python
from pathlib import Path
from typing import Optional
import pandas as pd

def load_data(path: Path, encoding: str = 'utf-8') -> Optional[pd.DataFrame]:
    """Load CSV with encoding fallback."""
    encodings = [encoding, 'latin-1', 'iso-8859-1', 'cp1252']

    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc)
            print(f"✅ Loaded with encoding: {enc}")
            return df
        except UnicodeDecodeError:
            continue

    print(f"❌ Could not decode file with any encoding", file=sys.stderr)
    return None
```

### Issue: Missing Data Handling

❌ **Bad:**
```python
# Drops all rows with any missing value
df = df.dropna()
```

✅ **Good:**
```python
from typing import Dict
import pandas as pd

def handle_missing_data(df: pd.DataFrame, strategy: str = 'smart') -> pd.DataFrame:
    """
    Handle missing data with intelligent strategies.

    Args:
        df: Input dataframe
        strategy: 'smart', 'drop', 'fill_mean', 'fill_median', 'fill_forward'

    Returns:
        Cleaned dataframe
    """
    if strategy == 'smart':
        # Drop columns with >50% missing
        threshold = len(df) * 0.5
        df = df.dropna(thresh=threshold, axis=1)

        # Fill numeric columns with median
        numeric_cols = df.select_dtypes(include=['number']).columns
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())

        # Fill categorical with mode
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else 'Unknown')

    elif strategy == 'drop':
        df = df.dropna()
    elif strategy == 'fill_mean':
        df = df.fillna(df.mean())
    elif strategy == 'fill_median':
        df = df.fillna(df.median())
    elif strategy == 'fill_forward':
        df = df.fillna(method='ffill')

    return df
```

### Issue: Memory Issues with Large Datasets

❌ **Bad:**
```python
# Loads entire dataset into memory
df = pd.read_csv("large_file.csv")
result = df.groupby('category')['value'].sum()
```

✅ **Good:**
```python
from typing import Iterator
import pandas as pd

def process_large_file(path: str, chunksize: int = 10000) -> pd.DataFrame:
    """Process large CSV file in chunks (memory efficient)."""
    chunks = []

    for chunk in pd.read_csv(path, chunksize=chunksize):
        # Process each chunk
        processed = chunk.groupby('category')['value'].sum()
        chunks.append(processed)

    # Combine results
    result = pd.concat(chunks).groupby(level=0).sum()
    return result
```

### Issue: Poor Data Type Selection

❌ **Bad:**
```python
# All columns loaded as objects/strings
df = pd.read_csv("data.csv")
```

✅ **Good:**
```python
import pandas as pd
from typing import Dict

def load_with_types(path: str, type_hints: Dict[str, str]) -> pd.DataFrame:
    """Load CSV with explicit data types for efficiency."""

    # Specify data types upfront
    dtypes = {
        'id': 'int32',  # int32 instead of int64 saves memory
        'category': 'category',  # category type for low-cardinality strings
        'value': 'float32',
        'date': str  # Parse dates separately
    }

    df = pd.read_csv(
        path,
        dtype=dtypes,
        parse_dates=['date']  # Parse date columns
    )

    return df
```

## Advanced Topics

### Statistical Analysis
For detailed statistical methods and hypothesis testing, see [references/statistical-analysis.md](references/statistical-analysis.md)

### Data Visualization
For plotting patterns and chart creation, see [references/visualization.md](references/visualization.md)

### Data Cleaning
For data quality and transformation techniques, see [references/data-cleaning.md](references/data-cleaning.md)

## Troubleshooting

### Tool Installation Issues

**Problem**: `pandas` or `numpy` not found
**Solution**: Install data science dependencies:
```bash
uv add pandas numpy matplotlib seaborn scipy
```

**Problem**: Excel file support missing
**Solution**: Install Excel support:
```bash
uv add openpyxl xlrd
```

### Common Errors

**pandas.errors.ParserError**: CSV parsing failed
- Check delimiter (try `sep=','` or `sep=';'` or `sep='\t'`)
- Try `error_bad_lines=False` to skip bad rows
- Check for quote character issues with `quotechar='"'`

**MemoryError**: Dataset too large
- Use chunking: `pd.read_csv(file, chunksize=10000)`
- Load only needed columns: `pd.read_csv(file, usecols=['col1', 'col2'])`
- Use more efficient data types (int32 instead of int64, category instead of object)

**KeyError**: Column not found
- Check column names: `df.columns.tolist()`
- Strip whitespace: `df.columns = df.columns.str.strip()`
- Case sensitivity: columns are case-sensitive

### Performance Tips

- Use `dtype` parameter when loading to specify data types upfront
- Use `usecols` to load only needed columns
- Use `nrows` for testing with sample data first
- Use `category` dtype for low-cardinality string columns
- Use vectorized operations instead of `apply()` when possible
- Use `query()` method instead of boolean indexing for complex filters
