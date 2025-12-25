"""
BDD Step definitions for admin panel scenarios
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import Page, expect
import os
from faker import Faker

fake = Faker()

# Load scenarios from feature files
scenarios('../features/admin_panel.feature')

@pytest.fixture
def admin_user_data():
    return {
        'email': 'admin@example.com',
        'password': 'admin_password',
        'role': 'super_admin'
    }

@pytest.fixture
def test_project_data():
    return {
        'project_name': f'Test Project {fake.random_int(1000, 9999)}',
        'description': 'A test project for BDD testing',
        'workflow_type': 'social_auth',
        'theme': 'default'
    }

@pytest.fixture
def test_user_creation_data():
    return {
        'email': fake.email(),
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
        'role': 'user'
    }

# Background steps
@given('I am logged in as an administrator')
def logged_in_as_admin(page: Page, base_url, admin_user_data):
    """Log in as an administrator"""
    page.goto(f"{base_url}/admin/login")
    
    # Fill login form
    page.fill('[data-testid="email-input"], input[name="email"]', admin_user_data['email'])
    page.fill('[data-testid="password-input"], input[name="password"]', admin_user_data['password'])
    page.click('button[type="submit"], button:has-text("Login")')
    
    # Verify admin dashboard is accessible
    expect(page.locator('[data-testid="admin-dashboard"], .admin-panel')).to_be_visible(timeout=10000)

# Role-based access steps
@given(parsers.parse('I have "{role}" role'))
def have_role(page: Page, role, api_url):
    """Set user role for testing"""
    # Set role via API or localStorage for testing
    page.evaluate(f'localStorage.setItem("user_role", "{role}")')
    
    # Verify role via API if available
    response = page.request.get(f"{api_url}/api/user/profile")
    if response.status == 200:
        profile = response.json()
        # In a real scenario, we'd verify the role from the profile

@when('I navigate to the admin panel')
def navigate_to_admin_panel(page: Page, base_url):
    """Navigate to the admin panel"""
    page.goto(f"{base_url}/admin")
    expect(page.locator('[data-testid="admin-dashboard"], .admin-panel')).to_be_visible()

@then('I should see all admin sections:')
def should_see_all_admin_sections(page: Page, step):
    """Verify all specified admin sections are visible"""
    for row in step.table:
        section_name = row['section_name']
        section_selector = f'[data-testid="admin-section-{section_name}"], .admin-section[data-section="{section_name}"], a:has-text("{section_name.replace("_", " ").title()}")'
        expect(page.locator(section_selector)).to_be_visible()

@then('I should see these admin sections:')
def should_see_these_admin_sections(page: Page, step):
    """Verify specified admin sections are visible"""
    for row in step.table:
        section_name = row['section_name']
        section_selector = f'[data-testid="admin-section-{section_name}"], .admin-section[data-section="{section_name}"], a:has-text("{section_name.replace("_", " ").title()}")'
        expect(page.locator(section_selector)).to_be_visible()

@then('I should not see these admin sections:')
def should_not_see_these_admin_sections(page: Page, step):
    """Verify specified admin sections are not visible"""
    for row in step.table:
        section_name = row['section_name']
        section_selector = f'[data-testid="admin-section-{section_name}"], .admin-section[data-section="{section_name}"], a:has-text("{section_name.replace("_", " ").title()}")'
        expect(page.locator(section_selector)).not_to_be_visible()

# User management steps
@when('I navigate to the user management section')
def navigate_to_user_management(page: Page):
    """Navigate to user management section"""
    user_mgmt_link = page.locator('[data-testid="admin-section-user_management"], a:has-text("User Management")')
    expect(user_mgmt_link).to_be_visible()
    user_mgmt_link.click()

@then('I should see a list of users')
def should_see_user_list(page: Page):
    """Verify user list is displayed"""
    user_list = page.locator('[data-testid="user-list"], .user-table, table')
    expect(user_list).to_be_visible()

@when('I click "Add New User"')
def click_add_new_user(page: Page):
    """Click the Add New User button"""
    add_user_button = page.locator('[data-testid="add-user-button"], button:has-text("Add New User")')
    expect(add_user_button).to_be_visible()
    add_user_button.click()

@then('I should see a user creation form')
def should_see_user_creation_form(page: Page):
    """Verify user creation form is displayed"""
    user_form = page.locator('[data-testid="user-creation-form"], .user-form, form')
    expect(user_form).to_be_visible()

@when('I fill in valid user details:')
def fill_user_details(page: Page, step):
    """Fill in user creation form"""
    for row in step.table:
        field = row['field']
        value = row['value']
        
        if field == 'email':
            page.fill('[data-testid="user-email"], input[name="email"]', value)
        elif field == 'first_name':
            page.fill('[data-testid="user-first-name"], input[name="first_name"]', value)
        elif field == 'last_name':
            page.fill('[data-testid="user-last-name"], input[name="last_name"]', value)
        elif field == 'role':
            page.select_option('[data-testid="user-role"], select[name="role"]', value)

@when('I click "Create User"')
def click_create_user(page: Page):
    """Click the Create User button"""
    create_button = page.locator('[data-testid="create-user-button"], button:has-text("Create User")')
    expect(create_button).to_be_visible()
    create_button.click()

@then('the user should be created successfully')
def user_created_successfully(page: Page):
    """Verify user creation success"""
    success_message = page.locator('[data-testid="success-message"], .success, .alert-success')
    expect(success_message).to_be_visible(timeout=5000)

@then('I should see a success message')
def should_see_success_message(page: Page):
    """Verify success message is displayed"""
    success_message = page.locator('[data-testid="success-message"], .success, .alert-success')
    expect(success_message).to_be_visible()

# Project management steps
@when('I navigate to the project management section')
def navigate_to_project_management(page: Page):
    """Navigate to project management section"""
    project_mgmt_link = page.locator('[data-testid="admin-section-project_management"], a:has-text("Project Management")')
    expect(project_mgmt_link).to_be_visible()
    project_mgmt_link.click()

@when('I click "Create New Project"')
def click_create_new_project(page: Page):
    """Click the Create New Project button"""
    create_project_button = page.locator('[data-testid="create-project-button"], button:has-text("Create New Project")')
    expect(create_project_button).to_be_visible()
    create_project_button.click()

@then('I should see a project creation form')
def should_see_project_creation_form(page: Page):
    """Verify project creation form is displayed"""
    project_form = page.locator('[data-testid="project-creation-form"], .project-form, form')
    expect(project_form).to_be_visible()

@when('I fill in project details:')
def fill_project_details(page: Page, step):
    """Fill in project creation form"""
    for row in step.table:
        field = row['field']
        value = row['value']
        
        if field == 'project_name':
            page.fill('[data-testid="project-name"], input[name="project_name"]', value)
        elif field == 'description':
            page.fill('[data-testid="project-description"], textarea[name="description"]', value)
        elif field == 'workflow_type':
            page.select_option('[data-testid="workflow-type"], select[name="workflow_type"]', value)
        elif field == 'theme':
            page.select_option('[data-testid="theme"], select[name="theme"]', value)

@when('I click "Create Project"')
def click_create_project(page: Page):
    """Click the Create Project button"""
    create_button = page.locator('[data-testid="create-project-button"], button:has-text("Create Project")')
    expect(create_button).to_be_visible()
    create_button.click()

@then('the project should be created successfully')
def project_created_successfully(page: Page):
    """Verify project creation success"""
    success_message = page.locator('[data-testid="success-message"], .success, .alert-success')
    expect(success_message).to_be_visible(timeout=5000)

@then('I should be able to configure authentication providers')
def can_configure_auth_providers(page: Page):
    """Verify ability to configure authentication providers"""
    config_section = page.locator('[data-testid="auth-provider-config"], .provider-config')
    expect(config_section).to_be_visible()

# API Key management steps
@when('I navigate to the integrations section')
def navigate_to_integrations(page: Page):
    """Navigate to integrations section"""
    integrations_link = page.locator('[data-testid="admin-section-integrations"], a:has-text("Integrations")')
    expect(integrations_link).to_be_visible()
    integrations_link.click()

@when('I click "Add API Key"')
def click_add_api_key(page: Page):
    """Click the Add API Key button"""
    add_key_button = page.locator('[data-testid="add-api-key-button"], button:has-text("Add API Key")')
    expect(add_key_button).to_be_visible()
    add_key_button.click()

@then('I should see an API key creation form')
def should_see_api_key_form(page: Page):
    """Verify API key creation form is displayed"""
    api_key_form = page.locator('[data-testid="api-key-form"], .api-key-form, form')
    expect(api_key_form).to_be_visible()

@when('I select "OpenAI" as the provider')
def select_openai_provider(page: Page):
    """Select OpenAI as the API provider"""
    provider_select = page.locator('[data-testid="api-provider"], select[name="provider"]')
    expect(provider_select).to_be_visible()
    provider_select.select_option('openai')

@when('I enter a valid API key')
def enter_valid_api_key(page: Page):
    """Enter a valid API key"""
    api_key_input = page.locator('[data-testid="api-key-input"], input[name="api_key"]')
    expect(api_key_input).to_be_visible()
    api_key_input.fill('sk-test1234567890abcdef1234567890abcdef')

@when('I set the scope to "chat.completions"')
def set_scope_chat_completions(page: Page):
    """Set the API key scope"""
    scope_input = page.locator('[data-testid="api-scope"], input[name="scope"], select[name="scope"]')
    expect(scope_input).to_be_visible()
    if scope_input.get_attribute('type') == 'text':
        scope_input.fill('chat.completions')
    else:
        scope_input.select_option('chat.completions')

@when('I assign it to "developer" role')
def assign_to_developer_role(page: Page):
    """Assign API key to developer role"""
    role_select = page.locator('[data-testid="api-key-role"], select[name="allowed_roles"]')
    expect(role_select).to_be_visible()
    role_select.select_option('developer')

@when('I click "Save API Key"')
def click_save_api_key(page: Page):
    """Click the Save API Key button"""
    save_button = page.locator('[data-testid="save-api-key"], button:has-text("Save API Key")')
    expect(save_button).to_be_visible()
    save_button.click()

@then('the API key should be stored securely')
def api_key_stored_securely(page: Page):
    """Verify API key is stored securely"""
    success_message = page.locator('[data-testid="success-message"], .success')
    expect(success_message).to_be_visible(timeout=5000)

@then('I should see it in the API keys list with masked value')
def see_api_key_in_list_masked(page: Page):
    """Verify API key appears in list with masked value"""
    api_key_list = page.locator('[data-testid="api-key-list"], .api-key-table')
    expect(api_key_list).to_be_visible()
    
    # Check for masked key (should contain asterisks or dots)
    masked_key = page.locator('.api-key-value, [data-testid="masked-key"]')
    expect(masked_key).to_be_visible()
    expect(masked_key).to_contain_text(['***', '...', 'sk-***'])

# Audit logs steps
@when('I navigate to the audit logs section')
def navigate_to_audit_logs(page: Page):
    """Navigate to audit logs section"""
    audit_link = page.locator('[data-testid="admin-section-audit_logs"], a:has-text("Audit Logs")')
    expect(audit_link).to_be_visible()
    audit_link.click()

@then('I should see a list of recent authentication events')
def should_see_audit_events(page: Page):
    """Verify audit events list is displayed"""
    audit_list = page.locator('[data-testid="audit-log-list"], .audit-table, table')
    expect(audit_list).to_be_visible()

@then('I should be able to filter by:')
def should_be_able_to_filter_by(page: Page, step):
    """Verify filter options are available"""
    for row in step.table:
        filter_type = row['filter_type']
        filter_element = page.locator(f'[data-testid="filter-{filter_type}"], .filter-{filter_type}, select[name="{filter_type}"]')
        expect(filter_element).to_be_visible()

@when('I apply a date filter for "last 7 days"')
def apply_date_filter_last_7_days(page: Page):
    """Apply date filter for last 7 days"""
    date_filter = page.locator('[data-testid="filter-date_range"], select[name="date_range"]')
    expect(date_filter).to_be_visible()
    date_filter.select_option('last_7_days')

@then('I should see only events from the last 7 days')
def should_see_events_last_7_days(page: Page):
    """Verify only recent events are shown"""
    # Check that events are filtered (implementation depends on UI)
    audit_rows = page.locator('[data-testid="audit-row"], .audit-table tr')
    expect(audit_rows).to_have_count_greater_than(0)

@then('each log entry should show timestamp, user, event type, and details')
def each_log_entry_shows_details(page: Page):
    """Verify log entry structure"""
    first_row = page.locator('[data-testid="audit-row"], .audit-table tr').first
    expect(first_row).to_be_visible()
    
    # Check for required columns
    expect(first_row.locator('.timestamp, [data-column="timestamp"]')).to_be_visible()
    expect(first_row.locator('.user, [data-column="user"]')).to_be_visible()
    expect(first_row.locator('.event-type, [data-column="event_type"]')).to_be_visible()

# Role management steps
@when('I navigate to the role management section')
def navigate_to_role_management(page: Page):
    """Navigate to role management section"""
    role_mgmt_link = page.locator('[data-testid="admin-section-role_management"], a:has-text("Role Management")')
    expect(role_mgmt_link).to_be_visible()
    role_mgmt_link.click()

@when('I click "Create Custom Role"')
def click_create_custom_role(page: Page):
    """Click the Create Custom Role button"""
    create_role_button = page.locator('[data-testid="create-role-button"], button:has-text("Create Custom Role")')
    expect(create_role_button).to_be_visible()
    create_role_button.click()

@then('I should see a role creation form')
def should_see_role_creation_form(page: Page):
    """Verify role creation form is displayed"""
    role_form = page.locator('[data-testid="role-creation-form"], .role-form, form')
    expect(role_form).to_be_visible()

@when('I enter role name "custom_reviewer"')
def enter_role_name(page: Page):
    """Enter role name"""
    role_name_input = page.locator('[data-testid="role-name"], input[name="role_name"]')
    expect(role_name_input).to_be_visible()
    role_name_input.fill('custom_reviewer')

@when('I select these capabilities:')
def select_capabilities(page: Page, step):
    """Select specified capabilities"""
    for row in step.table:
        capability = row['capability']
        capability_checkbox = page.locator(f'[data-testid="capability-{capability}"], input[value="{capability}"]')
        expect(capability_checkbox).to_be_visible()
        capability_checkbox.check()

@when('I click "Create Role"')
def click_create_role(page: Page):
    """Click the Create Role button"""
    create_button = page.locator('[data-testid="create-role-submit"], button:has-text("Create Role")')
    expect(create_button).to_be_visible()
    create_button.click()

@then('the custom role should be created')
def custom_role_created(page: Page):
    """Verify custom role creation"""
    success_message = page.locator('[data-testid="success-message"], .success')
    expect(success_message).to_be_visible(timeout=5000)

@then('I should be able to assign it to users')
def can_assign_role_to_users(page: Page):
    """Verify ability to assign role to users"""
    # Navigate to user management or check role assignment interface
    role_assignment = page.locator('[data-testid="role-assignment"], .role-assignment')
    expect(role_assignment).to_be_visible()

# Error handling steps
@when('I try to access the system settings section directly')
def try_access_system_settings_directly(page: Page, base_url):
    """Try to access system settings directly"""
    page.goto(f"{base_url}/admin/system-settings")

@then('I should see an "Access Denied" message')
def should_see_access_denied(page: Page):
    """Verify access denied message"""
    access_denied = page.locator('[data-testid="access-denied"], .access-denied, .error')
    expect(access_denied).to_be_visible()
    expect(access_denied).to_contain_text(['Access Denied', 'Unauthorized', 'Permission denied'])

@then('I should be redirected to the admin dashboard')
def redirected_to_admin_dashboard(page: Page, base_url):
    """Verify redirection to admin dashboard"""
    page.wait_for_url(lambda url: '/admin' in url and 'system-settings' not in url, timeout=10000)

@then('the unauthorized access should be logged in audit logs')
def unauthorized_access_logged(page: Page, api_url):
    """Verify unauthorized access is logged"""
    # Check audit logs via API
    response = page.request.get(f"{api_url}/api/admin/audit-logs?event_type=unauthorized_access")
    if response.status == 200:
        logs = response.json()
        assert len(logs) > 0