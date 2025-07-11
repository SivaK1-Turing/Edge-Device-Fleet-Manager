#!/usr/bin/env python3
"""
Test runner script for Edge Device Fleet Manager.

This script provides a comprehensive way to run tests with different configurations
and generate detailed reports.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> int:
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def run_unit_tests(verbose: bool = False, coverage: bool = False) -> int:
    """Run unit tests."""
    print("🧪 Running unit tests...")
    
    cmd = ["pytest", "tests/unit"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=edge_device_fleet_manager",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])
    
    return run_command(cmd)


def run_integration_tests(verbose: bool = False) -> int:
    """Run integration tests."""
    print("🔗 Running integration tests...")
    
    cmd = ["pytest", "tests/integration"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def run_plugin_tests(verbose: bool = False) -> int:
    """Run plugin-specific tests."""
    print("🔌 Running plugin tests...")
    
    cmd = ["pytest", "tests/unit/test_plugins.py"]
    
    if verbose:
        cmd.append("-v")
    
    # Run the specific test mentioned in the requirements
    specific_test = [
        "pytest", 
        "tests/unit/test_plugins.py::TestPluginSystem::test_plugin_load_error_continues_loading_others",
        "-v"
    ]
    
    print("Running specific plugin error handling test...")
    result1 = run_command(specific_test)
    
    print("Running all plugin tests...")
    result2 = run_command(cmd)
    
    return max(result1, result2)


def run_cli_tests(verbose: bool = False) -> int:
    """Run CLI tests."""
    print("💻 Running CLI tests...")
    
    cmd = ["pytest", "tests/unit/test_cli.py"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def run_config_tests(verbose: bool = False) -> int:
    """Run configuration tests."""
    print("⚙️ Running configuration tests...")
    
    cmd = ["pytest", "tests/unit/test_config.py"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def run_context_tests(verbose: bool = False) -> int:
    """Run context management tests."""
    print("🔄 Running context management tests...")
    
    cmd = ["pytest", "tests/unit/test_context.py"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def run_linting() -> int:
    """Run linting checks."""
    print("🔍 Running linting checks...")
    
    commands = [
        ["black", "--check", "edge_device_fleet_manager", "tests"],
        ["isort", "--check-only", "edge_device_fleet_manager", "tests"],
        ["flake8", "edge_device_fleet_manager", "tests"],
        ["mypy", "edge_device_fleet_manager"],
        ["bandit", "-r", "edge_device_fleet_manager"]
    ]
    
    exit_code = 0
    for cmd in commands:
        result = run_command(cmd)
        if result != 0:
            exit_code = result
    
    return exit_code


def run_security_checks() -> int:
    """Run security checks."""
    print("🔒 Running security checks...")
    
    commands = [
        ["bandit", "-r", "edge_device_fleet_manager", "-f", "json", "-o", "bandit-report.json"],
        ["safety", "check"]
    ]
    
    exit_code = 0
    for cmd in commands:
        result = run_command(cmd)
        if result != 0:
            exit_code = result
    
    return exit_code


def run_feature1_tests(verbose: bool = False, coverage: bool = False) -> int:
    """Run all Feature 1 related tests."""
    print("🎯 Running Feature 1: Meta-Driven CLI & Configuration tests...")
    
    test_functions = [
        lambda: run_plugin_tests(verbose),
        lambda: run_cli_tests(verbose),
        lambda: run_config_tests(verbose),
        lambda: run_context_tests(verbose),
    ]
    
    exit_code = 0
    for test_func in test_functions:
        result = test_func()
        if result != 0:
            exit_code = result
    
    # Run comprehensive coverage for Feature 1
    if coverage:
        print("📊 Generating coverage report for Feature 1...")
        cmd = [
            "pytest",
            "tests/unit/test_plugins.py",
            "tests/unit/test_cli.py", 
            "tests/unit/test_config.py",
            "tests/unit/test_context.py",
            "--cov=edge_device_fleet_manager.core",
            "--cov=edge_device_fleet_manager.cli",
            "--cov-report=html:htmlcov/feature1",
            "--cov-report=term-missing"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = run_command(cmd)
        if result != 0:
            exit_code = result
    
    return exit_code


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test runner for Edge Device Fleet Manager"
    )
    
    parser.add_argument(
        "test_type",
        choices=[
            "all", "unit", "integration", "plugins", "cli", 
            "config", "context", "feature1", "lint", "security"
        ],
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    
    args = parser.parse_args()
    
    # Set environment for testing
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DEBUG"] = "true"
    
    exit_code = 0
    
    if args.test_type == "all":
        print("🚀 Running all tests...")
        exit_code = max(
            run_unit_tests(args.verbose, args.coverage),
            run_integration_tests(args.verbose),
            run_linting(),
            run_security_checks()
        )
    elif args.test_type == "unit":
        exit_code = run_unit_tests(args.verbose, args.coverage)
    elif args.test_type == "integration":
        exit_code = run_integration_tests(args.verbose)
    elif args.test_type == "plugins":
        exit_code = run_plugin_tests(args.verbose)
    elif args.test_type == "cli":
        exit_code = run_cli_tests(args.verbose)
    elif args.test_type == "config":
        exit_code = run_config_tests(args.verbose)
    elif args.test_type == "context":
        exit_code = run_context_tests(args.verbose)
    elif args.test_type == "feature1":
        exit_code = run_feature1_tests(args.verbose, args.coverage)
    elif args.test_type == "lint":
        exit_code = run_linting()
    elif args.test_type == "security":
        exit_code = run_security_checks()
    
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
