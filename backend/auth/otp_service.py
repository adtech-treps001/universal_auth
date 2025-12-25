
"""
Mobile OTP Authentication Service

This module implements OTP (One-Time Password) authentication for mobile numbers,
specifically designed for Indian mobile numbers with SMS integration.
"""

import re
import time
import random
import secrets
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class OTPStatus(Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    FAILED = "failed"

@dataclass
class OTPSession:
    """OTP session data"""
    phone_number: str
    otp_code: str
    created_at: float
    attempts: int = 0
    status: OTPStatus = OTPStatus.PENDING
    expires_at: float = 0

    def __post_init__(self):
        if self.expires_at == 0:
            self.expires_at = self.created_at + 300  # 5 minutes default

class IndianMobileValidator:
    """Validator for Indian mobile numbers"""
    
    # Indian mobile number patterns
    INDIAN_MOBILE_PATTERN = re.compile(r'^(\+91|91)?[6-9]\d{9}$')
    
    @classmethod
    def validate(cls, phone_number: str) -> bool:
        """
        Validate Indian mobile number format
        
        Accepts formats:
        - +916123456789
        - 916123456789  
        - 6123456789
        
        Must start with 6, 7, 8, or 9 (valid Indian mobile prefixes)
        """
        if not phone_number:
            return False
        
        # Remove spaces and hyphens
        cleaned = re.sub(r'[\s\-]', '', phone_number)
        
        return bool(cls.INDIAN_MOBILE_PATTERN.match(cleaned))
    
    @classmethod
    def normalize(cls, phone_number: str) -> str:
        """
        Normalize Indian mobile number to +91XXXXXXXXXX format
        """
        if not cls.validate(phone_number):
            raise ValueError("Invalid Indian mobile number format")
        
        # Remove spaces and hyphens
        cleaned = re.sub(r'[\s\-]', '', phone_number)
        
        # Remove country code if present and add +91
        if cleaned.startswith('+91'):
            return cleaned
        elif cleaned.startswith('91') and len(cleaned) == 12:
            return '+' + cleaned
        elif len(cleaned) == 10:
            return '+91' + cleaned
        else:
            raise ValueError("Invalid Indian mobile number format")

class SMSGateway:
    """SMS Gateway interface for sending OTP messages"""
    
    def __init__(self, provider: str = "mock"):
        self.provider = provider
    
    async def send_sms(self, phone_number: str, message: str) -> bool:
        """
        Send SMS message to phone number
        
        In production, this would integrate with actual SMS providers like:
        - Twilio
        - AWS SNS
        - MSG91
        - TextLocal
        """
        if self.provider == "mock":
            # Mock implementation for testing
            print(f"[SMS Mock] Sending to {phone_number}: {message}")
            return True
        
        # TODO: Implement actual SMS provider integration
        raise NotImplementedError(f"SMS provider {self.provider} not implemented")

class OTPService:
    """OTP authentication service for mobile numbers"""
    
    def __init__(self, sms_gateway: Optional[SMSGateway] = None):
        self.sms_gateway = sms_gateway or SMSGateway()
        self.sessions: Dict[str, OTPSession] = {}  # In production, use Redis
        self.otp_length = 6
        self.otp_expiry_seconds = 300  # 5 minutes
        self.max_attempts = 3
        self.rate_limit_window = 60  # 1 minute between OTP requests
        self.rate_limit_tracker: Dict[str, float] = {}
    
    def _generate_otp(self) -> str:
        """Generate a secure random OTP"""
        return ''.join([str(random.randint(0, 9)) for _ in range(self.otp_length)])
    
    def _is_rate_limited(self, phone_number: str) -> bool:
        """Check if phone number is rate limited"""
        last_request = self.rate_limit_tracker.get(phone_number, 0)
        return time.time() - last_request < self.rate_limit_window
    
    def _cleanup_expired_sessions(self):
        """Remove expired OTP sessions"""
        current_time = time.time()
        expired_keys = [
            key for key, session in self.sessions.items()
            if current_time > session.expires_at
        ]
        for key in expired_keys:
            del self.sessions[key]
    
    async def send_otp(self, phone_number: str) -> Tuple[bool, str]:
        """
        Send OTP to Indian mobile number
        
        Returns:
            Tuple[bool, str]: (success, message/error)
        """
        try:
            # Validate Indian mobile number
            if not IndianMobileValidator.validate(phone_number):
                return False, "Invalid Indian mobile number format"
            
            # Normalize phone number
            normalized_phone = IndianMobileValidator.normalize(phone_number)
            
            # Check rate limiting
            if self._is_rate_limited(normalized_phone):
                return False, "Please wait before requesting another OTP"
            
            # Clean up expired sessions
            self._cleanup_expired_sessions()
            
            # Generate OTP
            otp_code = self._generate_otp()
            current_time = time.time()
            
            # Create OTP session
            session = OTPSession(
                phone_number=normalized_phone,
                otp_code=otp_code,
                created_at=current_time,
                expires_at=current_time + self.otp_expiry_seconds
            )
            
            # Store session
            self.sessions[normalized_phone] = session
            
            # Update rate limiting
            self.rate_limit_tracker[normalized_phone] = current_time
            
            # Send SMS
            message = f"Your verification code is: {otp_code}. Valid for 5 minutes. Do not share this code."
            sms_sent = await self.sms_gateway.send_sms(normalized_phone, message)
            
            if not sms_sent:
                # Clean up session if SMS failed
                del self.sessions[normalized_phone]
                return False, "Failed to send OTP. Please try again."
            
            return True, "OTP sent successfully"
            
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Failed to send OTP: {str(e)}"
    
    def verify_otp(self, phone_number: str, otp_code: str) -> Tuple[bool, str]:
        """
        Verify OTP for phone number
        
        Returns:
            Tuple[bool, str]: (success, message/error)
        """
        try:
            # Validate and normalize phone number
            if not IndianMobileValidator.validate(phone_number):
                return False, "Invalid Indian mobile number format"
            
            normalized_phone = IndianMobileValidator.normalize(phone_number)
            
            # Check if session exists
            if normalized_phone not in self.sessions:
                return False, "No OTP session found. Please request a new OTP."
            
            session = self.sessions[normalized_phone]
            current_time = time.time()
            
            # Check if OTP is expired
            if current_time > session.expires_at:
                session.status = OTPStatus.EXPIRED
                return False, "OTP has expired. Please request a new one."
            
            # Check if already verified
            if session.status == OTPStatus.VERIFIED:
                return False, "OTP already verified"
            
            # Check max attempts
            if session.attempts >= self.max_attempts:
                session.status = OTPStatus.FAILED
                return False, "Maximum verification attempts exceeded. Please request a new OTP."
            
            # Increment attempts
            session.attempts += 1
            
            # Verify OTP
            if session.otp_code == otp_code:
                session.status = OTPStatus.VERIFIED
                return True, "OTP verified successfully"
            else:
                if session.attempts >= self.max_attempts:
                    session.status = OTPStatus.FAILED
                    return False, "Invalid OTP. Maximum attempts exceeded."
                else:
                    remaining = self.max_attempts - session.attempts
                    return False, f"Invalid OTP. {remaining} attempts remaining."
            
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"OTP verification failed: {str(e)}"
    
    def get_session_status(self, phone_number: str) -> Optional[OTPSession]:
        """Get OTP session status for phone number"""
        try:
            normalized_phone = IndianMobileValidator.normalize(phone_number)
            return self.sessions.get(normalized_phone)
        except ValueError:
            return None
    
    def cleanup_session(self, phone_number: str) -> bool:
        """Clean up OTP session for phone number"""
        try:
            normalized_phone = IndianMobileValidator.normalize(phone_number)
            if normalized_phone in self.sessions:
                del self.sessions[normalized_phone]
                return True
            return False
        except ValueError:
            return False
    
    def is_phone_verified(self, phone_number: str) -> bool:
        """Check if phone number has been verified"""
        session = self.get_session_status(phone_number)
        return session is not None and session.status == OTPStatus.VERIFIED
