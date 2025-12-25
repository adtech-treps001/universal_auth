#!/usr/bin/env python3
"""
Universal Auth System Deployment Script

This script handles local Docker deployment with comprehensive setup,
health checks, and testing capabilities.
"""

import os
import sys
import subprocess
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import requests
import docker
from docker.errors import DockerException

class UniversalAuthDeployer:
    """Universal Auth System deployment manager"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.docker_compose_file = self.base_dir / "docker-compose.yml"
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except DockerException as e:
            print(f"❌ Docker not available: {e}")
            sys.exit(1)
    
    def check_prerequisites(self) -> bool:
        """Check deployment prerequisites"""
        print("🔍 Checking prerequisites...")
        
        checks = []
        
        # Check Docker
        try:
            self.docker_client.ping()
            checks.append(("Docker", True, "Docker daemon is running"))
        except Exception as e:
            checks.append(("Docker", False, f"Docker daemon not available: {e}"))
        
        # Check Docker Compose
        try:
            result = subprocess.run(["docker-compose", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                checks.append(("Docker Compose", True, result.stdout.strip()))
            else:
                checks.append(("Docker Compose", False, "docker-compose command not found"))
        except FileNotFoundError:
            checks.append(("Docker Compose", False, "docker-compose not installed"))
        
        # Check docker-compose.yml
        if self.docker_compose_file.exists():
            checks.append(("Docker Compose File", True, f"Found at {self.docker_compose_file}"))
        else:
            checks.append(("Docker Compose File", False, f"Not found at {self.docker_compose_file}"))
        
        # Check required directories
        required_dirs = ["backend", "frontend", "nginx", "database", "policy"]
        for dir_name in required_dirs:
            dir_path = self.base_dir / dir_name
            if dir_path.exists():
                checks.append((f"{dir_name.title()} Directory", True, f"Found at {dir_path}"))
            else:
                checks.append((f"{dir_name.title()} Directory", False, f"Not found at {dir_path}"))
        
        # Print results
        all_passed = True
        for name, passed, message in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {name}: {message}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def setup_environment(self):
        """Set up deployment environment"""
        print("🔧 Setting up deployment environment...")
        
        # Create necessary directories
        directories = [
            "test_results",
            "logs",
            "nginx/ssl",
            "database/backups"
        ]
        
        for dir_name in directories:
            dir_path = self.base_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  📁 Created directory: {dir_path}")
        
        # Generate environment file if it doesn't exist
        env_file = self.base_dir / ".env"
        if not env_file.exists():
            self.generate_env_file(env_file)
        
        # Set up SSL certificates (self-signed for local development)
        ssl_dir = self.base_dir / "nginx" / "ssl"
        cert_file = ssl_dir / "cert.pem"
        key_file = ssl_dir / "key.pem"
        
        if not cert_file.exists() or not key_file.exists():
            self.generate_ssl_certificates(ssl_dir)
    
    def generate_env_file(self, env_file: Path):
        """Generate environment configuration file"""
        print("  🔐 Generating environment configuration...")
        
        import secrets
        
        env_content = f"""# Universal Auth System Environment Configuration
# Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}

# Database Configuration
DATABASE_URL=postgresql://auth_user:auth_password@postgres:5432/universal_auth
POSTGRES_DB=universal_auth
POSTGRES_USER=auth_user
POSTGRES_PASSWORD=auth_password

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# JWT Configuration
JWT_SECRET_KEY={secrets.token_urlsafe(64)}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRY_HOURS=24
JWT_REFRESH_TOKEN_EXPIRY_DAYS=30
JWT_ISSUER=universal-auth

# Encryption Configuration
ENCRYPTION_KEY={secrets.token_urlsafe(32)}

# OPA Configuration
OPA_URL=http://opa:8181

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development

# OAuth Provider Configuration (Add your credentials)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret

# Email Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Security Configuration
SECURITY_MONITORING_ENABLED=true
AUDIT_LOGGING_ENABLED=true
RATE_LIMITING_ENABLED=true

# Testing Configuration
TEST_DATABASE_URL=postgresql://auth_user:auth_password@postgres:5432/universal_auth_test
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print(f"  ✅ Environment file created: {env_file}")
        print("  ⚠️  Please update OAuth credentials in .env file before deployment")
    
    def generate_ssl_certificates(self, ssl_dir: Path):
        """Generate self-signed SSL certificates for local development"""
        print("  🔒 Generating SSL certificates...")
        
        try:
            # Generate private key
            subprocess.run([
                "openssl", "genrsa", "-out", str(ssl_dir / "key.pem"), "2048"
            ], check=True, capture_output=True)
            
            # Generate certificate
            subprocess.run([
                "openssl", "req", "-new", "-x509", "-key", str(ssl_dir / "key.pem"),
                "-out", str(ssl_dir / "cert.pem"), "-days", "365",
                "-subj", "/C=US/ST=State/L=City/O=Organization/CN=localhost"
            ], check=True, capture_output=True)
            
            print(f"  ✅ SSL certificates generated in {ssl_dir}")
            
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  Could not generate SSL certificates: {e}")
            print("  ℹ️  SSL will be disabled for this deployment")
        except FileNotFoundError:
            print("  ⚠️  OpenSSL not found, skipping SSL certificate generation")
    
    def build_images(self, no_cache: bool = False):
        """Build Docker images"""
        print("🏗️  Building Docker images...")
        
        cmd = ["docker-compose", "build"]
        if no_cache:
            cmd.append("--no-cache")
        
        result = subprocess.run(cmd, cwd=self.base_dir)
        
        if result.returncode != 0:
            print("❌ Failed to build Docker images")
            sys.exit(1)
        
        print("✅ Docker images built successfully")
    
    def start_services(self, services: List[str] = None):
        """Start Docker services"""
        print("🚀 Starting Universal Auth System services...")
        
        cmd = ["docker-compose", "up", "-d"]
        if services:
            cmd.extend(services)
        
        result = subprocess.run(cmd, cwd=self.base_dir)
        
        if result.returncode != 0:
            print("❌ Failed to start services")
            sys.exit(1)
        
        print("✅ Services started successfully")
    
    def wait_for_services(self, timeout: int = 300):
        """Wait for services to be healthy"""
        print("⏳ Waiting for services to be ready...")
        
        services = {
            "Database": "http://localhost:5432",  # Will check via Docker health
            "Redis": "http://localhost:6379",    # Will check via Docker health
            "OPA": "http://localhost:8181/health",
            "Backend API": "http://localhost:8000/health",
            "Frontend": "http://localhost:3000/health",
            "Nginx": "http://localhost:80/health"
        }
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_healthy = True
            
            # Check Docker container health
            try:
                containers = self.docker_client.containers.list()
                for container in containers:
                    if 'universal_auth' in container.name:
                        health = container.attrs.get('State', {}).get('Health', {})
                        if health and health.get('Status') != 'healthy':
                            all_healthy = False
                            break
            except Exception as e:
                print(f"  ⚠️  Error checking container health: {e}")
                all_healthy = False
            
            # Check HTTP endpoints
            for service_name, url in services.items():
                if url.startswith('http'):
                    try:
                        response = requests.get(url, timeout=5)
                        if response.status_code != 200:
                            all_healthy = False
                            break
                    except requests.RequestException:
                        all_healthy = False
                        break
            
            if all_healthy:
                print("✅ All services are healthy and ready")
                return True
            
            print("  ⏳ Services still starting up...")
            time.sleep(10)
        
        print(f"❌ Services did not become healthy within {timeout} seconds")
        return False
    
    def run_health_checks(self) -> Dict[str, Any]:
        """Run comprehensive health checks"""
        print("🏥 Running health checks...")
        
        checks = {}
        
        # Database health check
        try:
            response = requests.get("http://localhost:8000/api/health/database", timeout=10)
            checks["database"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds(),
                "details": response.json() if response.status_code == 200 else response.text
            }
        except Exception as e:
            checks["database"] = {"status": "unhealthy", "error": str(e)}
        
        # Redis health check
        try:
            response = requests.get("http://localhost:8000/api/health/redis", timeout=10)
            checks["redis"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds(),
                "details": response.json() if response.status_code == 200 else response.text
            }
        except Exception as e:
            checks["redis"] = {"status": "unhealthy", "error": str(e)}
        
        # OPA health check
        try:
            response = requests.get("http://localhost:8181/health", timeout=10)
            checks["opa"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            checks["opa"] = {"status": "unhealthy", "error": str(e)}
        
        # Backend API health check
        try:
            response = requests.get("http://localhost:8000/health", timeout=10)
            checks["backend"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds(),
                "details": response.json() if response.status_code == 200 else response.text
            }
        except Exception as e:
            checks["backend"] = {"status": "unhealthy", "error": str(e)}
        
        # Frontend health check
        try:
            response = requests.get("http://localhost:3000/health", timeout=10)
            checks["frontend"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            checks["frontend"] = {"status": "unhealthy", "error": str(e)}
        
        # Print results
        for service, check in checks.items():
            status_icon = "✅" if check["status"] == "healthy" else "❌"
            response_time = f" ({check.get('response_time', 0):.2f}s)" if 'response_time' in check else ""
            print(f"  {status_icon} {service.title()}: {check['status']}{response_time}")
            
            if check["status"] == "unhealthy" and "error" in check:
                print(f"    Error: {check['error']}")
        
        return checks
    
    def run_smoke_tests(self) -> bool:
        """Run smoke tests to verify basic functionality"""
        print("🧪 Running smoke tests...")
        
        tests = []
        
        # Test 1: API root endpoint
        try:
            response = requests.get("http://localhost:8000/api/", timeout=10)
            tests.append(("API Root", response.status_code == 200))
        except Exception as e:
            tests.append(("API Root", False))
        
        # Test 2: Authentication providers endpoint
        try:
            response = requests.get("http://localhost:8000/api/auth/providers", timeout=10)
            tests.append(("Auth Providers", response.status_code == 200))
        except Exception as e:
            tests.append(("Auth Providers", False))
        
        # Test 3: Frontend loading
        try:
            response = requests.get("http://localhost:3000/", timeout=10)
            tests.append(("Frontend", response.status_code == 200 and "Universal Auth" in response.text))
        except Exception as e:
            tests.append(("Frontend", False))
        
        # Test 4: Admin panel access (should redirect to login)
        try:
            response = requests.get("http://localhost:3000/admin", timeout=10, allow_redirects=False)
            tests.append(("Admin Panel", response.status_code in [200, 302, 401]))
        except Exception as e:
            tests.append(("Admin Panel", False))
        
        # Test 5: OPA policy endpoint
        try:
            response = requests.get("http://localhost:8181/v1/data", timeout=10)
            tests.append(("OPA Policies", response.status_code == 200))
        except Exception as e:
            tests.append(("OPA Policies", False))
        
        # Print results
        all_passed = True
        for test_name, passed in tests:
            status_icon = "✅" if passed else "❌"
            print(f"  {status_icon} {test_name}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def generate_test_data(self):
        """Generate test data using the mock data generator"""
        print("🎭 Generating test data...")
        
        script_path = self.base_dir / "scripts" / "generate_mock_data.py"
        if script_path.exists():
            result = subprocess.run([
                "python", str(script_path),
                "--users", "20",
                "--projects", "5",
                "--api-keys", "10",
                "--audit-logs", "100",
                "--output-dir", str(self.base_dir / "test_data")
            ], cwd=self.base_dir)
            
            if result.returncode == 0:
                print("✅ Test data generated successfully")
            else:
                print("⚠️  Failed to generate test data")
        else:
            print("⚠️  Mock data generator not found")
    
    def run_tests(self, test_types: List[str] = None):
        """Run automated tests"""
        print("🧪 Running automated tests...")
        
        if test_types is None:
            test_types = ["unit", "property"]
        
        script_path = self.base_dir / "scripts" / "run_tests.py"
        if script_path.exists():
            cmd = [
                "python", str(script_path),
                "--types"
            ] + test_types
            
            result = subprocess.run(cmd, cwd=self.base_dir)
            
            if result.returncode == 0:
                print("✅ All tests passed")
                return True
            else:
                print("❌ Some tests failed")
                return False
        else:
            print("⚠️  Test runner not found")
            return False
    
    def show_deployment_info(self):
        """Show deployment information"""
        print("\n" + "=" * 60)
        print("🎉 Universal Auth System Deployment Complete!")
        print("=" * 60)
        
        print("\n📍 Service URLs:")
        print("  🌐 Frontend:        http://localhost:3000")
        print("  🔧 Backend API:     http://localhost:8000")
        print("  📊 API Docs:        http://localhost:8000/docs")
        print("  🛡️  Admin Panel:     http://localhost:3000/admin")
        print("  🔍 OPA Console:     http://localhost:8181")
        print("  🔄 Nginx Proxy:     http://localhost:80")
        
        print("\n🔐 Default Credentials:")
        print("  📧 Email:    admin@universal-auth.local")
        print("  🔑 Password: admin123")
        
        print("\n📁 Important Directories:")
        print(f"  📊 Test Results:    {self.base_dir}/test_results/")
        print(f"  📝 Logs:            {self.base_dir}/logs/")
        print(f"  🎭 Test Data:       {self.base_dir}/test_data/")
        
        print("\n🛠️  Management Commands:")
        print("  📊 View logs:       docker-compose logs -f")
        print("  🔄 Restart:         docker-compose restart")
        print("  🛑 Stop:            docker-compose down")
        print("  🧹 Clean up:        docker-compose down -v --remove-orphans")
        
        print("\n🧪 Testing:")
        print("  🏃 Run tests:       python scripts/run_tests.py")
        print("  🎭 Generate data:   python scripts/generate_mock_data.py")
        print("  🌐 BDD tests:       python scripts/run_tests.py --types bdd")
    
    def deploy(self, build: bool = True, no_cache: bool = False, 
              generate_data: bool = True, run_tests: bool = True,
              test_types: List[str] = None):
        """Full deployment process"""
        print("🚀 Starting Universal Auth System Deployment")
        print("=" * 60)
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("❌ Prerequisites check failed")
            return False
        
        # Setup environment
        self.setup_environment()
        
        # Build images if requested
        if build:
            self.build_images(no_cache)
        
        # Start services
        self.start_services()
        
        # Wait for services to be ready
        if not self.wait_for_services():
            print("❌ Services failed to start properly")
            return False
        
        # Run health checks
        health_results = self.run_health_checks()
        
        # Run smoke tests
        if not self.run_smoke_tests():
            print("⚠️  Some smoke tests failed, but deployment continues")
        
        # Generate test data
        if generate_data:
            self.generate_test_data()
        
        # Run tests
        if run_tests:
            self.run_tests(test_types)
        
        # Show deployment info
        self.show_deployment_info()
        
        return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Universal Auth System Deployment")
    
    parser.add_argument("--no-build", action="store_true", help="Skip building Docker images")
    parser.add_argument("--no-cache", action="store_true", help="Build images without cache")
    parser.add_argument("--no-data", action="store_true", help="Skip generating test data")
    parser.add_argument("--no-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--test-types", nargs="+", choices=["unit", "property", "integration", "bdd", "security"], 
                       default=["unit", "property"], help="Types of tests to run")
    parser.add_argument("--base-dir", help="Base directory of the project")
    
    args = parser.parse_args()
    
    # Create deployer
    deployer = UniversalAuthDeployer(args.base_dir)
    
    try:
        # Run deployment
        success = deployer.deploy(
            build=not args.no_build,
            no_cache=args.no_cache,
            generate_data=not args.no_data,
            run_tests=not args.no_tests,
            test_types=args.test_types
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n🛑 Deployment interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Deployment error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()