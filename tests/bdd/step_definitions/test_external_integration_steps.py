"""
BDD Step definitions for external website integration scenarios
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
import os
import time
from faker import Faker

fake = Faker()

# Load scenarios from feature files
scenarios('../features/external_integration.feature')

@pytest.fixture
def test_website_url():
    return os.getenv('TEST_WEBSITE_URL', 'http://localhost:3001')

@pytest.fixture
def mock_website_data():
    return {
        'website_name': 'Test Integration Site',
        'tenant_id': 'test_tenant_123',
        'api_key': 'test_api_key_456',
        'redirect_url': 'http://localhost:3001/auth/callback'
    }

# Background steps
@given('I have a test website with Universal Auth integration')
def test_website_with_integration(page: Page, test_website_url, mock_website_data):
    """Set up test website with Universal Auth integration"""
    # Navigate to test website
    page.goto(test_website_url)
    
    # Verify test website is running
    expect(page).to_have_title(lambda title: 'Test' in title or 'Integration' in title)

# Embedded widget steps
@given('I have embedded the Universal Auth widget in my website')
def embedded_auth_widget(page: Page, test_website_url):
    """Verify embedded auth widget is present"""
    page.goto(test_website_url)
    
    # Check for embedded widget iframe or container
    widget_container = page.locator('[data-testid="universal-auth-widget"], .auth-widget, iframe[src*="universal-auth"]')
    expect(widget_container).to_be_visible()

@when('a user visits my website')
def user_visits_website(page: Page, test_website_url):
    """User visits the website"""
    page.goto(test_website_url)

@then('they should see the authentication widget')
def should_see_auth_widget(page: Page):
    """Verify authentication widget is visible"""
    auth_widget = page.locator('[data-testid="universal-auth-widget"], .auth-widget, .login-widget')
    expect(auth_widget).to_be_visible()

@when('they click "Login" in the widget')
def click_login_in_widget(page: Page):
    """Click login button in the widget"""
    login_button = page.locator('[data-testid="widget-login"], .widget-login, button:has-text("Login")')
    expect(login_button).to_be_visible()
    login_button.click()

@then('the authentication options should appear within the widget')
def auth_options_appear_in_widget(page: Page):
    """Verify authentication options appear within widget"""
    # Check for auth options within widget container
    widget_auth_options = page.locator('.auth-widget .auth-options, .widget-container .provider-buttons')
    expect(widget_auth_options).to_be_visible()
    
    # Verify multiple auth options are available
    auth_buttons = page.locator('.auth-widget button[data-provider], .widget-container .provider-button')
    expect(auth_buttons).to_have_count_greater_than(0)

@when('they complete authentication successfully')
def complete_authentication_successfully(page: Page):
    """Complete authentication process successfully"""
    # Click Google auth button (or first available option)
    google_button = page.locator('button:has-text("Google"), button[data-provider="google"]').first
    if google_button.is_visible():
        google_button.click()
        
        # Handle OAuth flow (mocked)
        page.wait_for_load_state('networkidle')
        
        # If redirected to OAuth page, simulate success
        if 'oauth' in page.url or 'google' in page.url:
            # Navigate back to simulate successful OAuth
            page.go_back()

@then('they should remain on my website')
def should_remain_on_website(page: Page, test_website_url):
    """Verify user remains on the original website"""
    current_url = page.url
    assert test_website_url in current_url, f"User should remain on {test_website_url}, but is on {current_url}"

@then('the widget should show their logged-in status')
def widget_shows_logged_in_status(page: Page):
    """Verify widget shows logged-in status"""
    logged_in_indicator = page.locator('[data-testid="widget-logged-in"], .widget-user-info, .logged-in-status')
    expect(logged_in_indicator).to_be_visible(timeout=10000)

# Redirect-based authentication steps
@given('my website is configured for redirect-based authentication')
def website_configured_for_redirect(page: Page, test_website_url):
    """Verify website is configured for redirect authentication"""
    page.goto(test_website_url)
    
    # Check for redirect configuration
    redirect_config = page.locator('[data-auth-mode="redirect"], .redirect-auth-config')
    expect(redirect_config).to_be_visible()

@when('a user clicks the "Login with Universal Auth" button on my website')
def click_login_with_universal_auth(page: Page):
    """Click the Universal Auth login button"""
    login_button = page.locator('[data-testid="universal-auth-login"], button:has-text("Login with Universal Auth")')
    expect(login_button).to_be_visible()
    login_button.click()

@then('they should be redirected to the Universal Auth login page')
def redirected_to_universal_auth_login(page: Page, base_url):
    """Verify redirection to Universal Auth login page"""
    page.wait_for_url(lambda url: base_url in url and 'login' in url, timeout=10000)
    
    # Verify we're on the Universal Auth login page
    expect(page.locator('h1:has-text("Login"), h2:has-text("Sign In")')).to_be_visible()

@when('they complete authentication successfully')
def complete_auth_successfully_redirect(page: Page):
    """Complete authentication in redirect flow"""
    # Click Google auth (or first available option)
    google_button = page.locator('button:has-text("Google"), button[data-provider="google"]').first
    expect(google_button).to_be_visible()
    google_button.click()
    
    # Simulate successful OAuth
    page.wait_for_load_state('networkidle')

@then('they should be redirected back to my website')
def redirected_back_to_website(page: Page, test_website_url):
    """Verify redirection back to original website"""
    page.wait_for_url(lambda url: test_website_url in url, timeout=15000)
    current_url = page.url
    assert test_website_url in current_url

@then('they should be logged in with a valid session token')
def logged_in_with_valid_session_token(page: Page):
    """Verify user is logged in with valid session"""
    # Check for session token in localStorage or cookies
    session_token = page.evaluate('localStorage.getItem("auth_token") || document.cookie.includes("session")')
    assert session_token, "Should have valid session token"
    
    # Check for logged-in UI elements
    logged_in_indicator = page.locator('[data-testid="logged-in"], .user-profile, .logout-button')
    expect(logged_in_indicator).to_be_visible()

# Popup-based authentication steps
@given('my website uses popup-based authentication')
def website_uses_popup_auth(page: Page, test_website_url):
    """Verify website uses popup authentication"""
    page.goto(test_website_url)
    
    # Check for popup configuration
    popup_config = page.locator('[data-auth-mode="popup"], .popup-auth-config')
    expect(popup_config).to_be_visible()

@when('a user clicks "Login" on my website')
def click_login_on_website(page: Page):
    """Click login button on website"""
    login_button = page.locator('[data-testid="login-button"], button:has-text("Login")')
    expect(login_button).to_be_visible()
    login_button.click()

@then('a popup window should open with the Universal Auth login page')
def popup_opens_with_universal_auth(page: Page, base_url):
    """Verify popup opens with Universal Auth login"""
    # Wait for popup to open
    with page.expect_popup() as popup_info:
        pass
    
    popup = popup_info.value
    popup.wait_for_load_state()
    
    # Verify popup contains Universal Auth login
    expect(popup.locator('h1:has-text("Login"), h2:has-text("Sign In")')).to_be_visible()

@when('they complete authentication in the popup')
def complete_auth_in_popup(page: Page):
    """Complete authentication in popup window"""
    # Get the popup window
    popup_pages = page.context.pages
    popup = popup_pages[-1] if len(popup_pages) > 1 else page
    
    # Complete authentication in popup
    google_button = popup.locator('button:has-text("Google"), button[data-provider="google"]').first
    if google_button.is_visible():
        google_button.click()
        popup.wait_for_load_state('networkidle')

@then('the popup should close automatically')
def popup_closes_automatically(page: Page):
    """Verify popup closes automatically"""
    # Wait for popup to close
    page.wait_for_timeout(2000)
    
    # Verify only main page remains
    assert len(page.context.pages) == 1, "Popup should have closed"

@then('the parent window should receive the authentication result')
def parent_window_receives_auth_result(page: Page):
    """Verify parent window receives authentication result"""
    # Check for authentication result in parent window
    auth_result = page.evaluate('window.authResult || localStorage.getItem("auth_result")')
    assert auth_result, "Parent window should receive authentication result"

@then('the user should be logged in on my website')
def user_logged_in_on_website(page: Page):
    """Verify user is logged in on the website"""
    logged_in_indicator = page.locator('[data-testid="logged-in"], .user-info, .logout-button')
    expect(logged_in_indicator).to_be_visible(timeout=10000)

# API-based authentication verification steps
@given('my website has received an authentication token')
def website_received_auth_token(page: Page):
    """Set up scenario with authentication token"""
    # Set mock authentication token
    page.evaluate('localStorage.setItem("auth_token", "mock_jwt_token_12345")')

@when('my backend makes a request to verify the token')
def backend_verifies_token(page: Page, api_url):
    """Backend verifies the authentication token"""
    # Simulate backend token verification
    auth_token = page.evaluate('localStorage.getItem("auth_token")')
    
    # Make API request to verify token
    response = page.request.post(f"{api_url}/api/auth/verify", data={
        'token': auth_token
    })
    
    # Store response for verification
    page.evaluate(f'window.tokenVerificationResponse = {response.json()}')

@then('the Universal Auth API should validate the token')
def universal_auth_validates_token(page: Page):
    """Verify Universal Auth API validates the token"""
    response = page.evaluate('window.tokenVerificationResponse')
    assert response is not None, "Should receive token verification response"
    assert response.get('valid') == True, "Token should be validated as valid"

@then('return the user\'s profile information')
def returns_user_profile_info(page: Page):
    """Verify user profile information is returned"""
    response = page.evaluate('window.tokenVerificationResponse')
    assert 'user' in response, "Response should contain user information"
    assert 'email' in response['user'] or 'id' in response['user'], "Should contain user profile data"

@then('confirm the user\'s roles and capabilities')
def confirms_user_roles_and_capabilities(page: Page):
    """Verify user roles and capabilities are confirmed"""
    response = page.evaluate('window.tokenVerificationResponse')
    user_data = response.get('user', {})
    assert 'roles' in user_data or 'capabilities' in user_data, "Should contain roles or capabilities"

# Multi-tenant integration steps
@given('I have multiple websites using Universal Auth')
def multiple_websites_using_universal_auth(page: Page):
    """Set up multiple websites scenario"""
    # Set up tenant configurations
    page.evaluate('''
        window.tenantConfigs = {
            "website_a": { tenant_id: "tenant_a", domain: "website-a.com" },
            "website_b": { tenant_id: "tenant_b", domain: "website-b.com" }
        }
    ''')

@given('each website has its own tenant configuration')
def each_website_has_tenant_config(page: Page):
    """Verify each website has tenant configuration"""
    tenant_configs = page.evaluate('window.tenantConfigs')
    assert len(tenant_configs) >= 2, "Should have multiple tenant configurations"

@when('a user authenticates on Website A')
def user_authenticates_on_website_a(page: Page, test_website_url):
    """User authenticates on Website A"""
    # Navigate to Website A
    page.goto(f"{test_website_url}?tenant=tenant_a")
    
    # Complete authentication
    login_button = page.locator('button:has-text("Login"), [data-testid="login-button"]')
    if login_button.is_visible():
        login_button.click()
        
        # Complete auth flow
        google_button = page.locator('button:has-text("Google")').first
        if google_button.is_visible():
            google_button.click()

@then('they should have access specific to Website A\'s tenant')
def access_specific_to_website_a_tenant(page: Page):
    """Verify access is specific to Website A's tenant"""
    # Check tenant context
    tenant_context = page.evaluate('localStorage.getItem("tenant_id")')
    assert tenant_context == "tenant_a", "Should have Website A's tenant context"

@when('they visit Website B')
def visit_website_b(page: Page, test_website_url):
    """User visits Website B"""
    page.goto(f"{test_website_url}?tenant=tenant_b")

@then('they should need to authenticate separately for Website B')
def need_separate_auth_for_website_b(page: Page):
    """Verify separate authentication is required for Website B"""
    # Should see login form again
    login_form = page.locator('[data-testid="login-form"], .login-container, button:has-text("Login")')
    expect(login_form).to_be_visible()

@then('their permissions should be isolated between tenants')
def permissions_isolated_between_tenants(page: Page):
    """Verify permissions are isolated between tenants"""
    # Check that tenant context has changed
    tenant_context = page.evaluate('localStorage.getItem("tenant_id")')
    assert tenant_context != "tenant_a", "Tenant context should be different"

# SSO integration steps
@given('multiple websites are configured for SSO with Universal Auth')
def multiple_websites_configured_for_sso(page: Page):
    """Set up SSO configuration"""
    page.evaluate('''
        window.ssoConfig = {
            enabled: true,
            domains: ["website-a.com", "website-b.com"],
            shared_session: true
        }
    ''')

@when('a user authenticates on Website A')
def user_authenticates_on_website_a_sso(page: Page, test_website_url):
    """User authenticates on Website A for SSO"""
    page.goto(f"{test_website_url}?sso=true&site=a")
    
    # Complete authentication
    login_button = page.locator('button:has-text("Login")').first
    if login_button.is_visible():
        login_button.click()

@when('they visit Website B that supports SSO')
def visit_website_b_with_sso(page: Page, test_website_url):
    """Visit Website B with SSO support"""
    page.goto(f"{test_website_url}?sso=true&site=b")

@then('they should be automatically logged in to Website B')
def automatically_logged_in_to_website_b(page: Page):
    """Verify automatic login to Website B"""
    # Should not see login form
    login_form = page.locator('button:has-text("Login")')
    expect(login_form).not_to_be_visible()
    
    # Should see logged-in status
    logged_in_indicator = page.locator('[data-testid="logged-in"], .user-info')
    expect(logged_in_indicator).to_be_visible()

@then('without needing to re-authenticate')
def without_re_authentication(page: Page):
    """Verify no re-authentication is needed"""
    # Verify no authentication prompts appeared
    auth_prompts = page.locator('.auth-form, .login-modal, .oauth-redirect')
    expect(auth_prompts).not_to_be_visible()

@then('their session should be synchronized across both sites')
def session_synchronized_across_sites(page: Page):
    """Verify session synchronization"""
    # Check for shared session indicators
    shared_session = page.evaluate('localStorage.getItem("shared_session") || sessionStorage.getItem("sso_session")')
    assert shared_session, "Should have shared session data"

# Logout integration steps
@given('a user is logged in across multiple integrated websites')
def user_logged_in_across_multiple_sites(page: Page, test_website_url):
    """Set up user logged in across multiple sites"""
    # Set up multi-site login state
    page.evaluate('''
        localStorage.setItem("auth_token", "shared_token_123");
        localStorage.setItem("logged_in_sites", JSON.stringify(["site_a", "site_b"]));
    ''')

@when('they click "Logout" on any website')
def click_logout_on_any_website(page: Page):
    """Click logout on any website"""
    logout_button = page.locator('[data-testid="logout-button"], button:has-text("Logout")')
    expect(logout_button).to_be_visible()
    logout_button.click()

@then('they should be logged out from all integrated websites')
def logged_out_from_all_integrated_websites(page: Page):
    """Verify logout from all integrated websites"""
    # Check that auth tokens are cleared
    auth_token = page.evaluate('localStorage.getItem("auth_token")')
    assert not auth_token, "Auth token should be cleared"
    
    logged_in_sites = page.evaluate('localStorage.getItem("logged_in_sites")')
    assert not logged_in_sites, "Logged in sites should be cleared"

@then('all session tokens should be invalidated')
def all_session_tokens_invalidated(page: Page):
    """Verify all session tokens are invalidated"""
    # Check for token invalidation
    session_data = page.evaluate('''
        Object.keys(localStorage).filter(key => key.includes('token') || key.includes('session'))
    ''')
    assert len(session_data) == 0, "All session data should be cleared"

@then('they should need to re-authenticate to access any website')
def need_re_auth_for_any_website(page: Page):
    """Verify re-authentication is required"""
    # Should see login form
    login_form = page.locator('button:has-text("Login"), .login-container')
    expect(login_form).to_be_visible()

# Error handling steps
@given('my website is integrated with Universal Auth')
def website_integrated_with_universal_auth(page: Page, test_website_url):
    """Verify website integration"""
    page.goto(test_website_url)
    
    # Check for integration indicators
    integration_config = page.locator('[data-universal-auth], .universal-auth-integration')
    expect(integration_config).to_be_visible()

@when('the Universal Auth service is temporarily unavailable')
def universal_auth_service_unavailable(page: Page):
    """Simulate Universal Auth service unavailability"""
    # Mock service unavailability
    page.route('**/api/auth/**', lambda route: route.abort())

@then('my website should show a graceful error message')
def website_shows_graceful_error(page: Page):
    """Verify graceful error message"""
    error_message = page.locator('[data-testid="auth-error"], .auth-service-error, .error-message')
    expect(error_message).to_be_visible(timeout=10000)

@then('provide alternative authentication options if available')
def provide_alternative_auth_options(page: Page):
    """Verify alternative authentication options"""
    alternative_auth = page.locator('[data-testid="alternative-auth"], .fallback-auth, .local-auth')
    expect(alternative_auth).to_be_visible()

@when('the service becomes available again')
def service_becomes_available_again(page: Page):
    """Simulate service becoming available"""
    # Remove the route mock
    page.unroute('**/api/auth/**')

@then('authentication should resume normally')
def authentication_resumes_normally(page: Page):
    """Verify authentication resumes normally"""
    # Try authentication again
    login_button = page.locator('button:has-text("Login")').first
    if login_button.is_visible():
        login_button.click()
        
        # Should not see error messages
        error_message = page.locator('.auth-service-error, .error-message')
        expect(error_message).not_to_be_visible()

# Mobile responsive steps
@when('a user accesses my website on a mobile device')
def user_accesses_on_mobile(page: Page, test_website_url):
    """Simulate mobile device access"""
    # Set mobile viewport
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(test_website_url)

@then('the authentication widget should be mobile-responsive')
def auth_widget_mobile_responsive(page: Page):
    """Verify authentication widget is mobile-responsive"""
    auth_widget = page.locator('[data-testid="universal-auth-widget"], .auth-widget')
    expect(auth_widget).to_be_visible()
    
    # Check widget fits mobile viewport
    widget_box = auth_widget.bounding_box()
    assert widget_box['width'] <= 375, "Widget should fit mobile viewport"

@then('the authentication flow should work smoothly on mobile')
def auth_flow_works_on_mobile(page: Page):
    """Verify authentication flow works on mobile"""
    # Test login button is accessible
    login_button = page.locator('button:has-text("Login")').first
    expect(login_button).to_be_visible()
    
    # Button should be touch-friendly (at least 44px)
    button_box = login_button.bounding_box()
    assert button_box['height'] >= 44, "Button should be touch-friendly"

@then('all authentication methods should be accessible on mobile devices')
def all_auth_methods_accessible_on_mobile(page: Page):
    """Verify all authentication methods are accessible on mobile"""
    # Check for multiple auth options
    auth_buttons = page.locator('button[data-provider], .provider-button')
    expect(auth_buttons).to_have_count_greater_than(0)
    
    # All buttons should be visible and accessible
    for i in range(auth_buttons.count()):
        button = auth_buttons.nth(i)
        expect(button).to_be_visible()
        button_box = button.bounding_box()
        assert button_box['height'] >= 44, f"Auth button {i} should be touch-friendly"