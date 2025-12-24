#!/usr/bin/env python3
"""
Automated markdown report generation from data analysis.

Usage:
    python create_report.py <data_file> [--output report.md]
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd
import numpy as np


def load_data(file_path: Path) -> Optional[pd.DataFrame]:
    """Load data from file."""
    try:
        if file_path.suffix == '.csv':
            return pd.read_csv(file_path)
        elif file_path.suffix == '.json':
            return pd.read_json(file_path)
        elif file_path.suffix in ['.xlsx', '.xls']:
            return pd.read_excel(file_path)
        else:
            print(f"❌ Unsupported file format: {file_path.suffix}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"❌ Error loading file: {e}", file=sys.stderr)
        return None


def detect_outliers(series: pd.Series) -> int:
    """Detect outliers using IQR method."""
    if not pd.api.types.is_numeric_dtype(series):
        return 0

    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    outliers = ((series < lower_bound) | (series > upper_bound)).sum()
    return int(outliers)


def generate_markdown_report(df: pd.DataFrame, file_path: Path) -> str:
    """
    Generate formatted markdown report.

    Args:
        df: Input dataframe
        file_path: Original file path

    Returns:
        Formatted markdown string
    """
    report = []

    # Title and metadata
    report.append(f"# Data Analysis Report")
    report.append(f"\n**File**: `{file_path.name}`  ")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    report.append(f"**Rows**: {len(df):,}  ")
    report.append(f"**Columns**: {len(df.columns)}  \n")

    # Executive Summary
    report.append("## Executive Summary\n")
    report.append(f"This report analyzes data from `{file_path.name}` containing "
                  f"{len(df):,} records across {len(df.columns)} columns.\n")

    missing_total = df.isnull().sum().sum()
    duplicates = df.duplicated().sum()

    if missing_total > 0 or duplicates > 0:
        report.append("**Key Findings**:\n")
        if missing_total > 0:
            report.append(f"- ⚠️ Found {missing_total:,} missing values across dataset\n")
        if duplicates > 0:
            report.append(f"- ⚠️ Found {duplicates:,} duplicate rows\n")
    else:
        report.append("✅ **Data Quality**: No missing values or duplicates detected.\n")

    # Column Overview
    report.append("\n## Column Overview\n")
    report.append("| Column | Type | Missing | Unique |\n")
    report.append("|--------|------|---------|--------|\n")

    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = df[col].isnull().sum()
        missing_pct = f"{(missing / len(df) * 100):.1f}%" if missing > 0 else "-"
        unique = df[col].nunique()

        report.append(f"| {col} | {dtype} | {missing_pct} | {unique:,} |\n")

    # Numeric Analysis
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        report.append("\n## Numeric Columns Analysis\n")

        for col in numeric_cols:
            report.append(f"\n### {col}\n")

            stats = df[col].describe()
            outliers = detect_outliers(df[col])

            report.append("| Statistic | Value |\n")
            report.append("|-----------|-------|\n")
            report.append(f"| Count | {int(stats['count']):,} |\n")
            report.append(f"| Mean | {stats['mean']:.2f} |\n")
            report.append(f"| Median | {df[col].median():.2f} |\n")
            report.append(f"| Std Dev | {stats['std']:.2f} |\n")
            report.append(f"| Min | {stats['min']:.2f} |\n")
            report.append(f"| Max | {stats['max']:.2f} |\n")
            report.append(f"| 25th Percentile | {stats['25%']:.2f} |\n")
            report.append(f"| 75th Percentile | {stats['75%']:.2f} |\n")

            if outliers > 0:
                report.append(f"| **Outliers** | **{outliers:,}** |\n")

    # Categorical Analysis
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    if len(categorical_cols) > 0:
        report.append("\n## Categorical Columns Analysis\n")

        for col in categorical_cols:
            report.append(f"\n### {col}\n")

            unique_count = df[col].nunique()
            most_common = df[col].value_counts().head(10)

            report.append(f"**Unique Values**: {unique_count:,}\n")
            report.append(f"\n**Top 10 Values**:\n\n")
            report.append("| Value | Count | Percentage |\n")
            report.append("|-------|-------|------------|\n")

            for value, count in most_common.items():
                pct = (count / len(df) * 100)
                report.append(f"| {value} | {count:,} | {pct:.1f}% |\n")

    # Data Quality Issues
    report.append("\n## Data Quality Assessment\n")

    issues_found = False

    # Missing values
    missing_cols = df.columns[df.isnull().any()].tolist()
    if missing_cols:
        issues_found = True
        report.append("\n### Missing Values\n")
        report.append("| Column | Missing Count | Percentage |\n")
        report.append("|--------|---------------|------------|\n")

        for col in missing_cols:
            missing = df[col].isnull().sum()
            pct = (missing / len(df) * 100)
            report.append(f"| {col} | {missing:,} | {pct:.1f}% |\n")

    # Duplicates
    if duplicates > 0:
        issues_found = True
        report.append(f"\n### Duplicate Rows\n")
        report.append(f"Found {duplicates:,} duplicate rows ({(duplicates/len(df)*100):.1f}% of dataset)\n")

    # Outliers
    outlier_cols = []
    for col in numeric_cols:
        outliers = detect_outliers(df[col])
        if outliers > 0:
            outlier_cols.append((col, outliers))

    if outlier_cols:
        issues_found = True
        report.append("\n### Outliers (IQR Method)\n")
        report.append("| Column | Outlier Count | Percentage |\n")
        report.append("|--------|---------------|------------|\n")

        for col, count in outlier_cols:
            pct = (count / len(df) * 100)
            report.append(f"| {col} | {count:,} | {pct:.1f}% |\n")

    if not issues_found:
        report.append("\n✅ **No major data quality issues detected.**\n")

    # Recommendations
    report.append("\n## Recommendations\n")

    if missing_total > 0:
        report.append("- Consider handling missing values through imputation or removal\n")
    if duplicates > 0:
        report.append("- Remove or investigate duplicate rows\n")
    if outlier_cols:
        report.append("- Review outliers to determine if they are errors or valid extreme values\n")
    if not issues_found:
        report.append("- Data quality is good; proceed with analysis\n")

    report.append("\n---\n")
    report.append(f"*Report generated using automated data analysis tools*\n")

    return "".join(report)


def main():
    """Run report generation."""
    parser = argparse.ArgumentParser(
        description='Generate markdown report from data analysis'
    )
    parser.add_argument('file', type=str, help='Path to data file')
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='report.md',
        help='Output markdown file (default: report.md)'
    )

    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    print(f"📂 Loading data from: {file_path}")
    df = load_data(file_path)

    if df is None:
        sys.exit(1)

    print(f"✅ Loaded {len(df):,} rows and {len(df.columns)} columns")
    print(f"📝 Generating markdown report...")

    report = generate_markdown_report(df, file_path)

    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ Report saved to: {output_path}")


if __name__ == "__main__":
    main()
