"""
API Key Validation Routes

API endpoints for validating API key access, scope checking, and rate limiting.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from database import get_db
from services.api_key_validation import APIKeyValidationService, ScopeValidator, RateLimitManager
from auth.middleware import get_current_user
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/keys/validation", tags=["api-key-validation"])

# Pydantic models for request/response
class ValidationRequest(BaseModel):
    key_id: str = Field(..., description="API key ID to validate")
    scopes: Optional[List[str]] = Field(None, description="Required scopes")
    model: Optional[str] = Field(None, description="Model to access")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    method: str = Field("GET", description="HTTP method")
    estimated_tokens: Optional[int] = Field(None, description="Estimated token usage")

class ValidationResponse(BaseModel):
    valid: bool
    message: str
    timestamp: str
    
    # Additional data when valid
    key_id: Optional[str] = None
    provider: Optional[str] = None
    allowed_scopes: Optional[List[str]] = None
    allowed_models: Optional[List[str]] = None
    rate_limits: Optional[Dict[str, Any]] = None
    remaining_requests: Optional[int] = None
    reset_time: Optional[int] = None

class ScopeCheckRequest(BaseModel):
    key_id: str = Field(..., description="API key ID")
    required_scopes: List[str] = Field(..., description="Required scopes")

class RateLimitCheckRequest(BaseModel):
    key_id: str = Field(..., description="API key ID")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    method: str = Field("GET", description="HTTP method")
    estimated_tokens: Optional[int] = Field(None, description="Estimated token usage")

class RateLimitResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    limit: Optional[int] = None
    current: Optional[int] = None
    remaining_requests: Optional[int] = None
    reset_time: Optional[int] = None

class KeyPermissionsResponse(BaseModel):
    key_id: str
    key_name: str
    provider: str
    has_access: bool
    status: str
    is_active: bool
    is_expired: bool
    expires_at: Optional[str]
    scopes: List[str]
    allowed_roles: List[str]
    allowed_models: List[str]
    ip_whitelist: List[str]
    rate_limits: Dict[str, Any]
    usage_count: int
    last_used_at: Optional[str]

class ScopeValidationRequest(BaseModel):
    scopes: List[str] = Field(..., description="Scopes to validate")

class ScopeValidationResponse(BaseModel):
    valid_scopes: List[str]
    invalid_scopes: List[str]
    all_valid: bool

def _extract_request_context(request: Request, current_user: User) -> Dict[str, Any]:
    """Extract request context for validation"""
    return {
        'client_ip': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent'),
        'session_id': getattr(current_user, 'session_id', None)
    }

@router.post("/validate", response_model=ValidationResponse)
async def validate_api_key(
    validation_request: ValidationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Comprehensive API key validation
    
    Validates API key access, scopes, rate limits, and permissions
    """
    try:
        validation_service = APIKeyValidationService(db)
        
        # Build request context
        request_context = _extract_request_context(request, current_user)
        request_context.update({
            'scopes': validation_request.scopes,
            'model': validation_request.model,
            'endpoint': validation_request.endpoint,
            'method': validation_request.method,
            'estimated_tokens': validation_request.estimated_tokens
        })
        
        # Perform validation
        result = validation_service.validate_api_key(
            key_id=validation_request.key_id,
            user_id=current_user.id,
            request_context=request_context
        )
        
        # Log validation attempt
        validation_service.log_validation_attempt(
            key_id=validation_request.key_id,
            user_id=current_user.id,
            success=result['valid'],
            reason=result['message'] if not result['valid'] else None,
            request_context=request_context
        )
        
        return ValidationResponse(**result)
        
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation error occurred"
        )

@router.post("/scope-check", response_model=dict)
async def check_scope_access(
    scope_request: ScopeCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if API key has required scopes"""
    
    try:
        validation_service = APIKeyValidationService(db)
        
        has_access = validation_service.check_scope_access(
            key_id=scope_request.key_id,
            required_scopes=scope_request.required_scopes
        )
        
        return {
            "key_id": scope_request.key_id,
            "required_scopes": scope_request.required_scopes,
            "has_access": has_access,
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking scope access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check scope access"
        )

@router.post("/rate-limit-check", response_model=RateLimitResponse)
async def check_rate_limit(
    rate_limit_request: RateLimitCheckRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check rate limit status for API key"""
    
    try:
        validation_service = APIKeyValidationService(db)
        
        # Build request context
        request_context = _extract_request_context(request, current_user)
        request_context.update({
            'endpoint': rate_limit_request.endpoint,
            'method': rate_limit_request.method,
            'estimated_tokens': rate_limit_request.estimated_tokens
        })
        
        result = validation_service.check_rate_limit(
            key_id=rate_limit_request.key_id,
            request_context=request_context
        )
        
        return RateLimitResponse(**result)
        
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check rate limit"
        )

@router.get("/{key_id}/permissions", response_model=KeyPermissionsResponse)
async def get_key_permissions(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed permissions for an API key"""
    
    try:
        validation_service = APIKeyValidationService(db)
        
        permissions = validation_service.get_key_permissions(
            key_id=key_id,
            user_id=current_user.id
        )
        
        if 'error' in permissions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=permissions['error']
            )
        
        return KeyPermissionsResponse(**permissions)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting key permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get key permissions"
        )

@router.post("/role-access-check")
async def validate_role_access(
    key_id: str = Query(..., description="API key ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate if user's roles allow access to API key"""
    
    try:
        validation_service = APIKeyValidationService(db)
        
        has_access = validation_service.validate_role_access(
            key_id=key_id,
            user_id=current_user.id
        )
        
        return {
            "key_id": key_id,
            "user_id": current_user.id,
            "has_access": has_access,
            "validated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error validating role access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate role access"
        )

# Utility endpoints for scope management
@router.post("/scopes/validate", response_model=ScopeValidationResponse)
async def validate_scopes(
    scope_request: ScopeValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """Validate scope format and existence"""
    
    try:
        result = ScopeValidator.validate_scopes(scope_request.scopes)
        return ScopeValidationResponse(**result)
        
    except Exception as e:
        logger.error(f"Error validating scopes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate scopes"
        )

@router.get("/scopes/{scope}/hierarchy")
async def get_scope_hierarchy(
    scope: str,
    current_user: User = Depends(get_current_user)
):
    """Get scope hierarchy (parent scopes)"""
    
    try:
        hierarchy = ScopeValidator.get_scope_hierarchy(scope)
        
        return {
            "scope": scope,
            "hierarchy": hierarchy,
            "depth": len(hierarchy)
        }
        
    except Exception as e:
        logger.error(f"Error getting scope hierarchy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get scope hierarchy"
        )

@router.post("/scopes/check-permission")
async def check_scope_permission(
    allowed_scopes: List[str] = Query(..., description="Allowed scopes"),
    required_scope: str = Query(..., description="Required scope"),
    current_user: User = Depends(get_current_user)
):
    """Check if required scope is covered by allowed scopes"""
    
    try:
        has_permission = ScopeValidator.check_scope_permission(
            allowed_scopes=allowed_scopes,
            required_scope=required_scope
        )
        
        return {
            "allowed_scopes": allowed_scopes,
            "required_scope": required_scope,
            "has_permission": has_permission,
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking scope permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check scope permission"
        )

@router.get("/scopes/standard")
async def get_standard_scopes(
    current_user: User = Depends(get_current_user)
):
    """Get list of standard scopes"""
    
    return {
        "standard_scopes": ScopeValidator.STANDARD_SCOPES,
        "total_count": len(ScopeValidator.STANDARD_SCOPES)
    }

@router.get("/rate-limits/calculate-reset")
async def calculate_rate_limit_reset(
    limit_type: str = Query(..., description="Rate limit type (minute, hour, day)"),
    current_user: User = Depends(get_current_user)
):
    """Calculate when rate limit resets"""
    
    try:
        current_time = datetime.utcnow()
        reset_time = RateLimitManager.calculate_rate_limit_reset(limit_type, current_time)
        
        return {
            "limit_type": limit_type,
            "current_time": current_time.isoformat(),
            "reset_time": reset_time.isoformat(),
            "seconds_until_reset": int((reset_time - current_time).total_seconds())
        }
        
    except Exception as e:
        logger.error(f"Error calculating rate limit reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate rate limit reset"
        )