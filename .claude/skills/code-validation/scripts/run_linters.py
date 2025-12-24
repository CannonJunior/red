#!/usr/bin/env python3
"""
Automated code review script that runs multiple linting tools.

Usage:
    python run_linters.py <file_or_directory>
"""

import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any


def run_command(cmd: List[str], description: str) -> Dict[str, Any]:
    """
    Run a command and capture output.

    Args:
        cmd: Command to run as list of arguments
        description: Human-readable description of what's being run

    Returns:
        Dictionary with command results
    """
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        return {
            'tool': description,
            'command': ' '.join(cmd),
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'status': 'passed' if result.returncode == 0 else 'failed'
        }

    except FileNotFoundError:
        return {
            'tool': description,
            'command': ' '.join(cmd),
            'returncode': -1,
            'stdout': '',
            'stderr': f'{cmd[0]} not found. Install with: pip install {cmd[0]}',
            'status': 'not_installed'
        }
    except subprocess.TimeoutExpired:
        return {
            'tool': description,
            'command': ' '.join(cmd),
            'returncode': -1,
            'stdout': '',
            'stderr': 'Command timed out after 60 seconds',
            'status': 'timeout'
        }
    except Exception as e:
        return {
            'tool': description,
            'command': ' '.join(cmd),
            'returncode': -1,
            'stdout': '',
            'stderr': str(e),
            'status': 'error'
        }


def print_result(result: Dict[str, Any]):
    """Print formatted result."""
    status_symbols = {
        'passed': '✅',
        'failed': '❌',
        'not_installed': '⚠️',
        'timeout': '⏱️',
        'error': '💥'
    }

    symbol = status_symbols.get(result['status'], '❓')
    print(f"\n{symbol} {result['tool']}: {result['status'].upper()}")

    if result['stdout']:
        print("\nOutput:")
        print(result['stdout'])

    if result['stderr'] and result['status'] != 'passed':
        print("\nErrors/Warnings:")
        print(result['stderr'])


def main():
    """Run all linting tools."""
    if len(sys.argv) != 2:
        print("Usage: python run_linters.py <file_or_directory>", file=sys.stderr)
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"Error: {target} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"\n🔍 Running automated code review on: {target}")
    print(f"Target type: {'directory' if target.is_dir() else 'file'}")

    results = []

    # 1. flake8 - Style and PEP8 compliance
    results.append(run_command(
        ['flake8', '--max-line-length=100', '--show-source', '--statistics', str(target)],
        'flake8 (PEP8 Style Check)'
    ))
    print_result(results[-1])

    # 2. pylint - Code quality and potential bugs
    results.append(run_command(
        ['pylint', '--max-line-length=100', str(target)],
        'pylint (Code Quality)'
    ))
    print_result(results[-1])

    # 3. mypy - Type checking
    results.append(run_command(
        ['mypy', '--ignore-missing-imports', str(target)],
        'mypy (Type Checking)'
    ))
    print_result(results[-1])

    # 4. bandit - Security vulnerability scanning
    if target.is_dir():
        results.append(run_command(
            ['bandit', '-r', str(target)],
            'bandit (Security Scan)'
        ))
    else:
        results.append(run_command(
            ['bandit', str(target)],
            'bandit (Security Scan)'
        ))
    print_result(results[-1])

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r['status'] == 'passed')
    failed = sum(1 for r in results if r['status'] == 'failed')
    not_installed = sum(1 for r in results if r['status'] == 'not_installed')

    print(f"\n✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Not installed: {not_installed}")

    # Output JSON for programmatic access
    output_file = Path('.code_review_results.json')
    with open(output_file, 'w') as f:
        json.dump({
            'target': str(target),
            'results': results,
            'summary': {
                'passed': passed,
                'failed': failed,
                'not_installed': not_installed,
                'total': len(results)
            }
        }, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")

    # Exit with error if any checks failed
    if failed > 0:
        print("\n⚠️  Some checks failed. Review output above.")
        sys.exit(1)
    elif not_installed > 0:
        print("\n⚠️  Some tools not installed. Install with:")
        print("    pip install flake8 pylint mypy bandit")
        sys.exit(1)
    else:
        print("\n✅ All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
