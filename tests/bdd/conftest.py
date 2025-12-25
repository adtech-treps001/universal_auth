"""
Pytest configuration for BDD tests with Playwright

This module provides fixtures and configuration for running BDD tests
with Playwright browser automation.
"""

import pytest
import os
import json
import time
from pathlib import Path
from typing import Generator, Dict, Any
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page
from faker import Faker

# Initialize Faker for test data generation
fake = Faker()

# Test configuration
BASE_URL = os.getenv('BASE_URL', 'http://localhost:3000')
API_URL = os.getenv('API_URL', 'http://localhost:8000')
HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'
BROWSER_TYPE = os.getenv('BROWSER', 'chromium')  # chromium, firefox, webkit
SLOW_MO = int(os.getenv('SLOW_MO', '0'))  # Slow down operations for debugging

# Test data configuration
TEST_USER_EMAIL = os.getenv('TEST_USER_EMAIL', 'test@example.com')
TEST_MOBILE_NUMBER = os.getenv('TEST_MOBILE_NUMBER', '+919876543210')
MOCK_OTP = os.getenv('MOCK_OTP', '123456')

@pytest.fixture(scope="session")
def playwright() -> Generator[Playwright, None, None]:
    """Playwright instance for the test session"""
    with sync_playwright() as p:
        yield p

@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Browser launch arguments"""
    args = []
    
    # Add CI-specific arguments
    if os.getenv('CI'):
        args.extend([
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor'
        ])
    
    return {
        'headless': HEADLESS,
        'slow_mo': SLOW_MO,
        'args': args
    }

@pytest.fixture(scope="session")
def browser(playwright: Playwright, browser_type_launch_args) -> Generator[Browser, None, None]:
    """Browser instance for the test session"""
    browser_type = getattr(playwright, BROWSER_TYPE)
    browser = browser_type.launch(**browser_type_launch_args)
    yield browser
    browser.close()

@pytest.fixture
def browser_context_args():
    """Browser context arguments"""
    return {
        'viewport': {'width': 1280, 'height': 720},
        'ignore_https_errors': True,
        'java_script_enabled': True,
        'accept_downloads': True,
        'record_video_dir': 'test_results/videos' if not HEADLESS else None,
        'record_video_size': {'width': 1280, 'height': 720} if not HEADLESS else None
    }

@pytest.fixture
def context(browser: Browser, browser_context_args) -> Generator[BrowserContext, None, None]:
    """Browser context for each test"""
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()

@pytest.fixture
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Page instance for each test"""
    page = context.new_page()
    
    # Set up page event listeners for debugging
    if not HEADLESS:
        page.on('console', lambda msg: print(f'Console: {msg.text}'))
        page.on('pageerror', lambda error: print(f'Page Error: {error}'))
    
    yield page
    
    # Take screenshot on test failure
    if hasattr(page, '_test_failed') and page._test_failed:
        screenshot_dir = Path('test_results/screenshots')
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        test_name = os.environ.get('PYTEST_CURRENT_TEST', 'unknown_test').split('::')[-1]
        screenshot_path = screenshot_dir / f'{test_name}_{timestamp}.png'
        
        try:
            page.screenshot(path=str(screenshot_path))
            print(f'Screenshot saved: {screenshot_path}')
        except Exception as e:
            print(f'Failed to take screenshot: {e}')
    
    page.close()

@pytest.fixture
def base_url() -> str:
    """Base URL for the application"""
    return BASE_URL

@pytest.fixture
def api_url() -> str:
    """API URL for the backend"""
    return API_URL

@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Test user data for authentication scenarios"""
    return {
        'email': TEST_USER_EMAIL,
        'mobile_number': TEST_MOBILE_NUMBER,
        'otp': MOCK_OTP,
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
        'company': fake.company(),
        'bio': fake.text(max_nb_chars=100),
        'website': fake.url()
    }

@pytest.fixture
def admin_user_data() -> Dict[str, Any]:
    """Admin user data for admin panel testing"""
    return {
        'email': 'admin@universal-auth.local',
        'password': 'admin123',
        'first_name': 'Admin',
        'last_name': 'User'
    }

@pytest.fixture
def mock_oauth_data() -> Dict[str, Any]:
    """Mock OAuth provider data"""
    return {
        'google': {
            'client_id': 'mock_google_client_id',
            'redirect_uri': f'{BASE_URL}/auth/callback/google',
            'scope': 'openid email profile'
        },
        'github': {
            'client_id': 'mock_github_client_id',
            'redirect_uri': f'{BASE_URL}/auth/callback/github',
            'scope': 'user:email'
        },
        'linkedin': {
            'client_id': 'mock_linkedin_client_id',
            'redirect_uri': f'{BASE_URL}/auth/callback/linkedin',
            'scope': 'r_liteprofile r_emailaddress'
        }
    }

@pytest.fixture
def mock_project_data() -> Dict[str, Any]:
    """Mock project data for testing"""
    return {
        'name': f'Test Project {fake.random_int(1000, 9999)}',
        'description': fake.text(max_nb_chars=200),
        'domain': f'test-{fake.random_int(1000, 9999)}.example.com',
        'callback_urls': [
            f'https://test-{fake.random_int(1000, 9999)}.example.com/callback',
            f'https://test-{fake.random_int(1000, 9999)}.example.com/auth/callback'
        ]
    }

# Pytest hooks for BDD integration
def pytest_bdd_step_error(request, feature, scenario, step, step_func, step_func_args, exception):
    """Handle BDD step errors"""
    print(f'\\n❌ BDD Step Error:')
    print(f'   Feature: {feature.filename}')
    print(f'   Scenario: {scenario.name}')
    print(f'   Step: {step.name}')
    print(f'   Error: {exception}')
    
    # Mark page for screenshot on failure
    if 'page' in step_func_args:
        page = step_func_args['page']
        page._test_failed = True

def pytest_bdd_before_scenario(request, feature, scenario):
    """Before each scenario"""
    print(f'\\n🎬 Starting scenario: {scenario.name}')

def pytest_bdd_after_scenario(request, feature, scenario):
    """After each scenario"""
    print(f'✅ Completed scenario: {scenario.name}')

def pytest_bdd_before_step(request, feature, scenario, step, step_func):
    """Before each step"""
    if not HEADLESS:
        print(f'   🔸 {step.name}')

def pytest_bdd_after_step(request, feature, scenario, step, step_func, step_func_args):
    """After each step"""
    pass

# Custom pytest markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line('markers', 'oauth: OAuth authentication tests')
    config.addinivalue_line('markers', 'otp: OTP authentication tests')
    config.addinivalue_line('markers', 'admin: Admin panel tests')
    config.addinivalue_line('markers', 'integration: External integration tests')
    config.addinivalue_line('markers', 'security: Security-focused tests')
    config.addinivalue_line('markers', 'performance: Performance tests')
    config.addinivalue_line('markers', 'mobile: Mobile-specific tests')
    config.addinivalue_line('markers', 'progressive: Progressive profiling tests')
    config.addinivalue_line('markers', 'error: Error handling tests')
    config.addinivalue_line('markers', 'slow: Slow tests (deselect with -m \"not slow\")')

# Test environment setup
@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """Set up test environment before running tests"""
    print('🔧 Setting up BDD test environment...')
    
    # Create test results directories
    test_dirs = [
        'test_results',
        'test_results/screenshots',
        'test_results/videos',
        'test_results/reports'
    ]
    
    for dir_path in test_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Log test configuration
    config_info = {
        'base_url': BASE_URL,
        'api_url': API_URL,
        'headless': HEADLESS,
        'browser': BROWSER_TYPE,
        'slow_mo': SLOW_MO
    }
    
    print('📋 Test Configuration:')
    for key, value in config_info.items():
        print(f'   {key}: {value}')
    
    yield
    
    print('🧹 Cleaning up test environment...')

# Utility fixtures for common operations
@pytest.fixture
def login_user(page: Page, base_url: str, test_user_data: Dict[str, Any]):
    """Utility fixture to log in a user"""
    def _login(email: str = None, provider: str = 'email'):
        email = email or test_user_data['email']
        
        page.goto(f'{base_url}/login')
        
        if provider == 'email':
            # Mock email login
            page.fill('[data-testid=\"email-input\"]', email)
            page.fill('[data-testid=\"password-input\"]', 'password123')
            page.click('[data-testid=\"login-button\"]')
        elif provider in ['google', 'github', 'linkedin']:
            # Mock OAuth login
            page.click(f'[data-testid=\"{provider}-signin\"]')
            # Simulate OAuth callback
            page.goto(f'{base_url}/auth/callback/{provider}?code=mock_code&state=mock_state')
        
        # Wait for login to complete
        page.wait_for_selector('[data-testid=\"user-menu\"], .user-profile, .dashboard', timeout=10000)
        
        return page
    
    return _login

@pytest.fixture
def create_mock_project(page: Page, api_url: str, mock_project_data: Dict[str, Any]):
    """Utility fixture to create a mock project"""
    def _create_project(project_data: Dict[str, Any] = None):
        project_data = project_data or mock_project_data
        
        # Mock API call to create project
        response = page.request.post(
            f'{api_url}/api/projects',
            data=json.dumps(project_data),
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status == 201:
            return response.json()
        else:
            raise Exception(f'Failed to create project: {response.status}')
    
    return _create_project

# Performance monitoring fixtures
@pytest.fixture
def performance_monitor(page: Page):
    """Monitor page performance during tests"""
    metrics = {}
    
    def start_monitoring():
        # Start performance monitoring
        page.evaluate('performance.mark(\"test-start\")')
        metrics['start_time'] = time.time()
    
    def stop_monitoring():
        # Stop performance monitoring
        page.evaluate('performance.mark(\"test-end\")')
        page.evaluate('performance.measure(\"test-duration\", \"test-start\", \"test-end\")')
        
        metrics['end_time'] = time.time()
        metrics['duration'] = metrics['end_time'] - metrics['start_time']
        
        # Get browser performance metrics
        try:
            perf_data = page.evaluate('''
                () => {
                    const navigation = performance.getEntriesByType('navigation')[0];
                    const measures = performance.getEntriesByType('measure');
                    
                    return {
                        load_time: navigation ? navigation.loadEventEnd - navigation.loadEventStart : 0,
                        dom_content_loaded: navigation ? navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart : 0,
                        test_measures: measures.map(m => ({name: m.name, duration: m.duration}))
                    };
                }
            ''')
            metrics.update(perf_data)
        except Exception as e:
            print(f'Warning: Could not collect performance metrics: {e}')
        
        return metrics
    
    return {
        'start': start_monitoring,
        'stop': stop_monitoring,
        'metrics': metrics
    }

# Accessibility testing fixture
@pytest.fixture
def accessibility_checker(page: Page):
    """Check accessibility compliance during tests"""
    def check_accessibility():
        # Inject axe-core for accessibility testing
        page.add_script_tag(url='https://unpkg.com/axe-core@4.7.0/axe.min.js')
        
        # Run accessibility check
        results = page.evaluate('''
            async () => {
                const results = await axe.run();
                return {
                    violations: results.violations.length,
                    passes: results.passes.length,
                    incomplete: results.incomplete.length,
                    details: results.violations.map(v => ({
                        id: v.id,
                        impact: v.impact,
                        description: v.description,
                        nodes: v.nodes.length
                    }))
                };
            }
        ''')
        
        return results
    
    return check_accessibility