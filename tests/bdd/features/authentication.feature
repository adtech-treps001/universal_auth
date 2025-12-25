Feature: Universal Authentication System
  As a user of the Universal Auth System
  I want to authenticate using multiple methods
  So that I can access the system securely

  Background:
    Given the Universal Auth System is running
    And the authentication providers are configured

  @oauth @google
  Scenario: Successful Google OAuth Authentication
    Given I am on the login page
    When I click the "Sign in with Google" button
    Then I should be redirected to Google's OAuth page
    When I complete Google authentication successfully
    Then I should be redirected back to the application
    And I should be logged in as a Google user
    And my user profile should be created or updated

  @oauth @github
  Scenario: Successful GitHub OAuth Authentication
    Given I am on the login page
    When I click the "Sign in with GitHub" button
    Then I should be redirected to GitHub's OAuth page
    When I complete GitHub authentication successfully
    Then I should be redirected back to the application
    And I should be logged in as a GitHub user
    And my user profile should be created or updated

  @otp @mobile
  Scenario: Successful Mobile OTP Authentication
    Given I am on the login page
    When I select "Mobile OTP" authentication method
    And I enter a valid Indian mobile number "+919876543210"
    And I click "Send OTP"
    Then I should receive an OTP on my mobile number
    When I enter the correct OTP
    And I click "Verify OTP"
    Then I should be logged in successfully
    And my user profile should be created with mobile number

  @otp @mobile @error
  Scenario: Failed Mobile OTP Authentication - Invalid Number
    Given I am on the login page
    When I select "Mobile OTP" authentication method
    And I enter an invalid mobile number "123456"
    And I click "Send OTP"
    Then I should see an error message "Invalid Indian mobile number format"
    And no OTP should be sent

  @otp @mobile @error
  Scenario: Failed Mobile OTP Authentication - Wrong OTP
    Given I am on the login page
    When I select "Mobile OTP" authentication method
    And I enter a valid Indian mobile number "+919876543210"
    And I click "Send OTP"
    And I receive an OTP on my mobile number
    When I enter an incorrect OTP "000000"
    And I click "Verify OTP"
    Then I should see an error message "Invalid OTP"
    And I should remain on the OTP verification page

  @progressive_profiling
  Scenario: Progressive Profiling Flow
    Given I am a new user who just authenticated via Google
    When I complete my first login
    Then I should see a minimal profile form with required fields only
    When I fill in the required information and submit
    Then I should be taken to the main application
    When I log in for the third time
    Then I should see additional optional profile fields
    And I should be able to skip or fill them

  @multi_provider
  Scenario: Multiple Authentication Providers Available
    Given I am on the login page
    And multiple authentication providers are configured
    Then I should see buttons for "Google", "GitHub", "LinkedIn", "Apple"
    And I should see an option for "Mobile OTP"
    And all authentication options should be clearly visible

  @error_handling
  Scenario: OAuth Provider Error Handling
    Given I am on the login page
    When I click the "Sign in with Google" button
    And Google OAuth fails with an error
    Then I should be redirected back to the login page
    And I should see a user-friendly error message
    And I should be able to try authentication again