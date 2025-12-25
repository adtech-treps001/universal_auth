
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class WorkflowResponse(BaseModel):
    workflow: str

class TokenResponse(BaseModel):
    access_token: str
    role: str

class OAuthUrlResponse(BaseModel):
    auth_url: str
    provider: str

class ProviderListResponse(BaseModel):
    providers: List[str]

class UserInfoResponse(BaseModel):
    provider_user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None

class OAuthTokensResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None

class OAuthCallbackResponse(BaseModel):
    success: bool
    provider: str
    user_info: UserInfoResponse
    tokens: OAuthTokensResponse

class OTPSendRequest(BaseModel):
    phone_number: str
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if not v or not v.strip():
            raise ValueError('Phone number is required')
        return v.strip()

class OTPSendResponse(BaseModel):
    success: bool
    message: str

class OTPVerifyRequest(BaseModel):
    phone_number: str
    otp_code: str
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if not v or not v.strip():
            raise ValueError('Phone number is required')
        return v.strip()
    
    @validator('otp_code')
    def validate_otp_code(cls, v):
        if not v or not v.strip():
            raise ValueError('OTP code is required')
        # Remove spaces and validate length
        cleaned = v.strip().replace(' ', '')
        if not cleaned.isdigit():
            raise ValueError('OTP code must contain only digits')
        if len(cleaned) != 6:
            raise ValueError('OTP code must be 6 digits')
        return cleaned

class OTPVerifyResponse(BaseModel):
    success: bool
    message: str
    phone_number: str
    verified: bool
    user_id: Optional[str] = None

# User Management Schemas

class UserCreateRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    provider_data: Optional[Dict[str, Any]] = None
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v

class UserProfileData(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    completion_percentage: Optional[int] = None
    required_fields_completed: Optional[bool] = None

class UserResponse(BaseModel):
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    session_count: int
    created_at: datetime
    last_login: Optional[datetime] = None
    profile: Optional[UserProfileData] = None

class UserProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

class UserProfileResponse(BaseModel):
    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    completion_percentage: int
    required_fields_completed: bool
    updated_at: datetime

class ProfileCompletionResponse(BaseModel):
    completion_percentage: int
    required_fields_completed: bool
    missing_required_fields: List[str]
    next_progressive_fields: List[str]
    session_count: int
    total_possible_fields: List[str]

class ProgressiveFieldsResponse(BaseModel):
    user_id: str
    fields: List[str]
