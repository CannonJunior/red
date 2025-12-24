# Data Visualization Patterns

This reference provides patterns for creating effective data visualizations using matplotlib, seaborn, and pandas plotting.

## Table of Contents

1. [Basic Plotting Setup](#basic-plotting-setup)
2. [Distribution Plots](#distribution-plots)
3. [Relationship Plots](#relationship-plots)
4. [Categorical Plots](#categorical-plots)
5. [Time Series Plots](#time-series-plots)
6. [Statistical Plots](#statistical-plots)
7. [Best Practices](#best-practices)

## Basic Plotting Setup

### Standard Configuration

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

# Color palette
colors = sns.color_palette("husl", 8)
```

### Save Figure Function

```python
def save_plot(fig, filename: str, dpi: int = 300, formats: list = None):
    """
    Save figure in multiple formats.

    Args:
        fig: Matplotlib figure
        filename: Base filename without extension
        dpi: Resolution
        formats: List of formats ['png', 'pdf', 'svg']
    """
    if formats is None:
        formats = ['png']

    for fmt in formats:
        fig.savefig(
            f"{filename}.{fmt}",
            dpi=dpi,
            bbox_inches='tight',
            facecolor='white'
        )
        print(f"✅ Saved: {filename}.{fmt}")

# Usage
fig, ax = plt.subplots()
# ... create plot ...
save_plot(fig, 'my_chart', formats=['png', 'pdf'])
```

## Distribution Plots

### Histogram with KDE

```python
def plot_distribution(df: pd.DataFrame, column: str, bins: int = 30):
    """Create histogram with kernel density estimate."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Histogram
    ax.hist(df[column].dropna(), bins=bins, alpha=0.7,
            color='skyblue', edgecolor='black', density=True,
            label='Histogram')

    # KDE
    df[column].dropna().plot(kind='kde', ax=ax, color='red',
                              linewidth=2, label='KDE')

    # Statistics
    mean = df[column].mean()
    median = df[column].median()

    ax.axvline(mean, color='green', linestyle='--',
               linewidth=2, label=f'Mean: {mean:.2f}')
    ax.axvline(median, color='orange', linestyle='--',
               linewidth=2, label=f'Median: {median:.2f}')

    ax.set_xlabel(column, fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.set_title(f'Distribution of {column}', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig

# Usage
fig = plot_distribution(df, 'revenue', bins=50)
plt.show()
```

### Box Plot with Outliers

```python
def plot_boxplot(df: pd.DataFrame, column: str, by: str = None):
    """Create box plot showing outliers."""
    fig, ax = plt.subplots(figsize=(10, 6))

    if by:
        df.boxplot(column=column, by=by, ax=ax)
        ax.set_title(f'{column} by {by}')
    else:
        df.boxplot(column=column, ax=ax)
        ax.set_title(f'Distribution of {column}')

    # Add mean marker
    if by:
        means = df.groupby(by)[column].mean()
        positions = range(1, len(means) + 1)
        ax.scatter(positions, means, color='red', marker='D',
                   s=100, zorder=3, label='Mean')
    else:
        mean = df[column].mean()
        ax.scatter([1], [mean], color='red', marker='D',
                   s=100, zorder=3, label='Mean')

    ax.set_ylabel(column, fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig

# Usage
fig = plot_boxplot(df, 'sales', by='category')
plt.show()
```

## Relationship Plots

### Scatter Plot with Regression Line

```python
def plot_scatter_regression(df: pd.DataFrame, x_col: str, y_col: str,
                            hue_col: str = None):
    """Create scatter plot with regression line."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Scatter plot
    if hue_col:
        for group in df[hue_col].unique():
            mask = df[hue_col] == group
            ax.scatter(df[mask][x_col], df[mask][y_col],
                      label=group, alpha=0.6, s=50)
    else:
        ax.scatter(df[x_col], df[y_col], alpha=0.6, s=50,
                  color='skyblue', edgecolors='black')

    # Regression line
    from scipy.stats import linregress
    slope, intercept, r_value, p_value, std_err = linregress(
        df[x_col].dropna(),
        df[y_col].dropna()
    )

    x_line = np.array([df[x_col].min(), df[x_col].max()])
    y_line = slope * x_line + intercept

    ax.plot(x_line, y_line, 'r--', linewidth=2,
            label=f'Regression (R²={r_value**2:.3f})')

    ax.set_xlabel(x_col, fontsize=12)
    ax.set_ylabel(y_col, fontsize=12)
    ax.set_title(f'{y_col} vs {x_col}', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig

# Usage
fig = plot_scatter_regression(df, 'advertising', 'sales', hue_col='region')
plt.show()
```

### Correlation Heatmap

```python
def plot_correlation_heatmap(df: pd.DataFrame, method: str = 'pearson',
                             annot: bool = True):
    """Create correlation heatmap."""
    # Select numeric columns only
    numeric_df = df.select_dtypes(include=['number'])

    # Calculate correlation
    corr = numeric_df.corr(method=method)

    # Create heatmap
    fig, ax = plt.subplots(figsize=(12, 10))

    sns.heatmap(
        corr,
        annot=annot,
        fmt='.2f',
        cmap='coolwarm',
        center=0,
        square=True,
        linewidths=1,
        cbar_kws={'label': 'Correlation'},
        ax=ax
    )

    ax.set_title(f'{method.capitalize()} Correlation Matrix',
                 fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()
    return fig

# Usage
fig = plot_correlation_heatmap(df, method='pearson')
plt.show()
```

## Categorical Plots

### Bar Plot with Error Bars

```python
def plot_bar_with_errors(df: pd.DataFrame, category_col: str,
                         value_col: str, error_type: str = 'std'):
    """Create bar plot with error bars."""
    # Calculate statistics
    stats = df.groupby(category_col)[value_col].agg(['mean', 'std', 'sem'])

    # Choose error type
    if error_type == 'std':
        errors = stats['std']
    elif error_type == 'sem':
        errors = stats['sem']
    else:
        errors = None

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))

    x_pos = np.arange(len(stats))
    ax.bar(x_pos, stats['mean'], yerr=errors, capsize=5,
           alpha=0.7, color='skyblue', edgecolor='black')

    ax.set_xticks(x_pos)
    ax.set_xticklabels(stats.index, rotation=45, ha='right')
    ax.set_xlabel(category_col, fontsize=12)
    ax.set_ylabel(f'Mean {value_col}', fontsize=12)
    ax.set_title(f'{value_col} by {category_col}',
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    return fig

# Usage
fig = plot_bar_with_errors(df, 'category', 'sales', error_type='sem')
plt.show()
```

### Stacked Bar Chart

```python
def plot_stacked_bar(df: pd.DataFrame, x_col: str, y_col: str,
                     stack_col: str):
    """Create stacked bar chart."""
    # Pivot data for stacking
    pivot_df = df.pivot_table(
        values=y_col,
        index=x_col,
        columns=stack_col,
        aggfunc='sum',
        fill_value=0
    )

    # Create plot
    fig, ax = plt.subplots(figsize=(12, 6))

    pivot_df.plot(kind='bar', stacked=True, ax=ax,
                  colormap='viridis', edgecolor='black')

    ax.set_xlabel(x_col, fontsize=12)
    ax.set_ylabel(y_col, fontsize=12)
    ax.set_title(f'Stacked {y_col} by {x_col} and {stack_col}',
                 fontsize=14, fontweight='bold')
    ax.legend(title=stack_col, bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    return fig

# Usage
fig = plot_stacked_bar(df, 'month', 'revenue', 'product')
plt.show()
```

## Time Series Plots

### Time Series Line Plot

```python
def plot_time_series(df: pd.DataFrame, date_col: str, value_col: str,
                     ma_windows: list = None):
    """Create time series plot with moving averages."""
    # Ensure datetime
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    fig, ax = plt.subplots(figsize=(14, 6))

    # Main time series
    ax.plot(df[date_col], df[value_col], color='steelblue',
            linewidth=1.5, label='Actual', marker='o', markersize=3)

    # Moving averages
    if ma_windows:
        for window in ma_windows:
            ma = df[value_col].rolling(window=window).mean()
            ax.plot(df[date_col], ma, linewidth=2,
                   label=f'{window}-period MA', alpha=0.7)

    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel(value_col, fontsize=12)
    ax.set_title(f'{value_col} Over Time', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Rotate x-axis labels
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    return fig

# Usage
fig = plot_time_series(df, 'date', 'sales', ma_windows=[7, 30])
plt.show()
```

### Seasonal Decomposition

```python
from statsmodels.tsa.seasonal import seasonal_decompose

def plot_seasonal_decomposition(df: pd.DataFrame, date_col: str,
                                value_col: str, period: int = 12):
    """Plot seasonal decomposition."""
    # Prepare data
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()

    # Decompose
    decomposition = seasonal_decompose(
        df[value_col],
        model='additive',
        period=period
    )

    # Create subplots
    fig, axes = plt.subplots(4, 1, figsize=(14, 10))

    # Original
    axes[0].plot(df.index, df[value_col], color='steelblue')
    axes[0].set_ylabel('Original', fontsize=10)
    axes[0].grid(True, alpha=0.3)

    # Trend
    axes[1].plot(decomposition.trend.index, decomposition.trend,
                color='orange')
    axes[1].set_ylabel('Trend', fontsize=10)
    axes[1].grid(True, alpha=0.3)

    # Seasonal
    axes[2].plot(decomposition.seasonal.index, decomposition.seasonal,
                color='green')
    axes[2].set_ylabel('Seasonal', fontsize=10)
    axes[2].grid(True, alpha=0.3)

    # Residual
    axes[3].plot(decomposition.resid.index, decomposition.resid,
                color='red')
    axes[3].set_ylabel('Residual', fontsize=10)
    axes[3].set_xlabel('Date', fontsize=10)
    axes[3].grid(True, alpha=0.3)

    fig.suptitle(f'Seasonal Decomposition of {value_col}',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig

# Usage (requires statsmodels)
fig = plot_seasonal_decomposition(df, 'date', 'sales', period=12)
plt.show()
```

## Statistical Plots

### QQ Plot for Normality

```python
from scipy import stats

def plot_qq(df: pd.DataFrame, column: str):
    """Create Q-Q plot to assess normality."""
    fig, ax = plt.subplots(figsize=(8, 8))

    data = df[column].dropna()

    # Generate Q-Q plot
    stats.probplot(data, dist="norm", plot=ax)

    ax.set_title(f'Q-Q Plot: {column}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig

# Usage
fig = plot_qq(df, 'revenue')
plt.show()
```

## Best Practices

### Complete Visualization Example

```python
def create_complete_plot(df: pd.DataFrame, x_col: str, y_col: str,
                         title: str = None):
    """
    Create publication-quality plot with all best practices.
    """
    # Create figure with specific size and DPI
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

    # Main plot
    ax.scatter(df[x_col], df[y_col], alpha=0.6, s=50,
              color='steelblue', edgecolors='black', linewidth=0.5)

    # Labels with units if applicable
    ax.set_xlabel(x_col, fontsize=12, fontweight='bold')
    ax.set_ylabel(y_col, fontsize=12, fontweight='bold')

    # Title
    if title is None:
        title = f'{y_col} vs {x_col}'
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)

    # Grid
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

    # Formatting
    ax.tick_params(labelsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Add sample size
    n = len(df)
    ax.text(0.02, 0.98, f'n = {n:,}',
           transform=ax.transAxes,
           verticalalignment='top',
           fontsize=10,
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    return fig

# Usage
fig = create_complete_plot(df, 'price', 'sales',
                          title='Product Sales by Price')
save_plot(fig, 'sales_analysis', formats=['png', 'pdf'])
```

## Visualization Checklist

- [ ] Choose appropriate chart type for data
- [ ] Use clear, descriptive titles and labels
- [ ] Include axis labels with units
- [ ] Use consistent color schemes
- [ ] Add legends when multiple series
- [ ] Show sample size (n=)
- [ ] Use appropriate scale (linear vs log)
- [ ] Remove chart junk (unnecessary elements)
- [ ] Ensure readability at target size
- [ ] Add data source and date
- [ ] Use colorblind-friendly palettes
- [ ] Export in appropriate format and resolution

## Quick Reference

| Plot Type | Use Case | Library | Function |
|-----------|----------|---------|----------|
| Histogram | Distribution | matplotlib | `ax.hist()` |
| Box plot | Distribution + outliers | pandas/seaborn | `df.boxplot()` / `sns.boxplot()` |
| Scatter | Relationship | matplotlib | `ax.scatter()` |
| Line plot | Time series | matplotlib | `ax.plot()` |
| Bar chart | Categorical comparison | matplotlib | `ax.bar()` |
| Heatmap | Correlation matrix | seaborn | `sns.heatmap()` |
| Violin plot | Distribution shape | seaborn | `sns.violinplot()` |
| Pair plot | Multi-variable | seaborn | `sns.pairplot()` |

## Color Palettes

```python
# Categorical data
palette_categorical = sns.color_palette("Set2", 8)

# Sequential data
palette_sequential = sns.color_palette("Blues", 8)

# Diverging data
palette_diverging = sns.color_palette("RdBu_r", 11)

# Colorblind-friendly
palette_colorblind = sns.color_palette("colorblind", 8)
```
