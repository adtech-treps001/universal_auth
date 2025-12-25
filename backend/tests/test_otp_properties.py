"""
Property-Based Tests for OTP Service

This module contains property-based tests that validate universal correctness
properties for the OTP authentication system using Hypothesis.

Feature: universal-auth, Properties 5, 6, 7: OTP functionality
"""

import pytest
import time
import re
from unittest.mock import AsyncMock, patch
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from auth.otp_service import OTPService, IndianMobileValidator, SMSGateway, OTPStatus


def create_test_otp_service():
    """Create OTP service with mock SMS gateway for property testing"""
    mock_gateway = SMSGateway(provider="mock")
    return OTPService(sms_gateway=mock_gateway)


class TestOTPProperties:
    """Property-based tests for OTP Service correctness"""
    
    # Strategy for generating valid Indian mobile numbers
    valid_indian_numbers = st.one_of(
        # 10-digit numbers starting with 6-9
        st.integers(min_value=6000000000, max_value=9999999999).map(str),
        # With +91 prefix
        st.integers(min_value=6000000000, max_value=9999999999).map(lambda x: f"+91{x}"),
        # With 91 prefix
        st.integers(min_value=6000000000, max_value=9999999999).map(lambda x: f"91{x}"),
        # With spaces (should be handled)
        st.integers(min_value=6000000000, max_value=9999999999).map(lambda x: f"+91 {str(x)[:3]} {str(x)[3:6]} {str(x)[6:]}"),
        # With hyphens (should be handled)
        st.integers(min_value=6000000000, max_value=9999999999).map(lambda x: f"91-{str(x)[:3]}-{str(x)[3:6]}-{str(x)[6:]}")
    )
    
    # Strategy for generating invalid phone numbers
    invalid_phone_numbers = st.one_of(
        st.text(min_size=0, max_size=5),  # Too short
        st.text(min_size=15, max_size=30),  # Too long
        st.integers(min_value=1000000000, max_value=5999999999).map(str),  # Starts with 1-5
        st.integers(min_value=1000000000, max_value=5999999999).map(lambda x: f"+91{x}"),  # Invalid with prefix
        st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=10, max_size=10),  # Letters only
        st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=10, max_size=15)  # Mixed
    )
    
    # Strategy for generating 6-digit OTP codes
    valid_otp_codes = st.integers(min_value=100000, max_value=999999).map(str)
    
    # Strategy for generating invalid OTP codes
    invalid_otp_codes = st.one_of(
        st.text(min_size=1, max_size=5),  # Too short
        st.text(min_size=7, max_size=10),  # Too long
        st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=6, max_size=6),  # Letters
        st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')), min_size=6, max_size=6)  # Mixed
    )
    
    @given(phone_number=st.text(min_size=1, max_size=20))
    @settings(max_examples=50, deadline=3000)
    def test_indian_mobile_number_validation_property(self, phone_number):
        """
        Property 5: Indian Mobile Number Validation
        
        For any phone number input, the system should accept only valid Indian 
        mobile numbers (10 digits with +91 prefix) and reject all other formats.
        
        **Feature: universal-auth, Property 5: Indian Mobile Number Validation**
        **Validates: Requirements 2.5**
        """
        result = IndianMobileValidator.validate(phone_number)
        
        # Check if the phone number matches valid Indian mobile pattern
        cleaned = re.sub(r'[\s\-]', '', phone_number)
        indian_pattern = re.compile(r'^(\+91|91)?[6-9]\d{9}$')
        expected_valid = bool(indian_pattern.match(cleaned))
        
        assert result == expected_valid, f"Validation mismatch for {phone_number}: got {result}, expected {expected_valid}"
        
        # If valid, normalization should work
        if result:
            try:
                normalized = IndianMobileValidator.normalize(phone_number)
                # Normalized number should always start with +91 and be 13 characters
                assert normalized.startswith('+91'), f"Normalized number should start with +91: {normalized}"
                assert len(normalized) == 13, f"Normalized number should be 13 characters: {normalized}"
                # Should contain only digits after +91
                assert normalized[3:].isdigit(), f"Normalized number should contain only digits after +91: {normalized}"
                # Should start with 6-9 after country code
                assert normalized[3] in '6789', f"Normalized number should start with 6-9 after +91: {normalized}"
            except ValueError:
                # If normalization fails, validation should have been False
                assert False, f"Normalization failed for number that passed validation: {phone_number}"
    
    @given(phone_number=valid_indian_numbers)
    @settings(max_examples=30, deadline=3000)
    def test_valid_indian_numbers_always_validate(self, phone_number):
        """
        Property: All generated valid Indian numbers should pass validation
        
        **Feature: universal-auth, Property 5: Indian Mobile Number Validation**
        **Validates: Requirements 2.5**
        """
        assert IndianMobileValidator.validate(phone_number), f"Generated valid number failed validation: {phone_number}"
        
        # Should also normalize successfully
        normalized = IndianMobileValidator.normalize(phone_number)
        assert normalized.startswith('+91')
        assert len(normalized) == 13
        assert normalized[3:].isdigit()
    
    @given(phone_number=valid_indian_numbers)
    @settings(max_examples=20, deadline=3000)
    def test_otp_generation_and_delivery_property(self, phone_number):
        """
        Property 6: OTP Generation and Delivery
        
        For any valid Indian mobile number, the OTP service should generate 
        a unique verification code and successfully deliver it within the 
        configured time limit.
        
        **Feature: universal-auth, Property 6: OTP Generation and Delivery**
        **Validates: Requirements 2.1**
        """
        service = create_test_otp_service()
        
        # Clear any existing sessions to avoid rate limiting
        service.sessions.clear()
        service.rate_limit_tracker.clear()
        
        # Send OTP should succeed for valid numbers
        import asyncio
        success, message = asyncio.run(service.send_otp(phone_number))
        
        assert success is True, f"OTP sending failed for valid number {phone_number}: {message}"
        assert "sent successfully" in message.lower()
        
        # Normalize the phone number to check session
        normalized = IndianMobileValidator.normalize(phone_number)
        
        # Session should be created
        assert normalized in service.sessions, f"No session created for {normalized}"
        
        session = service.sessions[normalized]
        
        # OTP should be 6 digits
        assert len(session.otp_code) == 6, f"OTP should be 6 digits: {session.otp_code}"
        assert session.otp_code.isdigit(), f"OTP should contain only digits: {session.otp_code}"
        
        # Session should have correct properties
        assert session.phone_number == normalized
        assert session.status == OTPStatus.PENDING
        assert session.attempts == 0
        assert session.expires_at > session.created_at
        assert session.expires_at <= session.created_at + 300  # 5 minutes max
    
    @given(
        phone_number=valid_indian_numbers,
        correct_otp=st.booleans()
    )
    @settings(max_examples=30, deadline=3000)
    def test_otp_verification_accuracy_property(self, phone_number, correct_otp):
        """
        Property 7: OTP Verification Accuracy
        
        For any OTP verification attempt, the system should authenticate users 
        only when the provided OTP matches the generated code and is within 
        the validity period.
        
        **Feature: universal-auth, Property 7: OTP Verification Accuracy**
        **Validates: Requirements 2.2**
        """
        service = create_test_otp_service()
        
        # Clear sessions and rate limiting
        service.sessions.clear()
        service.rate_limit_tracker.clear()
        
        # Send OTP first
        import asyncio
        success, _ = asyncio.run(service.send_otp(phone_number))
        assume(success)  # Skip if OTP sending fails
        
        normalized = IndianMobileValidator.normalize(phone_number)
        session = service.sessions[normalized]
        
        # Choose OTP code based on test parameter
        if correct_otp:
            test_otp = session.otp_code
        else:
            # Generate a different OTP
            test_otp = "123456" if session.otp_code != "123456" else "654321"
        
        # Verify OTP
        verify_success, verify_message = service.verify_otp(phone_number, test_otp)
        
        if correct_otp:
            # Correct OTP should succeed
            assert verify_success is True, f"Correct OTP verification failed: {verify_message}"
            assert "verified successfully" in verify_message.lower()
            assert session.status == OTPStatus.VERIFIED
        else:
            # Incorrect OTP should fail
            assert verify_success is False, f"Incorrect OTP verification should fail: {verify_message}"
            assert "invalid" in verify_message.lower()
            assert session.status == OTPStatus.PENDING
            assert session.attempts > 0
    
    @given(phone_number=valid_indian_numbers)
    @settings(max_examples=15, deadline=3000)
    def test_otp_expiration_property(self, phone_number):
        """
        Property: Expired OTPs should always be rejected
        
        For any OTP that has expired, verification should fail regardless 
        of whether the code is correct.
        
        **Feature: universal-auth, Property 7: OTP Verification Accuracy**
        **Validates: Requirements 2.2**
        """
        service = create_test_otp_service()
        
        # Create an expired session manually
        from auth.otp_service import OTPSession
        normalized = IndianMobileValidator.normalize(phone_number)
        past_time = time.time() - 400  # 400 seconds ago
        
        session = OTPSession(
            phone_number=normalized,
            otp_code="123456",
            created_at=past_time,
            expires_at=past_time + 300  # Expired 100 seconds ago
        )
        service.sessions[normalized] = session
        
        # Try to verify with correct OTP
        success, message = service.verify_otp(phone_number, "123456")
        
        assert success is False, "Expired OTP should not verify successfully"
        assert "expired" in message.lower()
        assert session.status == OTPStatus.EXPIRED
    
    @given(phone_number=valid_indian_numbers)
    @settings(max_examples=15, deadline=3000)
    def test_otp_max_attempts_property(self, phone_number):
        """
        Property: OTP verification should fail after maximum attempts
        
        For any OTP session, after reaching maximum attempts (3), 
        further verification attempts should fail.
        
        **Feature: universal-auth, Property 7: OTP Verification Accuracy**
        **Validates: Requirements 2.2**
        """
        service = create_test_otp_service()
        
        # Create a session at max attempts
        from auth.otp_service import OTPSession
        normalized = IndianMobileValidator.normalize(phone_number)
        
        session = OTPSession(
            phone_number=normalized,
            otp_code="123456",
            created_at=time.time(),
            attempts=3  # Already at max
        )
        service.sessions[normalized] = session
        
        # Try to verify (even with correct OTP)
        success, message = service.verify_otp(phone_number, "123456")
        
        assert success is False, "Verification should fail after max attempts"
        assert "maximum" in message.lower()
    
    @given(
        phone_number=valid_indian_numbers,
        wait_time=st.floats(min_value=0, max_value=120)  # 0 to 2 minutes
    )
    @settings(max_examples=20, deadline=3000)
    def test_otp_rate_limiting_property(self, phone_number, wait_time):
        """
        Property: OTP rate limiting should prevent spam
        
        For any phone number, sending OTP requests within the rate limit 
        window should be rejected.
        
        **Feature: universal-auth, Property 6: OTP Generation and Delivery**
        **Validates: Requirements 2.1**
        """
        service = create_test_otp_service()
        
        # Clear sessions and rate limiting
        service.sessions.clear()
        service.rate_limit_tracker.clear()
        
        # Send first OTP
        import asyncio
        success1, _ = asyncio.run(service.send_otp(phone_number))
        assume(success1)  # Skip if first OTP fails
        
        # Simulate waiting
        if wait_time >= service.rate_limit_window:
            # Should be able to send another OTP after rate limit window
            # Simulate time passage by updating the tracker
            normalized = IndianMobileValidator.normalize(phone_number)
            service.rate_limit_tracker[normalized] = time.time() - wait_time
            
            success2, message2 = asyncio.run(service.send_otp(phone_number))
            assert success2 is True, f"Should be able to send OTP after rate limit: {message2}"
        else:
            # Should be rate limited
            success2, message2 = asyncio.run(service.send_otp(phone_number))
            assert success2 is False, f"Should be rate limited: {message2}"
            assert "wait" in message2.lower()
    
    @given(phone_number=invalid_phone_numbers)
    @settings(max_examples=30, deadline=3000)
    def test_invalid_phone_numbers_rejected(self, phone_number):
        """
        Property: Invalid phone numbers should always be rejected
        
        For any invalid phone number format, OTP operations should fail.
        
        **Feature: universal-auth, Property 5: Indian Mobile Number Validation**
        **Validates: Requirements 2.5**
        """
        # Skip numbers that might accidentally be valid
        assume(not IndianMobileValidator.validate(phone_number))
        
        service = create_test_otp_service()
        
        # OTP sending should fail
        import asyncio
        success, message = asyncio.run(service.send_otp(phone_number))
        
        assert success is False, f"Invalid number should be rejected: {phone_number}"
        assert "invalid" in message.lower()
        
        # OTP verification should also fail
        verify_success, verify_message = service.verify_otp(phone_number, "123456")
        assert verify_success is False, f"Invalid number verification should fail: {phone_number}"
        assert "invalid" in verify_message.lower()
    
    @given(
        phone_number=valid_indian_numbers,
        otp_code=invalid_otp_codes
    )
    @settings(max_examples=20, deadline=3000)
    def test_invalid_otp_codes_rejected(self, phone_number, otp_code):
        """
        Property: Invalid OTP codes should be rejected
        
        For any invalid OTP code format, verification should fail.
        
        **Feature: universal-auth, Property 7: OTP Verification Accuracy**
        **Validates: Requirements 2.2**
        """
        # Skip OTP codes that might accidentally be valid 6-digit numbers
        assume(not (otp_code.isdigit() and len(otp_code) == 6))
        
        service = create_test_otp_service()
        
        # Create a valid session first
        from auth.otp_service import OTPSession
        normalized = IndianMobileValidator.normalize(phone_number)
        session = OTPSession(
            phone_number=normalized,
            otp_code="123456",
            created_at=time.time()
        )
        service.sessions[normalized] = session
        
        # Try to verify with invalid OTP format
        success, message = service.verify_otp(phone_number, otp_code)
        
        # Should fail due to invalid format (handled by schema validation in API)
        # or due to incorrect code if it reaches the service
        assert success is False, f"Invalid OTP code should be rejected: {otp_code}"