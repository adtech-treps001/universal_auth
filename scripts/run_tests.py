#!/usr/bin/env python3
"""
Comprehensive Test Runner for Universal Auth System

This script runs all types of tests including unit tests, property tests,
integration tests, and BDD tests with proper reporting and coverage.
"""

import os
import sys
import subprocess
import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Any

class TestRunner:
    """Comprehensive test runner"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.backend_dir = self.base_dir / "backend"
        self.bdd_dir = self.base_dir / "tests" / "bdd"
        self.results = {}
        
    def run_unit_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run unit tests"""
        print("🧪 Running Unit Tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.backend_dir / "tests"),
            "--tb=short",
            "--cov=backend",
            "--cov-report=html:test_results/coverage_unit",
            "--cov-report=json:test_results/coverage_unit.json",
            "--junit-xml=test_results/unit_tests.xml",
            "--html=test_results/unit_tests.html",
            "--self-contained-html"
        ]
        
        if verbose:
            cmd.append("-v")
        
        # Exclude property tests and BDD tests
        cmd.extend([
            "--ignore", str(self.backend_dir / "tests" / "test_*_properties.py"),
            "--ignore", str(self.bdd_dir)
        ])
        
        result = subprocess.run(cmd, cwd=self.backend_dir, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode
        }
    
    def run_property_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run property-based tests"""
        print("🔍 Running Property-Based Tests...")
        
        # Find all property test files
        property_test_files = list(self.backend_dir.glob("tests/test_*_properties.py"))
        
        if not property_test_files:
            return {
                "success": True,
                "output": "No property test files found",
                "error": "",
                "return_code": 0
            }
        
        cmd = [
            "python", "-m", "pytest"
        ] + [str(f) for f in property_test_files] + [
            "--tb=short",
            "--junit-xml=test_results/property_tests.xml",
            "--html=test_results/property_tests.html",
            "--self-contained-html",
            "--hypothesis-show-statistics"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(cmd, cwd=self.backend_dir, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode
        }
    
    def run_integration_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run integration tests"""
        print("🔗 Running Integration Tests...")
        
        # Integration tests are typically in a separate directory or marked
        integration_files = list(self.backend_dir.glob("tests/integration/test_*.py"))
        
        if not integration_files:
            # If no separate integration directory, look for integration test markers
            cmd = [
                "python", "-m", "pytest",
                str(self.backend_dir / "tests"),
                "-m", "integration",
                "--tb=short",
                "--junit-xml=test_results/integration_tests.xml",
                "--html=test_results/integration_tests.html",
                "--self-contained-html"
            ]
        else:
            cmd = [
                "python", "-m", "pytest"
            ] + [str(f) for f in integration_files] + [
                "--tb=short",
                "--junit-xml=test_results/integration_tests.xml",
                "--html=test_results/integration_tests.html",
                "--self-contained-html"
            ]
        
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(cmd, cwd=self.backend_dir, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode
        }
    
    def run_bdd_tests(self, verbose: bool = False, headless: bool = True) -> Dict[str, Any]:
        """Run BDD tests with Playwright"""
        print("🎭 Running BDD Tests with Playwright...")
        
        if not self.bdd_dir.exists():
            return {
                "success": False,
                "output": "",
                "error": f"BDD test directory not found: {self.bdd_dir}",
                "return_code": 1
            }
        
        # Set environment variables for BDD tests
        env = os.environ.copy()
        env.update({
            "HEADLESS": "true" if headless else "false",
            "BASE_URL": "http://localhost:3000",
            "API_URL": "http://localhost:8000",
            "PYTHONPATH": str(self.bdd_dir)
        })
        
        cmd = [
            "python", "-m", "pytest",
            str(self.bdd_dir / "step_definitions"),
            "--tb=short",
            "--junit-xml=test_results/bdd_tests.xml",
            "--html=test_results/bdd_tests.html",
            "--self-contained-html"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(cmd, cwd=self.bdd_dir, env=env, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode
        }
    
    def run_security_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run security-focused tests"""
        print("🔒 Running Security Tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.backend_dir / "tests"),
            "-k", "security or auth or permission or access",
            "--tb=short",
            "--junit-xml=test_results/security_tests.xml",
            "--html=test_results/security_tests.html",
            "--self-contained-html"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(cmd, cwd=self.backend_dir, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode
        }
    
    def run_performance_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run performance tests"""
        print("⚡ Running Performance Tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.backend_dir / "tests"),
            "-k", "performance or benchmark or load",
            "--tb=short",
            "--junit-xml=test_results/performance_tests.xml",
            "--html=test_results/performance_tests.html",
            "--self-contained-html"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(cmd, cwd=self.backend_dir, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode
        }
    
    def setup_test_environment(self):
        """Set up test environment"""
        print("🔧 Setting up test environment...")
        
        # Create test results directory
        results_dir = self.base_dir / "test_results"
        results_dir.mkdir(exist_ok=True)
        
        # Install test dependencies
        requirements_files = [
            self.backend_dir / "requirements.txt",
            self.bdd_dir / "requirements.txt"
        ]
        
        for req_file in requirements_files:
            if req_file.exists():
                print(f"Installing requirements from {req_file}")
                subprocess.run([
                    "pip", "install", "-r", str(req_file)
                ], check=True)
        
        # Install Playwright browsers if BDD tests are enabled
        if self.bdd_dir.exists():
            print("Installing Playwright browsers...")
            subprocess.run(["playwright", "install"], check=True)
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        print("📊 Generating test report...")
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {},
            "results": self.results,
            "coverage": {}
        }
        
        # Calculate summary statistics
        for test_type, result in self.results.items():
            if result["success"]:
                # Parse test output for more detailed statistics
                # This is a simplified version - in practice, you'd parse XML/JSON reports
                passed_tests += 1
            else:
                failed_tests += 1
            total_tests += 1
        
        report["summary"] = {
            "total_test_suites": total_tests,
            "passed_suites": passed_tests,
            "failed_suites": failed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
        }
        
        # Load coverage data if available
        coverage_file = self.base_dir / "test_results" / "coverage_unit.json"
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    report["coverage"] = {
                        "total_coverage": coverage_data.get("totals", {}).get("percent_covered", 0),
                        "files": len(coverage_data.get("files", {})),
                        "lines_covered": coverage_data.get("totals", {}).get("covered_lines", 0),
                        "lines_total": coverage_data.get("totals", {}).get("num_statements", 0)
                    }
            except Exception as e:
                print(f"Warning: Could not load coverage data: {e}")
        
        # Save report
        report_file = self.base_dir / "test_results" / "test_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def run_all_tests(self, test_types: List[str] = None, verbose: bool = False, 
                     headless: bool = True) -> Dict[str, Any]:
        """Run all specified test types"""
        
        if test_types is None:
            test_types = ["unit", "property", "integration", "security"]
        
        print(f"🚀 Running Universal Auth System Tests: {', '.join(test_types)}")
        print("=" * 60)
        
        # Set up test environment
        self.setup_test_environment()
        
        # Run tests
        test_methods = {
            "unit": self.run_unit_tests,
            "property": self.run_property_tests,
            "integration": self.run_integration_tests,
            "bdd": self.run_bdd_tests,
            "security": self.run_security_tests,
            "performance": self.run_performance_tests
        }
        
        for test_type in test_types:
            if test_type in test_methods:
                if test_type == "bdd":
                    self.results[test_type] = test_methods[test_type](verbose, headless)
                else:
                    self.results[test_type] = test_methods[test_type](verbose)
            else:
                print(f"⚠️  Unknown test type: {test_type}")
        
        # Generate report
        report = self.generate_test_report()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        for test_type, result in self.results.items():
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            print(f"{test_type.upper():15} {status}")
            
            if not result["success"] and result["error"]:
                print(f"                Error: {result['error'][:100]}...")
        
        print(f"\nOverall Success Rate: {report['summary']['success_rate']:.1f}%")
        
        if "coverage" in report and report["coverage"]:
            print(f"Code Coverage: {report['coverage']['total_coverage']:.1f}%")
        
        print(f"\nDetailed reports available in: {self.base_dir}/test_results/")
        
        return report

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Universal Auth System Test Runner")
    
    parser.add_argument(
        "--types", 
        nargs="+", 
        choices=["unit", "property", "integration", "bdd", "security", "performance", "all"],
        default=["unit", "property", "security"],
        help="Types of tests to run"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run BDD tests in headed mode (show browser)"
    )
    
    parser.add_argument(
        "--base-dir",
        help="Base directory of the project"
    )
    
    args = parser.parse_args()
    
    # Handle "all" test type
    if "all" in args.types:
        args.types = ["unit", "property", "integration", "bdd", "security", "performance"]
    
    # Create test runner
    runner = TestRunner(args.base_dir)
    
    try:
        # Run tests
        report = runner.run_all_tests(
            test_types=args.types,
            verbose=args.verbose,
            headless=not args.headed
        )
        
        # Exit with appropriate code
        all_passed = all(result["success"] for result in runner.results.values())
        sys.exit(0 if all_passed else 1)
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test runner error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()