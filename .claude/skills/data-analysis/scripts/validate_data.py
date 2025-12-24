#!/usr/bin/env python3
"""
Data validation script to check data quality.

Usage:
    python validate_data.py <data_file> [--strict]
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
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


def check_empty_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """Check if dataset is empty."""
    is_empty = len(df) == 0
    return {
        'check': 'Empty Dataset',
        'passed': not is_empty,
        'severity': 'critical',
        'message': 'Dataset is empty' if is_empty else 'Dataset has data',
        'details': {'rows': len(df)}
    }


def check_missing_values(df: pd.DataFrame, threshold: float = 0.5) -> Dict[str, Any]:
    """Check for excessive missing values."""
    missing_pct = (df.isnull().sum() / len(df))
    problematic_cols = missing_pct[missing_pct > threshold].to_dict()

    passed = len(problematic_cols) == 0
    total_missing = df.isnull().sum().sum()

    return {
        'check': 'Missing Values',
        'passed': passed,
        'severity': 'high' if not passed else 'info',
        'message': f'Found {total_missing:,} missing values total',
        'details': {
            'total_missing': int(total_missing),
            'columns_over_threshold': {
                col: f"{pct*100:.1f}%"
                for col, pct in problematic_cols.items()
            }
        }
    }


def check_duplicates(df: pd.DataFrame) -> Dict[str, Any]:
    """Check for duplicate rows."""
    duplicates = df.duplicated().sum()
    passed = duplicates == 0

    return {
        'check': 'Duplicate Rows',
        'passed': passed,
        'severity': 'medium' if not passed else 'info',
        'message': f'Found {duplicates:,} duplicate rows' if duplicates > 0 else 'No duplicates',
        'details': {
            'duplicate_count': int(duplicates),
            'percentage': f"{(duplicates / len(df) * 100):.2f}%"
        }
    }


def check_data_types(df: pd.DataFrame) -> Dict[str, Any]:
    """Check for inappropriate data types."""
    issues = []

    for col in df.columns:
        # Check if numeric column stored as object
        if df[col].dtype == 'object':
            # Try to convert to numeric
            try:
                pd.to_numeric(df[col], errors='raise')
                issues.append({
                    'column': col,
                    'issue': 'Numeric data stored as object/string',
                    'suggestion': 'Convert to numeric type'
                })
            except (ValueError, TypeError):
                pass

    passed = len(issues) == 0

    return {
        'check': 'Data Types',
        'passed': passed,
        'severity': 'low' if not passed else 'info',
        'message': f'Found {len(issues)} data type issues' if issues else 'Data types appropriate',
        'details': {'issues': issues}
    }


def check_outliers(df: pd.DataFrame, iqr_multiplier: float = 1.5) -> Dict[str, Any]:
    """Check for outliers in numeric columns."""
    numeric_cols = df.select_dtypes(include=['number']).columns
    outlier_info = {}

    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - iqr_multiplier * IQR
        upper_bound = Q3 + iqr_multiplier * IQR

        outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()

        if outliers > 0:
            outlier_info[col] = {
                'count': int(outliers),
                'percentage': f"{(outliers / len(df) * 100):.2f}%",
                'lower_bound': float(lower_bound),
                'upper_bound': float(upper_bound)
            }

    passed = len(outlier_info) == 0

    return {
        'check': 'Outliers (IQR Method)',
        'passed': passed,
        'severity': 'info',
        'message': f'Found outliers in {len(outlier_info)} columns' if outlier_info else 'No outliers detected',
        'details': outlier_info
    }


def check_unique_id(df: pd.DataFrame) -> Dict[str, Any]:
    """Check for columns that could be unique identifiers."""
    id_candidates = []

    for col in df.columns:
        if df[col].nunique() == len(df):
            id_candidates.append(col)

    return {
        'check': 'Unique Identifier',
        'passed': len(id_candidates) > 0,
        'severity': 'info',
        'message': f'Found {len(id_candidates)} potential ID columns',
        'details': {'id_candidates': id_candidates}
    }


def check_cardinality(df: pd.DataFrame) -> Dict[str, Any]:
    """Check for high-cardinality categorical columns."""
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    high_cardinality = {}

    for col in categorical_cols:
        unique_count = df[col].nunique()
        unique_ratio = unique_count / len(df)

        # Flag if >50% unique values (might be better as ID or numeric)
        if unique_ratio > 0.5:
            high_cardinality[col] = {
                'unique_count': int(unique_count),
                'unique_ratio': f"{unique_ratio*100:.1f}%"
            }

    passed = len(high_cardinality) == 0

    return {
        'check': 'Cardinality',
        'passed': passed,
        'severity': 'low' if not passed else 'info',
        'message': f'Found {len(high_cardinality)} high-cardinality categorical columns',
        'details': high_cardinality
    }


def run_validation(df: pd.DataFrame, strict: bool = False) -> List[Dict[str, Any]]:
    """
    Run all validation checks.

    Args:
        df: Input dataframe
        strict: If True, use stricter validation thresholds

    Returns:
        List of validation results
    """
    results = []

    results.append(check_empty_dataset(df))
    results.append(check_missing_values(df, threshold=0.3 if strict else 0.5))
    results.append(check_duplicates(df))
    results.append(check_data_types(df))
    results.append(check_outliers(df))
    results.append(check_unique_id(df))
    results.append(check_cardinality(df))

    return results


def print_results(results: List[Dict[str, Any]]):
    """Print validation results in formatted output."""
    print("\n" + "=" * 80)
    print("DATA VALIDATION RESULTS")
    print("=" * 80 + "\n")

    severity_symbols = {
        'critical': '🔴',
        'high': '🟠',
        'medium': '🟡',
        'low': '🔵',
        'info': 'ℹ️'
    }

    passed_count = sum(1 for r in results if r['passed'])
    failed_count = len(results) - passed_count

    for result in results:
        symbol = '✅' if result['passed'] else '❌'
        severity_symbol = severity_symbols.get(result['severity'], 'ℹ️')

        print(f"{symbol} {severity_symbol} {result['check']}")
        print(f"   {result['message']}")

        if result['details'] and not result['passed']:
            print(f"   Details: {result['details']}")

        print()

    print("=" * 80)
    print(f"SUMMARY: {passed_count} passed, {failed_count} failed")
    print("=" * 80 + "\n")

    return failed_count == 0


def main():
    """Run data validation."""
    parser = argparse.ArgumentParser(
        description='Validate data quality'
    )
    parser.add_argument('file', type=str, help='Path to data file')
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Use strict validation thresholds'
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
    print(f"🔍 Running validation checks...")

    results = run_validation(df, strict=args.strict)
    all_passed = print_results(results)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
