# Data Cleaning & Transformation Patterns

This reference provides patterns for cleaning, transforming, and preparing data for analysis using pandas.

## Table of Contents

1. [Handling Missing Data](#handling-missing-data)
2. [Removing Duplicates](#removing-duplicates)
3. [Data Type Conversion](#data-type-conversion)
4. [Outlier Detection](#outlier-detection)
5. [String Cleaning](#string-cleaning)
6. [Date/Time Processing](#datetime-processing)
7. [Data Normalization](#data-normalization)
8. [Feature Engineering](#feature-engineering)

## Handling Missing Data

### Identifying Missing Data

```python
import pandas as pd
import numpy as np

def analyze_missing_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Comprehensive missing data analysis.

    Returns:
        DataFrame with missing data statistics
    """
    missing_stats = pd.DataFrame({
        'column': df.columns,
        'missing_count': df.isnull().sum().values,
        'missing_pct': (df.isnull().sum() / len(df) * 100).values,
        'dtype': df.dtypes.values
    })

    # Sort by missing percentage
    missing_stats = missing_stats.sort_values(
        'missing_pct',
        ascending=False
    ).reset_index(drop=True)

    # Add severity flag
    missing_stats['severity'] = missing_stats['missing_pct'].apply(
        lambda x: 'Critical' if x > 50
        else 'High' if x > 20
        else 'Medium' if x > 5
        else 'Low'
    )

    return missing_stats[missing_stats['missing_count'] > 0]

# Usage
missing_report = analyze_missing_data(df)
print(missing_report)
```

### Handling Strategies

```python
def handle_missing_data(df: pd.DataFrame, strategy: str = 'smart',
                        threshold: float = 0.5) -> pd.DataFrame:
    """
    Handle missing data with various strategies.

    Args:
        df: Input dataframe
        strategy: 'smart', 'drop', 'fill_mean', 'fill_median',
                 'fill_mode', 'fill_forward', 'fill_backward'
        threshold: Drop columns with missing % above this

    Returns:
        Cleaned dataframe
    """
    df = df.copy()

    if strategy == 'smart':
        # Drop columns with excessive missing data
        cols_to_drop = df.columns[df.isnull().mean() > threshold]
        df = df.drop(columns=cols_to_drop)
        print(f"Dropped {len(cols_to_drop)} columns with >{threshold*100}% missing")

        # Fill numeric columns with median
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if df[col].isnull().any():
                df[col].fillna(df[col].median(), inplace=True)

        # Fill categorical columns with mode
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        for col in categorical_cols:
            if df[col].isnull().any():
                mode_value = df[col].mode()[0] if not df[col].mode().empty else 'Unknown'
                df[col].fillna(mode_value, inplace=True)

    elif strategy == 'drop':
        initial_rows = len(df)
        df = df.dropna()
        print(f"Dropped {initial_rows - len(df)} rows with missing values")

    elif strategy == 'fill_mean':
        numeric_cols = df.select_dtypes(include=['number']).columns
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())

    elif strategy == 'fill_median':
        numeric_cols = df.select_dtypes(include=['number']).columns
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())

    elif strategy == 'fill_mode':
        for col in df.columns:
            if df[col].isnull().any():
                mode_value = df[col].mode()[0] if not df[col].mode().empty else None
                df[col].fillna(mode_value, inplace=True)

    elif strategy == 'fill_forward':
        df = df.fillna(method='ffill')

    elif strategy == 'fill_backward':
        df = df.fillna(method='bfill')

    return df

# Usage
cleaned_df = handle_missing_data(df, strategy='smart', threshold=0.5)
```

### Interpolation for Time Series

```python
def interpolate_time_series(df: pd.DataFrame, column: str,
                            method: str = 'linear') -> pd.DataFrame:
    """
    Interpolate missing values in time series.

    Args:
        df: Input dataframe
        column: Column to interpolate
        method: 'linear', 'polynomial', 'spline', 'time'

    Returns:
        Dataframe with interpolated values
    """
    df = df.copy()

    if method == 'polynomial':
        df[column] = df[column].interpolate(method='polynomial', order=2)
    elif method == 'spline':
        df[column] = df[column].interpolate(method='spline', order=3)
    else:
        df[column] = df[column].interpolate(method=method)

    return df

# Usage
df_interpolated = interpolate_time_series(df, 'temperature', method='linear')
```

## Removing Duplicates

### Identify Duplicates

```python
def analyze_duplicates(df: pd.DataFrame, subset: list = None) -> dict:
    """
    Analyze duplicate rows in dataframe.

    Args:
        df: Input dataframe
        subset: Columns to consider for duplicates (None = all columns)

    Returns:
        Dictionary with duplicate statistics
    """
    duplicates = df.duplicated(subset=subset, keep=False)
    duplicate_count = duplicates.sum()

    if duplicate_count > 0:
        duplicate_rows = df[duplicates]

        return {
            'total_duplicates': int(duplicate_count),
            'percentage': f"{(duplicate_count / len(df) * 100):.2f}%",
            'unique_duplicate_groups': len(duplicate_rows.drop_duplicates(subset=subset)),
            'duplicate_rows': duplicate_rows
        }
    else:
        return {
            'total_duplicates': 0,
            'percentage': '0%',
            'message': 'No duplicates found'
        }

# Usage
dup_analysis = analyze_duplicates(df, subset=['name', 'email'])
print(f"Found {dup_analysis['total_duplicates']} duplicates")
```

### Remove Duplicates

```python
def remove_duplicates(df: pd.DataFrame, subset: list = None,
                     keep: str = 'first') -> pd.DataFrame:
    """
    Remove duplicate rows.

    Args:
        df: Input dataframe
        subset: Columns to consider (None = all)
        keep: 'first', 'last', or False (remove all duplicates)

    Returns:
        Deduplicated dataframe
    """
    initial_rows = len(df)
    df = df.drop_duplicates(subset=subset, keep=keep)
    removed = initial_rows - len(df)

    print(f"Removed {removed} duplicate rows ({removed/initial_rows*100:.1f}%)")
    return df

# Usage
clean_df = remove_duplicates(df, subset=['user_id', 'date'], keep='first')
```

## Data Type Conversion

### Smart Type Conversion

```python
def convert_data_types(df: pd.DataFrame, optimize: bool = True) -> pd.DataFrame:
    """
    Intelligently convert data types for efficiency.

    Args:
        df: Input dataframe
        optimize: Downcast numeric types to save memory

    Returns:
        Dataframe with optimized types
    """
    df = df.copy()

    for col in df.columns:
        # Try numeric conversion
        if df[col].dtype == 'object':
            try:
                # Try integer first
                if df[col].str.match(r'^-?\d+$').all():
                    df[col] = pd.to_numeric(df[col], downcast='integer' if optimize else None)
                # Try float
                else:
                    numeric = pd.to_numeric(df[col], errors='coerce')
                    if numeric.notna().sum() / len(df) > 0.9:  # >90% convertible
                        df[col] = numeric
            except (AttributeError, TypeError):
                pass

        # Optimize existing numeric types
        if optimize and df[col].dtype in ['int64', 'float64']:
            if df[col].dtype == 'int64':
                df[col] = pd.to_numeric(df[col], downcast='integer')
            else:
                df[col] = pd.to_numeric(df[col], downcast='float')

        # Convert low-cardinality strings to category
        if df[col].dtype == 'object':
            num_unique = df[col].nunique()
            if num_unique / len(df) < 0.5:  # <50% unique values
                df[col] = df[col].astype('category')

    return df

# Usage
optimized_df = convert_data_types(df, optimize=True)

# Check memory savings
print(f"Before: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
print(f"After: {optimized_df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
```

### Date/Time Conversion

```python
def parse_dates(df: pd.DataFrame, date_columns: list,
                format: str = None, errors: str = 'coerce') -> pd.DataFrame:
    """
    Parse date columns with flexible formatting.

    Args:
        df: Input dataframe
        date_columns: List of columns to parse
        format: Date format string (None = infer)
        errors: 'coerce', 'raise', or 'ignore'

    Returns:
        Dataframe with parsed dates
    """
    df = df.copy()

    for col in date_columns:
        df[col] = pd.to_datetime(df[col], format=format, errors=errors)

        # Report parsing issues
        if errors == 'coerce':
            failed = df[col].isna().sum()
            if failed > 0:
                print(f"⚠️  {col}: {failed} dates failed to parse")

    return df

# Usage
df = parse_dates(df, ['created_at', 'updated_at'], errors='coerce')
```

## Outlier Detection

### IQR Method

```python
def detect_outliers_iqr(df: pd.DataFrame, column: str,
                        multiplier: float = 1.5) -> pd.Series:
    """
    Detect outliers using IQR method.

    Args:
        df: Input dataframe
        column: Column to check
        multiplier: IQR multiplier (1.5 = standard, 3.0 = extreme)

    Returns:
        Boolean series indicating outliers
    """
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - multiplier * IQR
    upper_bound = Q3 + multiplier * IQR

    outliers = (df[column] < lower_bound) | (df[column] > upper_bound)

    print(f"Outlier Detection for {column}:")
    print(f"  Lower bound: {lower_bound:.2f}")
    print(f"  Upper bound: {upper_bound:.2f}")
    print(f"  Outliers found: {outliers.sum()} ({outliers.sum()/len(df)*100:.1f}%)")

    return outliers

# Usage
outliers = detect_outliers_iqr(df, 'price', multiplier=1.5)
df_no_outliers = df[~outliers]
```

### Z-Score Method

```python
def detect_outliers_zscore(df: pd.DataFrame, column: str,
                           threshold: float = 3.0) -> pd.Series:
    """
    Detect outliers using z-score method.

    Args:
        df: Input dataframe
        column: Column to check
        threshold: Z-score threshold (typically 2.5 or 3.0)

    Returns:
        Boolean series indicating outliers
    """
    from scipy import stats

    z_scores = np.abs(stats.zscore(df[column].dropna()))
    outliers = pd.Series(False, index=df.index)
    outliers.loc[df[column].dropna().index] = z_scores > threshold

    print(f"Z-Score Outlier Detection for {column}:")
    print(f"  Threshold: {threshold}")
    print(f"  Outliers found: {outliers.sum()} ({outliers.sum()/len(df)*100:.1f}%)")

    return outliers

# Usage
outliers = detect_outliers_zscore(df, 'revenue', threshold=3.0)
```

## String Cleaning

### Clean Text Columns

```python
def clean_text_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Clean text column (lowercase, trim, remove special chars).

    Args:
        df: Input dataframe
        column: Column to clean

    Returns:
        Dataframe with cleaned text
    """
    df = df.copy()

    # Convert to string
    df[column] = df[column].astype(str)

    # Lowercase
    df[column] = df[column].str.lower()

    # Strip whitespace
    df[column] = df[column].str.strip()

    # Remove extra whitespace
    df[column] = df[column].str.replace(r'\s+', ' ', regex=True)

    # Remove special characters (optional)
    # df[column] = df[column].str.replace(r'[^a-zA-Z0-9\s]', '', regex=True)

    return df

# Usage
df = clean_text_column(df, 'product_name')
```

### Standardize Categories

```python
def standardize_categories(df: pd.DataFrame, column: str,
                          mapping: dict = None) -> pd.DataFrame:
    """
    Standardize categorical values.

    Args:
        df: Input dataframe
        column: Column to standardize
        mapping: Optional mapping dict {old: new}

    Returns:
        Dataframe with standardized categories
    """
    df = df.copy()

    # Clean first
    df[column] = df[column].str.strip().str.lower()

    # Apply mapping if provided
    if mapping:
        df[column] = df[column].replace(mapping)

    # Report unique values
    print(f"Unique values in {column}: {df[column].nunique()}")
    print(df[column].value_counts())

    return df

# Usage
category_mapping = {
    'usa': 'United States',
    'us': 'United States',
    'u.s.': 'United States',
    'uk': 'United Kingdom',
    'u.k.': 'United Kingdom'
}
df = standardize_categories(df, 'country', mapping=category_mapping)
```

## Date/Time Processing

### Extract Date Components

```python
def extract_date_features(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    """
    Extract features from datetime column.

    Args:
        df: Input dataframe
        date_column: Name of datetime column

    Returns:
        Dataframe with additional date features
    """
    df = df.copy()

    # Ensure datetime type
    df[date_column] = pd.to_datetime(df[date_column])

    # Extract components
    df[f'{date_column}_year'] = df[date_column].dt.year
    df[f'{date_column}_month'] = df[date_column].dt.month
    df[f'{date_column}_day'] = df[date_column].dt.day
    df[f'{date_column}_dayofweek'] = df[date_column].dt.dayofweek
    df[f'{date_column}_quarter'] = df[date_column].dt.quarter
    df[f'{date_column}_is_weekend'] = df[date_column].dt.dayofweek >= 5

    # Month name
    df[f'{date_column}_month_name'] = df[date_column].dt.month_name()

    return df

# Usage
df = extract_date_features(df, 'transaction_date')
```

## Data Normalization

### Min-Max Scaling

```python
def normalize_minmax(df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
    """
    Normalize numeric columns to [0, 1] range.

    Args:
        df: Input dataframe
        columns: Columns to normalize (None = all numeric)

    Returns:
        Dataframe with normalized columns
    """
    df = df.copy()

    if columns is None:
        columns = df.select_dtypes(include=['number']).columns

    for col in columns:
        min_val = df[col].min()
        max_val = df[col].max()

        if max_val > min_val:
            df[f'{col}_normalized'] = (df[col] - min_val) / (max_val - min_val)
        else:
            df[f'{col}_normalized'] = 0

    return df

# Usage
df = normalize_minmax(df, columns=['price', 'quantity'])
```

### Standardization (Z-Score)

```python
def standardize_zscore(df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
    """
    Standardize numeric columns to mean=0, std=1.

    Args:
        df: Input dataframe
        columns: Columns to standardize (None = all numeric)

    Returns:
        Dataframe with standardized columns
    """
    df = df.copy()

    if columns is None:
        columns = df.select_dtypes(include=['number']).columns

    for col in columns:
        mean = df[col].mean()
        std = df[col].std()

        if std > 0:
            df[f'{col}_standardized'] = (df[col] - mean) / std
        else:
            df[f'{col}_standardized'] = 0

    return df

# Usage
df = standardize_zscore(df, columns=['sales', 'revenue'])
```

## Feature Engineering

### Binning Continuous Variables

```python
def create_bins(df: pd.DataFrame, column: str, bins: int = 5,
                labels: list = None) -> pd.DataFrame:
    """
    Create categorical bins from continuous variable.

    Args:
        df: Input dataframe
        column: Column to bin
        bins: Number of bins or bin edges
        labels: Optional bin labels

    Returns:
        Dataframe with binned column
    """
    df = df.copy()

    df[f'{column}_binned'] = pd.cut(
        df[column],
        bins=bins,
        labels=labels,
        include_lowest=True
    )

    # Report distribution
    print(f"Binned {column}:")
    print(df[f'{column}_binned'].value_counts().sort_index())

    return df

# Usage
df = create_bins(df, 'age', bins=[0, 18, 35, 50, 65, 100],
                labels=['Youth', 'Young Adult', 'Adult', 'Senior', 'Elderly'])
```

## Data Cleaning Checklist

- [ ] Check for and handle missing values
- [ ] Identify and remove/handle duplicates
- [ ] Convert data types appropriately
- [ ] Detect and handle outliers
- [ ] Clean and standardize text fields
- [ ] Parse and validate dates
- [ ] Normalize/standardize numeric columns
- [ ] Create derived features if needed
- [ ] Validate data ranges and constraints
- [ ] Document all cleaning decisions

## Quick Reference

| Task | pandas Method | Example |
|------|---------------|---------|
| Drop missing | `dropna()` | `df.dropna()` |
| Fill missing | `fillna()` | `df.fillna(0)` |
| Detect missing | `isnull()` | `df.isnull().sum()` |
| Drop duplicates | `drop_duplicates()` | `df.drop_duplicates()` |
| Convert type | `astype()` | `df['col'].astype('int')` |
| Parse dates | `to_datetime()` | `pd.to_datetime(df['date'])` |
| Clean strings | `str` accessor | `df['col'].str.strip()` |
| Replace values | `replace()` | `df.replace({'old': 'new'})` |
| Rename columns | `rename()` | `df.rename(columns={'old': 'new'})` |
