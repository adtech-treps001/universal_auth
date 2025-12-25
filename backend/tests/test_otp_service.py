"""
Tests for OTP Service

This module contains unit tests for the OTP authentication service,
testing Indian mobile number validation, OTP generation, and verification.
"""

import pytest
import time
from unittest.mock import AsyncMock, patch
from auth.otp_service import OTPService, IndianMobileValidator, SMSGateway, OTPStatus


class TestIndianMobileValidator:
    """Test cases for Indian mobile number validation"""
    
    def test_valid_indian_mobile_numbers(self):
        """Test validation of valid Indian mobile numbers"""
        valid_numbers = [
            "+916123456789",
            "916123456789", 
            "6123456789",
            "+917123456789",
            "917123456789",
            "7123456789",
            "+918123456789",
            "918123456789",
            "8123456789",
            "+919123456789",
            "919123456789",
            "9123456789"
        ]
        
        for number in valid_numbers:
            assert IndianMobileValidator.validate(number), f"Should be valid: {number}"
    
    def test_invalid_indian_mobile_numbers(self):
        """Test validation of invalid Indian mobile numbers"""
        invalid_numbers = [
            "",
            "123456789",  # Too short
            "12345678901",  # Too long
            "+915123456789",  # Starts with 5 (invalid)
            "915123456789",
            "5123456789",
            "+911123456789",  # Starts with 1 (invalid)
            "abc123456789",  # Contains letters
            "+91 612 345 6789",  # With spaces (should be handled)
            "91-612-345-6789"  # With hyphens (should be handled)
        ]
        
        for number in invalid_numbers:
            if number in ["+91 612 345 6789", "91-612-345-6789"]:
                # These should actually be valid after cleaning
                assert IndianMobileValidator.validate(number), f"Should be valid after cleaning: {number}"
            else:
                assert not IndianMobileValidator.validate(number), f"Should be invalid: {number}"
    
    def test_normalize_indian_mobile_numbers(self):
        """Test normalization of Indian mobile numbers"""
        test_cases = [
            ("+916123456789", "+916123456789"),
            ("916123456789", "+916123456789"),
            ("6123456789", "+916123456789"),
            ("+91 612 345 6789", "+916123456789"),
            ("91-612-345-6789", "+916123456789")
        ]
        
        for input_number, expected in test_cases:
            result = IndianMobileValidator.normalize(input_number)
            assert result == expected, f"Expected {expected}, got {result} for {input_number}"
    
    def test_normalize_invalid_numbers(self):
        """Test normalization of invalid numbers raises ValueError"""
        invalid_numbers = ["123456789", "abc123456789", "5123456789"]
        
        for number in invalid_numbers:
            with pytest.raises(ValueError):
                IndianMobileValidator.normalize(number)


class TestSMSGateway:
    """Test cases for SMS Gateway"""
    
    @pytest.mark.asyncio
    async def test_mock_sms_gateway(self):
        """Test mock SMS gateway"""
        gateway = SMSGateway(provider="mock")
        result = await gateway.send_sms("+916123456789", "Test message")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_unimplemented_provider(self):
        """Test that unimplemented providers raise NotImplementedError"""
        gateway = SMSGateway(provider="unsupported")
        
        with pytest.raises(NotImplementedError):
            await gateway.send_sms("+916123456789", "Test message")


class TestOTPService:
    """Test cases for OTP Service"""
    
    @pytest.fixture
    def otp_service(self):
        """Create OTP service with mock SMS gateway"""
        mock_gateway = SMSGateway(provider="mock")
        return OTPService(sms_gateway=mock_gateway)
    
    @pytest.mark.asyncio
    async def test_send_otp_valid_number(self, otp_service):
        """Test sending OTP to valid Indian mobile number"""
        success, message = await otp_service.send_otp("+916123456789")
        
        assert success is True
        assert "sent successfully" in message.lower()
        assert "+916123456789" in otp_service.sessions
    
    @pytest.mark.asyncio
    async def test_send_otp_invalid_number(self, otp_service):
        """Test sending OTP to invalid mobile number"""
        success, message = await otp_service.send_otp("123456789")
        
        assert success is False
        assert "invalid" in message.lower()
    
    @pytest.mark.asyncio
    async def test_send_otp_rate_limiting(self, otp_service):
        """Test OTP rate limiting"""
        phone = "+916123456789"
        
        # First request should succeed
        success1, _ = await otp_service.send_otp(phone)
        assert success1 is True
        
        # Second request immediately should be rate limited
        success2, message2 = await otp_service.send_otp(phone)
        assert success2 is False
        assert "wait" in message2.lower()
    
    @pytest.mark.asyncio
    async def test_verify_otp_success(self, otp_service):
        """Test successful OTP verification"""
        phone = "+916123456789"
        
        # Send OTP first
        await otp_service.send_otp(phone)
        session = otp_service.sessions[phone]
        
        # Verify with correct OTP
        success, message = otp_service.verify_otp(phone, session.otp_code)
        
        assert success is True
        assert "verified successfully" in message.lower()
        assert session.status == OTPStatus.VERIFIED
    
    def test_verify_otp_invalid_code(self, otp_service):
        """Test OTP verification with invalid code"""
        phone = "+916123456789"
        
        # Create a session manually for testing
        from auth.otp_service import OTPSession
        session = OTPSession(
            phone_number=phone,
            otp_code="123456",
            created_at=time.time()
        )
        otp_service.sessions[phone] = session
        
        # Verify with wrong OTP
        success, message = otp_service.verify_otp(phone, "654321")
        
        assert success is False
        assert "invalid" in message.lower()
        assert session.attempts == 1
    
    def test_verify_otp_expired(self, otp_service):
        """Test OTP verification with expired code"""
        phone = "+916123456789"
        
        # Create an expired session
        from auth.otp_service import OTPSession
        past_time = time.time() - 400  # 400 seconds ago
        session = OTPSession(
            phone_number=phone,
            otp_code="123456",
            created_at=past_time,
            expires_at=past_time + 300  # Expired 100 seconds ago
        )
        otp_service.sessions[phone] = session
        
        # Try to verify expired OTP
        success, message = otp_service.verify_otp(phone, "123456")
        
        assert success is False
        assert "expired" in message.lower()
        assert session.status == OTPStatus.EXPIRED
    
    def test_verify_otp_max_attempts(self, otp_service):
        """Test OTP verification with maximum attempts exceeded"""
        phone = "+916123456789"
        
        # Create a session with max attempts
        from auth.otp_service import OTPSession
        session = OTPSession(
            phone_number=phone,
            otp_code="123456",
            created_at=time.time(),
            attempts=3  # Already at max attempts
        )
        otp_service.sessions[phone] = session
        
        # Try to verify
        success, message = otp_service.verify_otp(phone, "654321")
        
        assert success is False
        assert "maximum" in message.lower()
    
    def test_verify_otp_no_session(self, otp_service):
        """Test OTP verification without existing session"""
        success, message = otp_service.verify_otp("+916123456789", "123456")
        
        assert success is False
        assert "no otp session" in message.lower()
    
    def test_get_session_status(self, otp_service):
        """Test getting OTP session status"""
        phone = "+916123456789"
        
        # No session initially
        session = otp_service.get_session_status(phone)
        assert session is None
        
        # Create session
        from auth.otp_service import OTPSession
        test_session = OTPSession(
            phone_number=phone,
            otp_code="123456",
            created_at=time.time()
        )
        otp_service.sessions[phone] = test_session
        
        # Should return session
        session = otp_service.get_session_status(phone)
        assert session is not None
        assert session.phone_number == phone
    
    def test_cleanup_session(self, otp_service):
        """Test cleaning up OTP session"""
        phone = "+916123456789"
        
        # Create session
        from auth.otp_service import OTPSession
        session = OTPSession(
            phone_number=phone,
            otp_code="123456",
            created_at=time.time()
        )
        otp_service.sessions[phone] = session
        
        # Cleanup should succeed
        result = otp_service.cleanup_session(phone)
        assert result is True
        assert phone not in otp_service.sessions
        
        # Cleanup non-existent session should return False
        result = otp_service.cleanup_session(phone)
        assert result is False
    
    def test_is_phone_verified(self, otp_service):
        """Test checking if phone is verified"""
        phone = "+916123456789"
        
        # No session - not verified
        assert otp_service.is_phone_verified(phone) is False
        
        # Pending session - not verified
        from auth.otp_service import OTPSession
        session = OTPSession(
            phone_number=phone,
            otp_code="123456",
            created_at=time.time(),
            status=OTPStatus.PENDING
        )
        otp_service.sessions[phone] = session
        assert otp_service.is_phone_verified(phone) is False
        
        # Verified session - verified
        session.status = OTPStatus.VERIFIED
        assert otp_service.is_phone_verified(phone) is True