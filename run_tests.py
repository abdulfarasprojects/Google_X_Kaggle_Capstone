#!/usr/bin/env python3
"""
Test runner script for Weight Loss Tracker Agent evaluation framework.

This script provides convenient commands to run different test suites
and generate reports for the comprehensive testing framework.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running command: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Weight Loss Tracker Agent - Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit            # Run unit tests only
  python run_tests.py --coverage        # Run with coverage report
  python run_tests.py --performance     # Run performance tests
  python run_tests.py --ci              # Run CI-optimized test suite
        """
    )

    parser.add_argument('--unit', action='store_true',
                       help='Run unit tests only')
    parser.add_argument('--integration', action='store_true',
                       help='Run integration tests only')
    parser.add_argument('--e2e', action='store_true',
                       help='Run end-to-end tests only')
    parser.add_argument('--performance', action='store_true',
                       help='Run performance tests only')
    parser.add_argument('--coverage', action='store_true',
                       help='Generate coverage report')
    parser.add_argument('--html', action='store_true',
                       help='Generate HTML coverage report')
    parser.add_argument('--ci', action='store_true',
                       help='Run CI-optimized test suite (no slow tests)')
    parser.add_argument('--parallel', type=int, metavar='N',
                       help='Run tests in parallel with N workers')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--fail-fast', action='store_true',
                       help='Stop on first failure')

    args = parser.parse_args()

    # Determine test paths
    test_paths = []
    if args.unit:
        test_paths.append('tests/unit/')
    elif args.integration:
        test_paths.append('tests/integration/')
    elif args.e2e:
        test_paths.append('tests/e2e/')
    elif args.performance:
        test_paths.append('tests/performance/')
    else:
        test_paths.append('tests/')  # All tests

    # Build pytest command
    cmd = ['pytest']

    # Add test paths
    cmd.extend(test_paths)

    # Add coverage options
    if args.coverage or args.html or args.ci:
        cmd.extend(['--cov=.', '--cov-report=term-missing'])
        if args.html:
            cmd.append('--cov-report=html')
        if args.ci:
            cmd.append('--cov-report=xml')

    # Add parallel execution
    if args.parallel:
        cmd.extend(['-n', str(args.parallel)])
    elif args.ci:
        cmd.extend(['-n', 'auto'])

    # Add other options
    if args.verbose:
        cmd.append('-v')
    if args.fail_fast:
        cmd.append('--tb=short')
    if args.ci:
        cmd.extend(['-m', 'not slow'])  # Skip slow tests in CI

    # Run the tests
    success = run_command(cmd, "Running test suite")

    if success:
        print("\n✅ All tests passed!")

        if args.coverage or args.html:
            print("\n📊 Coverage report generated")
            if args.html:
                print("   Open htmlcov/index.html to view detailed coverage report")

        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())