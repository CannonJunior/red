#!/usr/bin/env python3
"""
Automated data summary generation script.

Usage:
    python generate_summary.py <data_file> [--output summary.txt]
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def load_data(file_path: Path) -> Optional[pd.DataFrame]:
    """
    Load data from CSV, JSON, or Excel file.

    Args:
        file_path: Path to data file

    Returns:
        DataFrame or None if load fails
    """
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


def generate_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate comprehensive data summary.

    Args:
        df: Input dataframe

    Returns:
        Dictionary with summary statistics
    """
    summary = {
        'shape': {
            'rows': len(df),
            'columns': len(df.columns)
        },
        'columns': df.columns.tolist(),
        'dtypes': df.dtypes.astype(str).to_dict(),
        'missing_values': {},
        'duplicates': df.duplicated().sum(),
        'memory_usage_mb': df.memory_usage(deep=True).sum() / (1024 * 1024),
        'numeric_summary': {},
        'categorical_summary': {}
    }

    # Missing values analysis
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    summary['missing_values'] = {
        col: {
            'count': int(missing[col]),
            'percentage': float(missing_pct[col])
        }
        for col in df.columns if missing[col] > 0
    }

    # Numeric column statistics
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        desc = df[numeric_cols].describe()
        summary['numeric_summary'] = {
            col: {
                'mean': float(desc[col]['mean']),
                'median': float(df[col].median()),
                'std': float(desc[col]['std']),
                'min': float(desc[col]['min']),
                'max': float(desc[col]['max']),
                'q25': float(desc[col]['25%']),
                'q75': float(desc[col]['75%'])
            }
            for col in numeric_cols
        }

    # Categorical column statistics
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    if len(categorical_cols) > 0:
        summary['categorical_summary'] = {
            col: {
                'unique_values': int(df[col].nunique()),
                'most_common': str(df[col].mode()[0]) if not df[col].mode().empty else None,
                'most_common_count': int(df[col].value_counts().iloc[0]) if len(df[col]) > 0 else 0
            }
            for col in categorical_cols
        }

    return summary


def format_summary(summary: Dict[str, Any], file_path: Path) -> str:
    """
    Format summary as readable text.

    Args:
        summary: Summary dictionary
        file_path: Original file path

    Returns:
        Formatted summary string
    """
    output = []
    output.append("=" * 80)
    output.append(f"DATA SUMMARY: {file_path.name}")
    output.append("=" * 80)

    # Basic info
    output.append(f"\n📊 BASIC INFORMATION")
    output.append(f"  Rows: {summary['shape']['rows']:,}")
    output.append(f"  Columns: {summary['shape']['columns']}")
    output.append(f"  Memory Usage: {summary['memory_usage_mb']:.2f} MB")
    output.append(f"  Duplicate Rows: {summary['duplicates']:,}")

    # Column types
    output.append(f"\n📋 COLUMN DATA TYPES")
    for col, dtype in summary['dtypes'].items():
        output.append(f"  {col}: {dtype}")

    # Missing values
    if summary['missing_values']:
        output.append(f"\n⚠️  MISSING VALUES")
        for col, info in summary['missing_values'].items():
            output.append(f"  {col}: {info['count']:,} ({info['percentage']:.1f}%)")
    else:
        output.append(f"\n✅ NO MISSING VALUES")

    # Numeric summary
    if summary['numeric_summary']:
        output.append(f"\n🔢 NUMERIC COLUMNS SUMMARY")
        for col, stats in summary['numeric_summary'].items():
            output.append(f"\n  {col}:")
            output.append(f"    Mean: {stats['mean']:.2f}")
            output.append(f"    Median: {stats['median']:.2f}")
            output.append(f"    Std Dev: {stats['std']:.2f}")
            output.append(f"    Min: {stats['min']:.2f}")
            output.append(f"    Max: {stats['max']:.2f}")
            output.append(f"    25th %ile: {stats['q25']:.2f}")
            output.append(f"    75th %ile: {stats['q75']:.2f}")

    # Categorical summary
    if summary['categorical_summary']:
        output.append(f"\n📝 CATEGORICAL COLUMNS SUMMARY")
        for col, stats in summary['categorical_summary'].items():
            output.append(f"\n  {col}:")
            output.append(f"    Unique Values: {stats['unique_values']}")
            output.append(f"    Most Common: {stats['most_common']}")
            output.append(f"    Most Common Count: {stats['most_common_count']}")

    output.append("\n" + "=" * 80)

    return "\n".join(output)


def main():
    """Run data summary generation."""
    parser = argparse.ArgumentParser(
        description='Generate comprehensive data summary'
    )
    parser.add_argument('file', type=str, help='Path to data file')
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output file path (default: print to console)'
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
    print(f"🔍 Generating summary...")

    summary = generate_summary(df)
    formatted = format_summary(summary, file_path)

    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted)
        print(f"✅ Summary saved to: {output_path}")
    else:
        print(formatted)


if __name__ == "__main__":
    main()
