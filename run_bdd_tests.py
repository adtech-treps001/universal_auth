#!/usr/bin/env python3
"""
Comprehensive BDD Test Runner for Universal Auth System

This script provides a complete BDD testing solution with Playwright,
supporting mock testing, integration testing, and various execution modes.
"""

import os
import sys
import subprocess
import argparse
import time
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

class BDDTestRunner:
    """Comprehensive BDD test runner with Playwright"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.bdd_dir = self.base_dir / "tests" / "bdd"
        self.results_dir = self.base_dir / "test_results"
        self.results = {}
        
    def check_system_availability(self) -> Dict[str, bool]:
        """Check if the Universal Auth system is running"""
        services = {
            'frontend': 'http://localhost:3000',
            'backend': 'http://localhost:8000/health',
            'nginx': 'http://localhost:80/health'
        }
        
        status = {}
        for service, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                status[service] = response.status_code == 200
            except requests.RequestException:
                status[service] = False
        
        return status
    
    def setup_test_environment(self) -> bool:
        """Set up the test environment"""
        print("🔧 Setting up BDD test environment...")
        
        # Create test results directory
        self.results_dir.mkdir(exist_ok=True)
        (self.results_dir / "screenshots").mkdir(exist_ok=True)
        (self.results_dir / "videos").mkdir(exist_ok=True)
        (self.results_dir / "reports").mkdir(exist_ok=True)
        
        # Check if BDD directory exists
        if not self.bdd_dir.exists():
            print(f"❌ BDD test directory not found: {self.bdd_dir}")
            return False
        
        # Install requirements
        requirements_file = self.bdd_dir / "requirements.txt"
        if requirements_file.exists():
            print("📦 Installing BDD test requirements...")
            result = subprocess.run([
                "pip", "install", "-r", str(requirements_file)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Failed to install requirements: {result.stderr}")
                return False
        
        # Install Playwright browsers
        print("🎭 Installing Playwright browsers...")
        result = subprocess.run([
            "playwright", "install"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"⚠️  Playwright browser installation warning: {result.stderr}")
            # Continue anyway as browsers might already be installed
        
        print("✅ Test environment setup complete")
        return True
    
    def run_mock_tests(self, verbose: bool = False, markers: List[str] = None) -> Dict[str, Any]:
        """Run BDD tests in mock mode (no system required)"""
        print("🎭 Running BDD Tests in Mock Mode...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.bdd_dir / "step_definitions"),
            "--tb=short",
            "--html=" + str(self.results_dir / "bdd_mock_tests.html"),
            "--self-contained-html",
            "--junit-xml=" + str(self.results_dir / "bdd_mock_tests.xml")
        ]
        
        if verbose:
            cmd.append("-v")
        
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # Set environment variables for mock mode
        env = os.environ.copy()
        env.update({
            "HEADLESS": "true",
            "BASE_URL": "http://localhost:3000",
            "API_URL": "http://localhost:8000",
            "MOCK_MODE": "true",
            "PYTHONPATH": str(self.bdd_dir)
        })
        
        result = subprocess.run(cmd, cwd=self.bdd_dir, env=env, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
            "mode": "mock"
        }
    
    def run_integration_tests(self, headless: bool = True, verbose: bool = False, 
                            markers: List[str] = None) -> Dict[str, Any]:
        """Run BDD tests against live system"""
        print("🔗 Running BDD Integration Tests...")
        
        # Check system availability
        system_status = self.check_system_availability()
        
        if not any(system_status.values()):
            print("⚠️  Universal Auth system not detected. Attempting to start...")
            
            # Try to start the system
            start_result = self.start_system()
            if not start_result:
                return {
                    "success": False,
                    "output": "",
                    "error": "Failed to start Universal Auth system",
                    "return_code": 1,
                    "mode": "integration"
                }
        
        print("✅ System is ready for integration testing")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.bdd_dir / "step_definitions"),
            "--tb=short",
            "--html=" + str(self.results_dir / "bdd_integration_tests.html"),
            "--self-contained-html",
            "--junit-xml=" + str(self.results_dir / "bdd_integration_tests.xml")
        ]
        
        if verbose:
            cmd.append("-v")
        
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # Set environment variables for integration mode
        env = os.environ.copy()
        env.update({
            "HEADLESS": "true" if headless else "false",
            "BASE_URL": "http://localhost:3000",
            "API_URL": "http://localhost:8000",
            "INTEGRATION_MODE": "true",
            "PYTHONPATH": str(self.bdd_dir)
        })
        
        result = subprocess.run(cmd, cwd=self.bdd_dir, env=env, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
            "mode": "integration"
        }
    
    def start_system(self) -> bool:
        """Start the Universal Auth system"""
        print("🚀 Starting Universal Auth system...")
        
        # Try Docker Compose first
        docker_compose_file = self.base_dir / "docker-compose.yml"
        if docker_compose_file.exists():
            result = subprocess.run([
                "docker-compose", "up", "-d"
            ], cwd=self.base_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("⏳ Waiting for services to be ready...")
                return self.wait_for_system_ready()
        
        # Try deployment script
        deploy_script = self.base_dir / "scripts" / "deploy.py"
        if deploy_script.exists():
            result = subprocess.run([
                "python", str(deploy_script)
            ], cwd=self.base_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                return self.wait_for_system_ready()
        
        print("❌ Could not start Universal Auth system")
        return False
    
    def wait_for_system_ready(self, max_wait: int = 120) -> bool:
        """Wait for the system to be ready"""
        wait_time = 0
        
        while wait_time < max_wait:
            system_status = self.check_system_availability()
            
            if system_status.get('frontend', False) or system_status.get('backend', False):
                print("✅ System is ready!")
                return True
            
            time.sleep(5)
            wait_time += 5
            print(f"  Waiting... ({wait_time}s/{max_wait}s)")
        
        print("❌ System failed to start within timeout")
        return False
    
    def run_specific_feature(self, feature: str, headless: bool = True, 
                           verbose: bool = False) -> Dict[str, Any]:
        """Run tests for a specific feature"""
        print(f"🎯 Running BDD tests for feature: {feature}")
        
        feature_file = self.bdd_dir / "features" / f"{feature}.feature"
        if not feature_file.exists():
            return {
                "success": False,
                "output": "",
                "error": f"Feature file not found: {feature_file}",
                "return_code": 1,
                "mode": "feature"
            }
        
        cmd = [
            "python", "-m", "pytest",
            str(self.bdd_dir / "step_definitions" / f"test_{feature}_steps.py"),
            "--tb=short",
            "--html=" + str(self.results_dir / f"bdd_{feature}_tests.html"),
            "--self-contained-html",
            "--junit-xml=" + str(self.results_dir / f"bdd_{feature}_tests.xml")
        ]
        
        if verbose:
            cmd.append("-v")
        
        env = os.environ.copy()
        env.update({
            "HEADLESS": "true" if headless else "false",
            "BASE_URL": "http://localhost:3000",
            "API_URL": "http://localhost:8000",
            "PYTHONPATH": str(self.bdd_dir)
        })
        
        result = subprocess.run(cmd, cwd=self.bdd_dir, env=env, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
            "mode": "feature",
            "feature": feature
        }
    
    def run_performance_tests(self, headless: bool = True, verbose: bool = False) -> Dict[str, Any]:
        """Run performance-focused BDD tests"""
        print("⚡ Running BDD Performance Tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.bdd_dir / "step_definitions"),
            "-m", "performance",
            "--tb=short",
            "--html=" + str(self.results_dir / "bdd_performance_tests.html"),
            "--self-contained-html",
            "--junit-xml=" + str(self.results_dir / "bdd_performance_tests.xml")
        ]
        
        if verbose:
            cmd.append("-v")
        
        env = os.environ.copy()
        env.update({
            "HEADLESS": "true" if headless else "false",
            "BASE_URL": "http://localhost:3000",
            "API_URL": "http://localhost:8000",
            "PERFORMANCE_MODE": "true",
            "PYTHONPATH": str(self.bdd_dir)
        })
        
        result = subprocess.run(cmd, cwd=self.bdd_dir, env=env, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
            "mode": "performance"
        }
    
    def run_security_tests(self, headless: bool = True, verbose: bool = False) -> Dict[str, Any]:
        """Run security-focused BDD tests"""
        print("🔒 Running BDD Security Tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.bdd_dir / "step_definitions"),
            "-m", "security",
            "--tb=short",
            "--html=" + str(self.results_dir / "bdd_security_tests.html"),
            "--self-contained-html",
            "--junit-xml=" + str(self.results_dir / "bdd_security_tests.xml")
        ]
        
        if verbose:
            cmd.append("-v")
        
        env = os.environ.copy()
        env.update({
            "HEADLESS": "true" if headless else "false",
            "BASE_URL": "http://localhost:3000",
            "API_URL": "http://localhost:8000",
            "SECURITY_MODE": "true",
            "PYTHONPATH": str(self.bdd_dir)
        })
        
        result = subprocess.run(cmd, cwd=self.bdd_dir, env=env, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
            "mode": "security"
        }
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        print("📊 Generating comprehensive BDD test report...")
        
        total_suites = len(self.results)
        passed_suites = sum(1 for result in self.results.values() if result["success"])
        failed_suites = total_suites - passed_suites
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_suites": total_suites,
                "passed_suites": passed_suites,
                "failed_suites": failed_suites,
                "success_rate": (passed_suites / total_suites * 100) if total_suites > 0 else 0
            },
            "results": self.results,
            "environment": {
                "base_url": os.getenv('BASE_URL', 'http://localhost:3000'),
                "api_url": os.getenv('API_URL', 'http://localhost:8000'),
                "headless": os.getenv('HEADLESS', 'true'),
                "browser": os.getenv('BROWSER', 'chromium')
            }
        }
        
        # Save report
        report_file = self.results_dir / "bdd_comprehensive_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        # Generate HTML summary
        self.generate_html_summary(report)
        
        return report
    
    def generate_html_summary(self, report: Dict[str, Any]):
        """Generate HTML summary report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Universal Auth BDD Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
                .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
                .metric {{ background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }}
                .success {{ background: #d4edda; color: #155724; }}
                .failure {{ background: #f8d7da; color: #721c24; }}
                .results {{ margin: 20px 0; }}
                .result-item {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ccc; }}
                .result-success {{ border-left-color: #28a745; }}
                .result-failure {{ border-left-color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎭 Universal Auth BDD Test Report</h1>
                <p>Generated: {report['timestamp']}</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <h3>Total Suites</h3>
                    <div>{report['summary']['total_suites']}</div>
                </div>
                <div class="metric success">
                    <h3>Passed</h3>
                    <div>{report['summary']['passed_suites']}</div>
                </div>
                <div class="metric failure">
                    <h3>Failed</h3>
                    <div>{report['summary']['failed_suites']}</div>
                </div>
                <div class="metric">
                    <h3>Success Rate</h3>
                    <div>{report['summary']['success_rate']:.1f}%</div>
                </div>
            </div>
            
            <div class="results">
                <h2>Test Results</h2>
        """
        
        for test_type, result in report['results'].items():
            status_class = "result-success" if result['success'] else "result-failure"
            status_text = "✅ PASSED" if result['success'] else "❌ FAILED"
            
            html_content += f"""
                <div class="result-item {status_class}">
                    <h3>{test_type.replace('_', ' ').title()} {status_text}</h3>
                    <p>Mode: {result.get('mode', 'unknown')}</p>
                    {f'<p>Feature: {result.get("feature", "")}</p>' if result.get('feature') else ''}
                    {f'<p>Error: {result.get("error", "")[:200]}...</p>' if not result['success'] and result.get('error') else ''}
                </div>
            """
        
        html_content += """
            </div>
            
            <div class="environment">
                <h2>Environment</h2>
                <ul>
        """
        
        for key, value in report['environment'].items():
            html_content += f"<li><strong>{key}:</strong> {value}</li>"
        
        html_content += """
                </ul>
            </div>
        </body>
        </html>
        """
        
        summary_file = self.results_dir / "bdd_summary.html"
        with open(summary_file, "w") as f:
            f.write(html_content)
        
        print(f"📄 HTML summary report: {summary_file}")
    
    def run_all_tests(self, mode: str = "mock", headless: bool = True, 
                     verbose: bool = False, markers: List[str] = None) -> Dict[str, Any]:
        """Run all BDD tests"""
        print(f"🚀 Running Universal Auth BDD Test Suite - Mode: {mode}")
        print("=" * 60)
        
        # Set up environment
        if not self.setup_test_environment():
            return {"success": False, "error": "Failed to set up test environment"}
        
        # Run tests based on mode
        if mode == "mock":
            self.results["mock_tests"] = self.run_mock_tests(verbose, markers)
        elif mode == "integration":
            self.results["integration_tests"] = self.run_integration_tests(headless, verbose, markers)
        elif mode == "all":
            self.results["mock_tests"] = self.run_mock_tests(verbose, markers)
            self.results["integration_tests"] = self.run_integration_tests(headless, verbose, markers)
            self.results["performance_tests"] = self.run_performance_tests(headless, verbose)
            self.results["security_tests"] = self.run_security_tests(headless, verbose)
        
        # Generate comprehensive report
        report = self.generate_comprehensive_report()
        
        # Print summary
        self.print_summary(report)
        
        return report
    
    def print_summary(self, report: Dict[str, Any]):
        """Print test summary"""
        print("\\n" + "=" * 60)
        print("📋 BDD TEST SUMMARY")
        print("=" * 60)
        
        for test_type, result in self.results.items():
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            mode = result.get("mode", "unknown")
            print(f"{test_type.replace('_', ' ').title():20} {status:10} ({mode})")
            
            if not result["success"] and result.get("error"):
                error_preview = result["error"][:100] + "..." if len(result["error"]) > 100 else result["error"]
                print(f"{'':20} Error: {error_preview}")
        
        print(f"\\nOverall Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"Test Reports: {self.results_dir}/")
        print(f"HTML Summary: {self.results_dir}/bdd_summary.html")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Universal Auth BDD Test Runner with Playwright",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_bdd_tests.py --mode mock                    # Run mock tests
  python run_bdd_tests.py --mode integration --headed    # Run integration tests with browser
  python run_bdd_tests.py --mode all --verbose           # Run all tests with verbose output
  python run_bdd_tests.py --feature authentication       # Run specific feature
  python run_bdd_tests.py --markers oauth,security       # Run tests with specific markers
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["mock", "integration", "all"],
        default="mock",
        help="Test execution mode"
    )
    
    parser.add_argument(
        "--feature",
        help="Run tests for specific feature (authentication, admin_panel, external_integration)"
    )
    
    parser.add_argument(
        "--markers",
        help="Comma-separated list of pytest markers to run (oauth, otp, admin, security, etc.)"
    )
    
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run tests in headed mode (show browser)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--base-dir",
        help="Base directory of the project"
    )
    
    args = parser.parse_args()
    
    # Parse markers
    markers = args.markers.split(",") if args.markers else None
    
    # Create test runner
    runner = BDDTestRunner(args.base_dir)
    
    try:
        if args.feature:
            # Run specific feature
            result = runner.run_specific_feature(
                args.feature,
                headless=not args.headed,
                verbose=args.verbose
            )
            success = result["success"]
        else:
            # Run all tests
            report = runner.run_all_tests(
                mode=args.mode,
                headless=not args.headed,
                verbose=args.verbose,
                markers=markers
            )
            success = report["summary"]["failed_suites"] == 0
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\\n🛑 BDD tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\\n💥 BDD test runner error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()