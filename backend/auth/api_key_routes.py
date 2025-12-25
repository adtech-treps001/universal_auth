"""
API Key Management Routes

API endpoints for managing API keys with encryption, rotation, and access control.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta
import logging

from database import get_db
# from services.api_key_service import APIKeyService
from services.api_key_validation import APIKeyValidationService
from services.project_service import ProjectConfigurationService
from auth.middleware import get_current_user, require_permission
from models.user import User
from models.api_key import APIKeyProvider, APIKeyStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/keys", tags=["api-keys"])

# Pydantic models for request/response
class APIKeyCreateRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    key_name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., description="API provider (openai, gemini, anthropic, etc.)")
    api_key_value: str = Field(..., min_length=8, description="The actual API key")
    
    # Optional configuration
    key_type: Optional[str] = Field(None, description="Key type (chat, embedding, etc.)")
    endpoint_url: Optional[str] = Field(None, description="Custom endpoint URL")
    model_access: Optional[List[str]] = Field(None, description="List of accessible models")
    scopes: Optional[List[str]] = Field(None, description="Allowed scopes")
    allowed_roles: Optional[List[str]] = Field(None, description="Roles that can use this key")
    ip_whitelist: Optional[List[str]] = Field(None, description="IP address restrictions")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Expiration in days")
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[Dict[str, str]] = Field(None, description="Key-value tags")
    
    # Rate limiting
    rate_limits: Optional[Dict[str, Any]] = Field(None, description="Rate limiting configuration")
    
    @validator('provider')
    def validate_provider(cls, v):
        valid_providers = [p.value for p in APIKeyProvider]
        if v not in valid_providers:
            raise ValueError(f"Provider must be one of: {', '.join(valid_providers)}")
        return v

class APIKeyUpdateRequest(BaseModel):
    key_name: Optional[str] = Field(None, min_length=1, max_length=100)
    key_type: Optional[str] = None
    endpoint_url: Optional[str] = None
    model_access: Optional[List[str]] = None
    scopes: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    ip_whitelist: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[Dict[str, str]] = None
    rate_limits: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = [s.value for s in APIKeyStatus]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v

class APIKeyRotateRequest(BaseModel):
    new_api_key_value: str = Field(..., min_length=8, description="New API key value")
    rotation_reason: Optional[str] = Field(None, max_length=500, description="Reason for rotation")

class APIKeyTemplateRequest(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., description="API provider")
    template_type: str = Field(..., description="Template type (development, production, etc.)")
    description: Optional[str] = Field(None, max_length=500)
    
    # Default configuration
    default_scopes: Optional[List[str]] = None
    default_rate_limits: Optional[Dict[str, Any]] = None
    default_model_access: Optional[List[str]] = None
    default_expiry_days: Optional[int] = Field(None, ge=1, le=365)
    is_public: bool = False

class APIKeyResponse(BaseModel):
    id: str
    key_name: str
    provider: str
    key_type: Optional[str]
    project_id: str
    tenant_id: Optional[str]
    
    # Configuration
    endpoint_url: Optional[str]
    model_access: Optional[List[str]]
    scopes: Optional[List[str]]
    allowed_roles: Optional[List[str]]
    
    # Status and lifecycle
    status: str
    version: int
    expires_at: Optional[str]
    last_used_at: Optional[str]
    usage_count: int
    is_expired: bool
    is_active: bool
    
    # Metadata
    description: Optional[str]
    tags: Optional[Dict[str, str]]
    created_at: str
    updated_at: str
    
    # Masked key for display
    masked_key: Optional[str] = None

class APIKeyUsageResponse(BaseModel):
    key_id: str
    key_name: str
    total_requests: int
    total_tokens: int
    error_count: int
    success_rate: float
    daily_usage: Dict[str, Dict[str, int]]
    last_used: Optional[str]
    created_at: str

@router.post("/", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new API key"""
    
    # Check project access
    project_service = ProjectConfigurationService(db)
    project = project_service.get_project(request.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions
    if project.owner_id != current_user.id:
        await require_permission(current_user, "api_key.create", db)
    
    try:
        api_key_service = APIKeyService(db)
        
        # Create API key
        api_key = api_key_service.create_api_key(
            project_id=request.project_id,
            key_name=request.key_name,
            provider=request.provider,
            api_key_value=request.api_key_value,
            user_id=current_user.id,
            key_type=request.key_type,
            endpoint_url=request.endpoint_url,
            model_access=request.model_access,
            scopes=request.scopes,
            allowed_roles=request.allowed_roles,
            ip_whitelist=request.ip_whitelist,
            expires_in_days=request.expires_in_days,
            description=request.description,
            tags=request.tags,
            rate_limits=request.rate_limits,
            tenant_id=current_user.tenant_id
        )
        
        # Generate masked key for response
        from services.api_key_encryption import APIKeyEncryption
        encryption = APIKeyEncryption()
        masked_key = encryption.mask_api_key(request.api_key_value)
        
        return APIKeyResponse(
            id=api_key.id,
            key_name=api_key.key_name,
            provider=api_key.provider,
            key_type=api_key.key_type,
            project_id=api_key.project_id,
            tenant_id=api_key.tenant_id,
            endpoint_url=api_key.endpoint_url,
            model_access=api_key.model_access,
            scopes=api_key.scopes,
            allowed_roles=api_key.allowed_roles,
            status=api_key.status,
            version=api_key.version,
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
            last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            usage_count=api_key.usage_count,
            is_expired=api_key.is_expired,
            is_active=api_key.is_active,
            description=api_key.description,
            tags=api_key.tags,
            created_at=api_key.created_at.isoformat(),
            updated_at=api_key.updated_at.isoformat(),
            masked_key=masked_key
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )

@router.get("/project/{project_id}", response_model=List[APIKeyResponse])
async def list_project_api_keys(
    project_id: str,
    include_inactive: bool = Query(False, description="Include inactive keys"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List API keys for a project"""
    
    # Check project access
    project_service = ProjectConfigurationService(db)
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions
    if project.owner_id != current_user.id:
        await require_permission(current_user, "api_key.read", db)
    
    try:
        api_key_service = APIKeyService(db)
        api_keys = api_key_service.list_project_api_keys(
            project_id=project_id,
            user_id=current_user.id,
            include_inactive=include_inactive
        )
        
        return [
            APIKeyResponse(
                id=key.id,
                key_name=key.key_name,
                provider=key.provider,
                key_type=key.key_type,
                project_id=key.project_id,
                tenant_id=key.tenant_id,
                endpoint_url=key.endpoint_url,
                model_access=key.model_access,
                scopes=key.scopes,
                allowed_roles=key.allowed_roles,
                status=key.status,
                version=key.version,
                expires_at=key.expires_at.isoformat() if key.expires_at else None,
                last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
                usage_count=key.usage_count,
                is_expired=key.is_expired,
                is_active=key.is_active,
                description=key.description,
                tags=key.tags,
                created_at=key.created_at.isoformat(),
                updated_at=key.updated_at.isoformat()
            )
            for key in api_keys
        ]
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )

@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    include_key: bool = Query(False, description="Include masked key in response"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific API key"""
    
    try:
        api_key_service = APIKeyService(db)
        api_key = api_key_service.get_api_key(
            key_id=key_id,
            user_id=current_user.id,
            decrypt=include_key
        )
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Generate masked key if requested
        masked_key = None
        if include_key and hasattr(api_key, '_decrypted_value'):
            from services.api_key_encryption import APIKeyEncryption
            encryption = APIKeyEncryption()
            masked_key = encryption.mask_api_key(api_key._decrypted_value)
        
        return APIKeyResponse(
            id=api_key.id,
            key_name=api_key.key_name,
            provider=api_key.provider,
            key_type=api_key.key_type,
            project_id=api_key.project_id,
            tenant_id=api_key.tenant_id,
            endpoint_url=api_key.endpoint_url,
            model_access=api_key.model_access,
            scopes=api_key.scopes,
            allowed_roles=api_key.allowed_roles,
            status=api_key.status,
            version=api_key.version,
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
            last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            usage_count=api_key.usage_count,
            is_expired=api_key.is_expired,
            is_active=api_key.is_active,
            description=api_key.description,
            tags=api_key.tags,
            created_at=api_key.created_at.isoformat(),
            updated_at=api_key.updated_at.isoformat(),
            masked_key=masked_key
        )
        
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this API key"
        )
    except Exception as e:
        logger.error(f"Error getting API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get API key"
        )

@router.put("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    request: APIKeyUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an API key"""
    
    try:
        api_key_service = APIKeyService(db)
        
        # Convert request to updates dict
        updates = request.dict(exclude_unset=True)
        
        api_key = api_key_service.update_api_key(
            key_id=key_id,
            user_id=current_user.id,
            updates=updates
        )
        
        return APIKeyResponse(
            id=api_key.id,
            key_name=api_key.key_name,
            provider=api_key.provider,
            key_type=api_key.key_type,
            project_id=api_key.project_id,
            tenant_id=api_key.tenant_id,
            endpoint_url=api_key.endpoint_url,
            model_access=api_key.model_access,
            scopes=api_key.scopes,
            allowed_roles=api_key.allowed_roles,
            status=api_key.status,
            version=api_key.version,
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
            last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            usage_count=api_key.usage_count,
            is_expired=api_key.is_expired,
            is_active=api_key.is_active,
            description=api_key.description,
            tags=api_key.tags,
            created_at=api_key.created_at.isoformat(),
            updated_at=api_key.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update this API key"
        )
    except Exception as e:
        logger.error(f"Error updating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key"
        )

@router.post("/{key_id}/rotate", response_model=APIKeyResponse)
async def rotate_api_key(
    key_id: str,
    request: APIKeyRotateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rotate an API key with a new value"""
    
    try:
        api_key_service = APIKeyService(db)
        
        new_key = api_key_service.rotate_api_key(
            key_id=key_id,
            new_api_key_value=request.new_api_key_value,
            user_id=current_user.id,
            rotation_reason=request.rotation_reason
        )
        
        # Generate masked key for response
        from services.api_key_encryption import APIKeyEncryption
        encryption = APIKeyEncryption()
        masked_key = encryption.mask_api_key(request.new_api_key_value)
        
        return APIKeyResponse(
            id=new_key.id,
            key_name=new_key.key_name,
            provider=new_key.provider,
            key_type=new_key.key_type,
            project_id=new_key.project_id,
            tenant_id=new_key.tenant_id,
            endpoint_url=new_key.endpoint_url,
            model_access=new_key.model_access,
            scopes=new_key.scopes,
            allowed_roles=new_key.allowed_roles,
            status=new_key.status,
            version=new_key.version,
            expires_at=new_key.expires_at.isoformat() if new_key.expires_at else None,
            last_used_at=new_key.last_used_at.isoformat() if new_key.last_used_at else None,
            usage_count=new_key.usage_count,
            is_expired=new_key.is_expired,
            is_active=new_key.is_active,
            description=new_key.description,
            tags=new_key.tags,
            created_at=new_key.created_at.isoformat(),
            updated_at=new_key.updated_at.isoformat(),
            masked_key=masked_key
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to rotate this API key"
        )
    except Exception as e:
        logger.error(f"Error rotating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate API key"
        )

@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    reason: Optional[str] = Query(None, description="Reason for revocation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke an API key"""
    
    try:
        api_key_service = APIKeyService(db)
        
        success = api_key_service.revoke_api_key(
            key_id=key_id,
            user_id=current_user.id,
            reason=reason
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return {"message": "API key revoked successfully"}
        
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to revoke this API key"
        )
    except Exception as e:
        logger.error(f"Error revoking API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )

@router.get("/{key_id}/usage", response_model=APIKeyUsageResponse)
async def get_api_key_usage(
    key_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get usage statistics for an API key"""
    
    try:
        api_key_service = APIKeyService(db)
        
        usage_stats = api_key_service.get_usage_statistics(
            key_id=key_id,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date
        )
        
        return APIKeyUsageResponse(**usage_stats)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view usage statistics"
        )
    except Exception as e:
        logger.error(f"Error getting usage statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage statistics"
        )

@router.post("/{key_id}/validate-comprehensive")
async def validate_api_key_comprehensive(
    key_id: str,
    request: Request,
    scopes: Optional[List[str]] = Query(None, description="Required scopes"),
    model: Optional[str] = Query(None, description="Model to access"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Comprehensive API key validation with scope and rate limit checking"""
    
    try:
        validation_service = APIKeyValidationService(db)
        
        # Build request context
        request_context = {
            'client_ip': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent'),
            'session_id': getattr(current_user, 'session_id', None),
            'endpoint': request.url.path,
            'method': request.method,
            'scopes': scopes,
            'model': model
        }
        
        # Perform comprehensive validation
        result = validation_service.validate_api_key(
            key_id=key_id,
            user_id=current_user.id,
            request_context=request_context
        )
        
        # Log validation attempt
        validation_service.log_validation_attempt(
            key_id=key_id,
            user_id=current_user.id,
            success=result['valid'],
            reason=result['message'] if not result['valid'] else None,
            request_context=request_context
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in comprehensive validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation error occurred"
        )

@router.post("/{key_id}/validate")
async def validate_api_key_access(
    key_id: str,
    scopes: Optional[List[str]] = Query(None, description="Required scopes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate API key access for specific scopes"""
    
    try:
        api_key_service = APIKeyService(db)
        
        is_valid = api_key_service.validate_api_key_access(
            key_id=key_id,
            user_id=current_user.id,
            scopes=scopes
        )
        
        return {
            "valid": is_valid,
            "key_id": key_id,
            "user_id": current_user.id,
            "scopes": scopes,
            "validated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error validating API key access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate API key access"
        )

# Template management endpoints
@router.post("/templates", response_model=dict)
async def create_api_key_template(
    request: APIKeyTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create an API key template"""
    
    await require_permission(current_user, "api_key.template.create", db)
    
    try:
        api_key_service = APIKeyService(db)
        
        config = {
            'default_scopes': request.default_scopes,
            'default_rate_limits': request.default_rate_limits,
            'default_model_access': request.default_model_access,
            'default_expiry_days': request.default_expiry_days,
            'description': request.description,
            'is_public': request.is_public
        }
        
        template = api_key_service.create_api_key_template(
            template_name=request.template_name,
            provider=request.provider,
            template_type=request.template_type,
            user_id=current_user.id,
            config=config
        )
        
        return {
            "id": template.id,
            "template_name": template.template_name,
            "provider": template.provider,
            "template_type": template.template_type,
            "description": template.description,
            "created_at": template.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating API key template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key template"
        )

@router.post("/templates/{template_id}/apply", response_model=APIKeyResponse)
async def apply_api_key_template(
    template_id: str,
    project_id: str = Query(..., description="Project ID"),
    key_name: str = Query(..., description="API key name"),
    api_key_value: str = Query(..., description="API key value"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create API key from template"""
    
    try:
        api_key_service = APIKeyService(db)
        
        api_key = api_key_service.apply_template(
            template_id=template_id,
            project_id=project_id,
            key_name=key_name,
            api_key_value=api_key_value,
            user_id=current_user.id
        )
        
        # Generate masked key for response
        from services.api_key_encryption import APIKeyEncryption
        encryption = APIKeyEncryption()
        masked_key = encryption.mask_api_key(api_key_value)
        
        return APIKeyResponse(
            id=api_key.id,
            key_name=api_key.key_name,
            provider=api_key.provider,
            key_type=api_key.key_type,
            project_id=api_key.project_id,
            tenant_id=api_key.tenant_id,
            endpoint_url=api_key.endpoint_url,
            model_access=api_key.model_access,
            scopes=api_key.scopes,
            allowed_roles=api_key.allowed_roles,
            status=api_key.status,
            version=api_key.version,
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
            last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            usage_count=api_key.usage_count,
            is_expired=api_key.is_expired,
            is_active=api_key.is_active,
            description=api_key.description,
            tags=api_key.tags,
            created_at=api_key.created_at.isoformat(),
            updated_at=api_key.updated_at.isoformat(),
            masked_key=masked_key
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error applying API key template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply API key template"
        )