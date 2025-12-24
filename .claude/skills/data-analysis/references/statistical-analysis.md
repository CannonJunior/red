# Statistical Analysis Patterns

This reference provides patterns for performing statistical analysis on datasets using pandas, numpy, and scipy.

## Table of Contents

1. [Descriptive Statistics](#descriptive-statistics)
2. [Correlation Analysis](#correlation-analysis)
3. [Hypothesis Testing](#hypothesis-testing)
4. [Distribution Analysis](#distribution-analysis)
5. [Time Series Analysis](#time-series-analysis)
6. [Grouping and Aggregation](#grouping-and-aggregation)

## Descriptive Statistics

### Basic Summary Statistics

```python
import pandas as pd
import numpy as np

def comprehensive_summary(df: pd.DataFrame, column: str) -> dict:
    """Calculate comprehensive statistics for a column."""
    data = df[column].dropna()

    return {
        'count': len(data),
        'mean': data.mean(),
        'median': data.median(),
        'mode': data.mode()[0] if not data.mode().empty else None,
        'std': data.std(),
        'var': data.var(),
        'min': data.min(),
        'max': data.max(),
        'range': data.max() - data.min(),
        'q25': data.quantile(0.25),
        'q75': data.quantile(0.75),
        'iqr': data.quantile(0.75) - data.quantile(0.25),
        'skewness': data.skew(),
        'kurtosis': data.kurtosis()
    }

# Usage
summary = comprehensive_summary(df, 'sales')
print(f"Mean: {summary['mean']:.2f}")
print(f"Median: {summary['median']:.2f}")
print(f"Std Dev: {summary['std']:.2f}")
```

### Percentile Analysis

```python
def percentile_analysis(df: pd.DataFrame, column: str, percentiles: list = None):
    """Calculate custom percentiles."""
    if percentiles is None:
        percentiles = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]

    results = df[column].quantile(percentiles)

    print(f"Percentile Analysis for {column}:")
    for p, value in results.items():
        print(f"  {p*100:.0f}th percentile: {value:.2f}")

    return results

# Usage
percentile_analysis(df, 'revenue')
```

## Correlation Analysis

### Pearson Correlation

```python
def correlation_analysis(df: pd.DataFrame, method: str = 'pearson'):
    """
    Calculate correlation matrix.

    Args:
        df: Dataframe with numeric columns
        method: 'pearson', 'spearman', or 'kendall'
    """
    # Select only numeric columns
    numeric_df = df.select_dtypes(include=['number'])

    # Calculate correlation
    corr_matrix = numeric_df.corr(method=method)

    return corr_matrix

# Usage
corr = correlation_analysis(df, method='pearson')
print(corr)

# Find highly correlated pairs
def find_high_correlations(corr_matrix: pd.DataFrame, threshold: float = 0.7):
    """Find pairs with correlation above threshold."""
    # Get upper triangle (avoid duplicates)
    upper = corr_matrix.where(
        np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
    )

    # Find columns with high correlation
    high_corr = []
    for column in upper.columns:
        for index in upper.index:
            if abs(upper.loc[index, column]) > threshold:
                high_corr.append({
                    'var1': index,
                    'var2': column,
                    'correlation': upper.loc[index, column]
                })

    return pd.DataFrame(high_corr).sort_values('correlation', ascending=False)

# Usage
high_corr = find_high_correlations(corr, threshold=0.7)
print(high_corr)
```

### Correlation Significance Testing

```python
from scipy import stats

def correlation_with_pvalue(df: pd.DataFrame, col1: str, col2: str):
    """Calculate correlation with statistical significance."""
    data1 = df[col1].dropna()
    data2 = df[col2].dropna()

    # Ensure same length
    common_idx = data1.index.intersection(data2.index)
    data1 = data1.loc[common_idx]
    data2 = data2.loc[common_idx]

    # Calculate Pearson correlation and p-value
    corr, pvalue = stats.pearsonr(data1, data2)

    print(f"Correlation between {col1} and {col2}:")
    print(f"  Coefficient: {corr:.4f}")
    print(f"  P-value: {pvalue:.4f}")
    print(f"  Significant: {'Yes' if pvalue < 0.05 else 'No'}")

    return corr, pvalue

# Usage
correlation_with_pvalue(df, 'price', 'sales')
```

## Hypothesis Testing

### T-Test (Compare Two Groups)

```python
from scipy import stats

def independent_ttest(df: pd.DataFrame, value_col: str, group_col: str,
                      group1: str, group2: str):
    """
    Perform independent t-test to compare two groups.

    H0: The means of the two groups are equal
    H1: The means are different
    """
    data1 = df[df[group_col] == group1][value_col].dropna()
    data2 = df[df[group_col] == group2][value_col].dropna()

    # Perform t-test
    t_stat, p_value = stats.ttest_ind(data1, data2)

    print(f"Independent T-Test: {group1} vs {group2}")
    print(f"  Group 1 mean: {data1.mean():.2f} (n={len(data1)})")
    print(f"  Group 2 mean: {data2.mean():.2f} (n={len(data2)})")
    print(f"  T-statistic: {t_stat:.4f}")
    print(f"  P-value: {p_value:.4f}")
    print(f"  Significant difference: {'Yes' if p_value < 0.05 else 'No'}")

    return t_stat, p_value

# Usage
independent_ttest(df, 'revenue', 'category', 'A', 'B')
```

### Chi-Square Test (Categorical Association)

```python
from scipy.stats import chi2_contingency

def chi_square_test(df: pd.DataFrame, col1: str, col2: str):
    """
    Test independence between two categorical variables.

    H0: Variables are independent
    H1: Variables are associated
    """
    # Create contingency table
    contingency = pd.crosstab(df[col1], df[col2])

    # Perform chi-square test
    chi2, p_value, dof, expected = chi2_contingency(contingency)

    print(f"Chi-Square Test: {col1} vs {col2}")
    print(f"  Chi-square: {chi2:.4f}")
    print(f"  P-value: {p_value:.4f}")
    print(f"  Degrees of freedom: {dof}")
    print(f"  Significant association: {'Yes' if p_value < 0.05 else 'No'}")

    print("\nContingency Table:")
    print(contingency)

    return chi2, p_value

# Usage
chi_square_test(df, 'category', 'outcome')
```

### ANOVA (Compare Multiple Groups)

```python
from scipy import stats

def one_way_anova(df: pd.DataFrame, value_col: str, group_col: str):
    """
    Perform one-way ANOVA to compare means across multiple groups.

    H0: All group means are equal
    H1: At least one group mean is different
    """
    groups = [group[value_col].dropna()
              for name, group in df.groupby(group_col)]

    # Perform ANOVA
    f_stat, p_value = stats.f_oneway(*groups)

    print(f"One-Way ANOVA: {value_col} by {group_col}")
    print(f"  F-statistic: {f_stat:.4f}")
    print(f"  P-value: {p_value:.4f}")
    print(f"  Significant difference: {'Yes' if p_value < 0.05 else 'No'}")

    # Group summaries
    print("\nGroup Summaries:")
    for name, group in df.groupby(group_col):
        data = group[value_col].dropna()
        print(f"  {name}: mean={data.mean():.2f}, n={len(data)}")

    return f_stat, p_value

# Usage
one_way_anova(df, 'sales', 'region')
```

## Distribution Analysis

### Test for Normality

```python
from scipy import stats

def test_normality(df: pd.DataFrame, column: str):
    """Test if data follows normal distribution."""
    data = df[column].dropna()

    # Shapiro-Wilk test
    shapiro_stat, shapiro_p = stats.shapiro(data)

    # Kolmogorov-Smirnov test
    ks_stat, ks_p = stats.kstest(data, 'norm',
                                  args=(data.mean(), data.std()))

    print(f"Normality Tests for {column}:")
    print(f"\nShapiro-Wilk Test:")
    print(f"  Statistic: {shapiro_stat:.4f}")
    print(f"  P-value: {shapiro_p:.4f}")
    print(f"  Normal: {'Yes' if shapiro_p > 0.05 else 'No'}")

    print(f"\nKolmogorov-Smirnov Test:")
    print(f"  Statistic: {ks_stat:.4f}")
    print(f"  P-value: {ks_p:.4f}")
    print(f"  Normal: {'Yes' if ks_p > 0.05 else 'No'}")

    return shapiro_p, ks_p

# Usage
test_normality(df, 'revenue')
```

## Time Series Analysis

### Basic Time Series Operations

```python
def analyze_time_series(df: pd.DataFrame, date_col: str, value_col: str):
    """Perform basic time series analysis."""
    # Ensure datetime index
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()

    # Calculate statistics
    results = {
        'total': df[value_col].sum(),
        'mean': df[value_col].mean(),
        'trend': df[value_col].iloc[-1] - df[value_col].iloc[0],
        'growth_rate': ((df[value_col].iloc[-1] / df[value_col].iloc[0]) - 1) * 100,
        'volatility': df[value_col].std(),
        'min_date': df[value_col].idxmin(),
        'max_date': df[value_col].idxmax()
    }

    print(f"Time Series Analysis: {value_col}")
    print(f"  Total: {results['total']:,.2f}")
    print(f"  Average: {results['mean']:,.2f}")
    print(f"  Trend: {results['trend']:,.2f}")
    print(f"  Growth Rate: {results['growth_rate']:.2f}%")
    print(f"  Volatility (Std): {results['volatility']:,.2f}")

    return results

# Usage
analyze_time_series(df, 'date', 'revenue')
```

### Moving Averages

```python
def calculate_moving_averages(df: pd.DataFrame, column: str, windows: list = None):
    """Calculate multiple moving averages."""
    if windows is None:
        windows = [7, 30, 90]

    result_df = df[[column]].copy()

    for window in windows:
        ma_col = f'MA_{window}'
        result_df[ma_col] = result_df[column].rolling(window=window).mean()

    return result_df

# Usage
ma_df = calculate_moving_averages(df, 'sales', windows=[7, 30])
```

## Grouping and Aggregation

### Multi-Level Aggregation

```python
def multi_level_aggregation(df: pd.DataFrame, group_cols: list, value_col: str):
    """Perform comprehensive aggregation."""
    agg_functions = {
        value_col: [
            'count',
            'sum',
            'mean',
            'median',
            'std',
            'min',
            'max'
        ]
    }

    result = df.groupby(group_cols).agg(agg_functions)
    result.columns = ['_'.join(col).strip() for col in result.columns.values]

    return result

# Usage
summary = multi_level_aggregation(df, ['category', 'region'], 'sales')
print(summary)
```

### Custom Aggregation Functions

```python
def custom_aggregations(df: pd.DataFrame, group_col: str, value_col: str):
    """Apply custom aggregation functions."""
    def coefficient_of_variation(x):
        """Calculate CV (std/mean)."""
        return x.std() / x.mean() if x.mean() != 0 else 0

    def percentile_90(x):
        """Calculate 90th percentile."""
        return x.quantile(0.9)

    result = df.groupby(group_col)[value_col].agg([
        ('count', 'count'),
        ('mean', 'mean'),
        ('std', 'std'),
        ('cv', coefficient_of_variation),
        ('p90', percentile_90),
        ('range', lambda x: x.max() - x.min())
    ])

    return result

# Usage
custom_stats = custom_aggregations(df, 'category', 'revenue')
print(custom_stats)
```

## Statistical Analysis Checklist

- [ ] Check data distribution (normality tests)
- [ ] Calculate descriptive statistics
- [ ] Identify correlations between variables
- [ ] Test statistical significance of findings
- [ ] Handle outliers appropriately
- [ ] Consider sample size for statistical power
- [ ] Use appropriate tests (parametric vs non-parametric)
- [ ] Report confidence intervals
- [ ] Account for multiple testing if applicable
- [ ] Validate assumptions of statistical tests

## Quick Reference

| Analysis | scipy.stats Function | Use Case |
|----------|---------------------|----------|
| T-test | `ttest_ind()` | Compare two group means |
| Paired T-test | `ttest_rel()` | Compare paired samples |
| ANOVA | `f_oneway()` | Compare 3+ group means |
| Chi-square | `chi2_contingency()` | Test categorical association |
| Correlation | `pearsonr()` | Linear relationship strength |
| Normality | `shapiro()` | Test normal distribution |
| Mann-Whitney | `mannwhitneyu()` | Non-parametric comparison |
| Kruskal-Wallis | `kruskal()` | Non-parametric ANOVA |
