Feature: External Website Integration
  As a website owner
  I want to integrate Universal Auth into my existing website
  So that users can authenticate seamlessly

  Background:
    Given the Universal Auth System is running
    And I have a test website with Universal Auth integration

  @integration @iframe
  Scenario: Embedded Authentication Widget
    Given I have embedded the Universal Auth widget in my website
    When a user visits my website
    Then they should see the authentication widget
    When they click "Login" in the widget
    Then the authentication options should appear within the widget
    When they complete authentication successfully
    Then they should remain on my website
    And the widget should show their logged-in status

  @integration @redirect
  Scenario: Redirect-based Authentication
    Given my website is configured for redirect-based authentication
    When a user clicks the "Login with Universal Auth" button on my website
    Then they should be redirected to the Universal Auth login page
    When they complete authentication successfully
    Then they should be redirected back to my website
    And they should be logged in with a valid session token

  @integration @popup
  Scenario: Popup-based Authentication
    Given my website uses popup-based authentication
    When a user clicks "Login" on my website
    Then a popup window should open with the Universal Auth login page
    When they complete authentication in the popup
    Then the popup should close automatically
    And the parent window should receive the authentication result
    And the user should be logged in on my website

  @integration @api
  Scenario: API-based Authentication Verification
    Given my website has received an authentication token
    When my backend makes a request to verify the token
    Then the Universal Auth API should validate the token
    And return the user's profile information
    And confirm the user's roles and capabilities

  @integration @multi_tenant
  Scenario: Multi-tenant Website Integration
    Given I have multiple websites using Universal Auth
    And each website has its own tenant configuration
    When a user authenticates on Website A
    Then they should have access specific to Website A's tenant
    When they visit Website B
    Then they should need to authenticate separately for Website B
    And their permissions should be isolated between tenants

  @integration @sso
  Scenario: Single Sign-On Between Integrated Websites
    Given multiple websites are configured for SSO with Universal Auth
    When a user authenticates on Website A
    And they visit Website B that supports SSO
    Then they should be automatically logged in to Website B
    Without needing to re-authenticate
    And their session should be synchronized across both sites

  @integration @logout
  Scenario: Logout Across Integrated Websites
    Given a user is logged in across multiple integrated websites
    When they click "Logout" on any website
    Then they should be logged out from all integrated websites
    And all session tokens should be invalidated
    And they should need to re-authenticate to access any website

  @integration @error_handling
  Scenario: Integration Error Handling
    Given my website is integrated with Universal Auth
    When the Universal Auth service is temporarily unavailable
    Then my website should show a graceful error message
    And provide alternative authentication options if available
    When the service becomes available again
    Then authentication should resume normally

  @integration @mobile_responsive
  Scenario: Mobile-Responsive Integration
    Given my website has Universal Auth integration
    When a user accesses my website on a mobile device
    Then the authentication widget should be mobile-responsive
    And the authentication flow should work smoothly on mobile
    And all authentication methods should be accessible on mobile devices