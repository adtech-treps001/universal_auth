
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from typing import Optional, List
from .schemas import (
    WorkflowResponse, TokenResponse, OAuthUrlResponse, ProviderListResponse, 
    OTPSendRequest, OTPSendResponse, OTPVerifyRequest, OTPVerifyResponse,
    UserCreateRequest, UserResponse, UserProfileUpdateRequest, UserProfileResponse,
    ProfileCompletionResponse, ProgressiveFieldsResponse
)
from .oauth_service import OAuthService
from .otp_service import OTPService
from services.user_service import UserService
from . import (
    rbac_routes, tenant_routes, opa_routes, project_routes
    # theme_routes, api_key_routes, api_key_validation_routes
)
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter()
oauth_service = OAuthService()
otp_service = OTPService()

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Get user service with database session"""
    return UserService(db)

@router.get("/workflow", response_model=WorkflowResponse)
def get_workflow():
    """Get the current authentication workflow configuration"""
    return {"workflow": "2_EMAIL_SOCIAL_GOOGLE"}

@router.get("/providers", response_model=ProviderListResponse)
def get_available_providers():
    """Get list of configured OAuth providers"""
    providers = oauth_service.get_available_providers()
    return {"providers": providers}

@router.post("/otp/send", response_model=OTPSendResponse)
async def send_otp(request: OTPSendRequest):
    """Send OTP to Indian mobile number"""
    success, message = await otp_service.send_otp(request.phone_number)
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

@router.post("/otp/verify", response_model=OTPVerifyResponse)
def verify_otp(request: OTPVerifyRequest, user_service: UserService = Depends(get_user_service)):
    """Verify OTP for mobile number"""
    success, message = otp_service.verify_otp(request.phone_number, request.otp_code)
    
    if success:
        # Create or get user
        user = user_service.get_user_by_phone(request.phone_number)
        if not user:
            user = user_service.create_user(phone=request.phone_number)
        
        # Increment session count for progressive profiling
        user_service.increment_session_count(user.id)
        
        # TODO: Generate JWT token for the user
        return {
            "success": True,
            "message": message,
            "phone_number": request.phone_number,
            "verified": True,
            "user_id": user.id
        }
    else:
        raise HTTPException(status_code=400, detail=message)

@router.get("/otp/status/{phone_number}")
def get_otp_status(phone_number: str):
    """Get OTP session status for phone number"""
    session = otp_service.get_session_status(phone_number)
    
    if session:
        return {
            "phone_number": session.phone_number,
            "status": session.status.value,
            "attempts": session.attempts,
            "expires_at": session.expires_at,
            "verified": session.status.value == "verified"
        }
    else:
        raise HTTPException(status_code=404, detail="No OTP session found")

@router.post("/users", response_model=UserResponse)
def create_user(request: UserCreateRequest, user_service: UserService = Depends(get_user_service)):
    """Create a new user"""
    try:
        user = user_service.create_user(
            email=request.email,
            phone=request.phone,
            provider_data=request.provider_data
        )
        
        return {
            "id": user.id,
            "email": user.email,
            "phone": user.phone,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "session_count": user.session_count,
            "created_at": user.created_at,
            "profile": {
                "first_name": user.profile.first_name,
                "last_name": user.profile.last_name,
                "display_name": user.profile.display_name,
                "avatar_url": user.profile.avatar_url,
                "completion_percentage": user.profile.completion_percentage,
                "required_fields_completed": user.profile.required_fields_completed
            } if user.profile else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, user_service: UserService = Depends(get_user_service)):
    """Get user by ID"""
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "session_count": user.session_count,
        "created_at": user.created_at,
        "last_login": user.last_login,
        "profile": {
            "first_name": user.profile.first_name,
            "last_name": user.profile.last_name,
            "display_name": user.profile.display_name,
            "avatar_url": user.profile.avatar_url,
            "bio": user.profile.bio,
            "company": user.profile.company,
            "job_title": user.profile.job_title,
            "location": user.profile.location,
            "website": user.profile.website,
            "completion_percentage": user.profile.completion_percentage,
            "required_fields_completed": user.profile.required_fields_completed
        } if user.profile else None
    }

@router.put("/users/{user_id}/profile", response_model=UserProfileResponse)
def update_user_profile(
    user_id: str, 
    request: UserProfileUpdateRequest, 
    user_service: UserService = Depends(get_user_service)
):
    """Update user profile"""
    try:
        profile = user_service.update_user_profile(user_id, request.dict(exclude_unset=True))
        
        return {
            "user_id": profile.user_id,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "display_name": profile.display_name,
            "avatar_url": profile.avatar_url,
            "bio": profile.bio,
            "company": profile.company,
            "job_title": profile.job_title,
            "location": profile.location,
            "website": profile.website,
            "timezone": profile.timezone,
            "language": profile.language,
            "completion_percentage": profile.completion_percentage,
            "required_fields_completed": profile.required_fields_completed,
            "updated_at": profile.updated_at
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/{user_id}/profile/completion", response_model=ProfileCompletionResponse)
def get_profile_completion(user_id: str, user_service: UserService = Depends(get_user_service)):
    """Get user profile completion status"""
    status = user_service.get_profile_completion_status(user_id)
    return status

@router.get("/users/{user_id}/progressive-fields", response_model=ProgressiveFieldsResponse)
def get_progressive_fields(user_id: str, user_service: UserService = Depends(get_user_service)):
    """Get progressive profiling fields for user"""
    fields = user_service.get_progressive_profiling_fields(user_id)
    return {"fields": fields, "user_id": user_id}

@router.post("/users/{user_id}/session")
def increment_session(user_id: str, user_service: UserService = Depends(get_user_service)):
    """Increment user session count"""
    try:
        session_count = user_service.increment_session_count(user_id)
        return {"user_id": user_id, "session_count": session_count}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/users/search")
def search_users(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
    user_service: UserService = Depends(get_user_service)
):
    """Search users by email, phone, or name"""
    users = user_service.search_users(q, limit)
    
    return {
        "query": q,
        "results": [
            {
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
                "display_name": user.profile.display_name if user.profile else None,
                "first_name": user.profile.first_name if user.profile else None,
                "last_name": user.profile.last_name if user.profile else None,
                "avatar_url": user.profile.avatar_url if user.profile else None
            }
            for user in users
        ]
    }

@router.post("/users/{user_id}/deactivate")
def deactivate_user(user_id: str, user_service: UserService = Depends(get_user_service)):
    """Deactivate user account"""
    success = user_service.deactivate_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deactivated successfully"}

@router.post("/users/{user_id}/reactivate")
def reactivate_user(user_id: str, user_service: UserService = Depends(get_user_service)):
    """Reactivate user account"""
    success = user_service.reactivate_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User reactivated successfully"}

@router.post("/login", response_model=TokenResponse)
def login():
    """Legacy login endpoint - will be replaced by OAuth flows"""
    return {"access_token": "jwt-token", "role": "user"}

# Include sub-routers
router.include_router(rbac_routes.router)
router.include_router(tenant_routes.router)
router.include_router(opa_routes.router)
router.include_router(project_routes.router)
# router.include_router(theme_routes.router)
# router.include_router(api_key_routes.router)
# router.include_router(api_key_validation_routes.router)
