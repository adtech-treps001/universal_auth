Feature: Admin Panel Access Control
  As an administrator
  I want to manage system configurations and users
  So that I can maintain the Universal Auth System

  Background:
    Given the Universal Auth System is running
    And I am logged in as an administrator

  @admin @access_control
  Scenario: Super Admin Access to All Sections
    Given I have "super_admin" role
    When I navigate to the admin panel
    Then I should see all admin sections:
      | section_name        |
      | project_management  |
      | user_management     |
      | role_management     |
      | configuration       |
      | audit_logs          |
      | integrations        |
      | system_settings     |

  @admin @access_control
  Scenario: Project Admin Limited Access
    Given I have "project_admin" role
    When I navigate to the admin panel
    Then I should see these admin sections:
      | section_name        |
      | project_management  |
      | user_management     |
      | configuration       |
    And I should not see these admin sections:
      | section_name        |
      | role_management     |
      | audit_logs          |
      | system_settings     |

  @admin @user_management
  Scenario: User Management Operations
    Given I have "user_admin" role
    When I navigate to the user management section
    Then I should see a list of users
    When I click "Add New User"
    Then I should see a user creation form
    When I fill in valid user details:
      | field       | value                |
      | email       | newuser@example.com  |
      | first_name  | John                 |
      | last_name   | Doe                  |
      | role        | user                 |
    And I click "Create User"
    Then the user should be created successfully
    And I should see a success message

  @admin @project_management
  Scenario: Project Configuration Management
    Given I have "project_admin" role
    When I navigate to the project management section
    And I click "Create New Project"
    Then I should see a project creation form
    When I fill in project details:
      | field           | value                    |
      | project_name    | Test Project             |
      | description     | A test project           |
      | workflow_type   | social_auth              |
      | theme           | default                  |
    And I click "Create Project"
    Then the project should be created successfully
    And I should be able to configure authentication providers

  @admin @api_keys
  Scenario: API Key Management
    Given I have "config_admin" role
    When I navigate to the integrations section
    And I click "Add API Key"
    Then I should see an API key creation form
    When I select "OpenAI" as the provider
    And I enter a valid API key
    And I set the scope to "chat.completions"
    And I assign it to "developer" role
    And I click "Save API Key"
    Then the API key should be stored securely
    And I should see it in the API keys list with masked value

  @admin @audit_logs
  Scenario: Audit Log Viewing
    Given I have "super_admin" role
    When I navigate to the audit logs section
    Then I should see a list of recent authentication events
    And I should be able to filter by:
      | filter_type  |
      | date_range   |
      | user_id      |
      | event_type   |
      | tenant_id    |
    When I apply a date filter for "last 7 days"
    Then I should see only events from the last 7 days
    And each log entry should show timestamp, user, event type, and details

  @admin @role_management
  Scenario: Custom Role Creation
    Given I have "super_admin" role
    When I navigate to the role management section
    And I click "Create Custom Role"
    Then I should see a role creation form
    When I enter role name "custom_reviewer"
    And I select these capabilities:
      | capability           |
      | admin.users.read     |
      | admin.audit.read     |
      | admin.projects.read  |
    And I click "Create Role"
    Then the custom role should be created
    And I should be able to assign it to users

  @admin @error_handling
  Scenario: Unauthorized Access Attempt
    Given I have "user_admin" role
    When I try to access the system settings section directly
    Then I should see an "Access Denied" message
    And I should be redirected to the admin dashboard
    And the unauthorized access should be logged in audit logs