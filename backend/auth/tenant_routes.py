"""
Tenant API Routes

This module provides REST API endpoints for multi-tenant management
including tenant creation, user management, and configuration.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from database import get_db
from services.tenant_service import TenantService
from auth.middleware import get_current_user, require_capability

router = APIRouter(prefix="/tenants", tags=["tenants"])

# Request/Response Models
class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    config: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: Optional[str] = None

class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    config: Optional[Dict[str, Any]] = None

class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    is_active: bool

class UserInvite(BaseModel):
    user_emails: List[str] = Field(..., min_items=1)
    role: str = Field(default="user")

class UserTenantAssignment(BaseModel):
    user_id: str
    role: str = Field(default="user")

class BulkInviteResponse(BaseModel):
    successful: List[Dict[str, Any]]
    failed: List[Dict[str, Any]]
    already_members: List[Dict[str, Any]]

@router.post("/", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new tenant"""
    # Check if user has admin capability
    if not require_capability(current_user, "tenant:create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create tenant"
        )
    
    tenant_service = TenantService(db)
    
    try:
        tenant = tenant_service.create_tenant(
            name=tenant_data.name,
            config=tenant_data.config,
            tenant_id=tenant_data.tenant_id
        )
        
        return TenantResponse(
            tenant_id=tenant.tenant_id,
            name=tenant.name,
            config=tenant.config,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            is_active=tenant.is_active
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all tenants"""
    # Check if user has admin capability
    if not require_capability(current_user, "tenant:list"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list tenants"
        )
    
    tenant_service = TenantService(db)
    tenants = tenant_service.list_tenants()
    
    return [
        TenantResponse(
            tenant_id=tenant.tenant_id,
            name=tenant.name,
            config=tenant.config,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            is_active=tenant.is_active
        )
        for tenant in tenants
    ]

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tenant by ID"""
    # Check if user has access to this tenant
    if not require_capability(current_user, "tenant:read", tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access tenant"
        )
    
    tenant_service = TenantService(db)
    tenant = tenant_service.get_tenant(tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return TenantResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        config=tenant.config,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        is_active=tenant.is_active
    )

@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_data: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update tenant information"""
    # Check if user has admin capability for this tenant
    if not require_capability(current_user, "tenant:update", tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update tenant"
        )
    
    tenant_service = TenantService(db)
    
    success = tenant_service.update_tenant(
        tenant_id=tenant_id,
        name=tenant_data.name,
        config=tenant_data.config
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Return updated tenant
    tenant = tenant_service.get_tenant(tenant_id)
    return TenantResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        config=tenant.config,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        is_active=tenant.is_active
    )

@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete tenant and all associated data"""
    # Check if user has admin capability
    if not require_capability(current_user, "tenant:delete"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete tenant"
        )
    
    tenant_service = TenantService(db)
    success = tenant_service.delete_tenant(tenant_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return {"message": "Tenant deleted successfully"}

@router.post("/{tenant_id}/users", response_model=Dict[str, Any])
async def add_user_to_tenant(
    tenant_id: str,
    assignment: UserTenantAssignment,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add user to tenant with specified role"""
    # Check if user has admin capability for this tenant
    if not require_capability(current_user, "tenant:manage_users", tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage tenant users"
        )
    
    tenant_service = TenantService(db)
    
    try:
        success = tenant_service.add_user_to_tenant(
            user_id=assignment.user_id,
            tenant_id=tenant_id,
            role=assignment.role
        )
        
        if success:
            return {"message": "User added to tenant successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add user to tenant"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{tenant_id}/users/{user_id}")
async def remove_user_from_tenant(
    tenant_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove user from tenant"""
    # Check if user has admin capability for this tenant
    if not require_capability(current_user, "tenant:manage_users", tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage tenant users"
        )
    
    tenant_service = TenantService(db)
    success = tenant_service.remove_user_from_tenant(user_id, tenant_id)
    
    if success:
        return {"message": "User removed from tenant successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in tenant"
        )

@router.get("/{tenant_id}/users", response_model=List[Dict[str, Any]])
async def get_tenant_users(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all users in tenant"""
    # Check if user has read capability for this tenant
    if not require_capability(current_user, "tenant:read_users", tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view tenant users"
        )
    
    tenant_service = TenantService(db)
    users = tenant_service.get_tenant_users(tenant_id)
    
    return users

@router.get("/users/{user_id}/tenants", response_model=List[Dict[str, Any]])
async def get_user_tenants(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all tenants user belongs to"""
    # Check if user is requesting their own tenants or has admin capability
    if current_user["user_id"] != user_id and not require_capability(current_user, "user:read_tenants"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view user tenants"
        )
    
    tenant_service = TenantService(db)
    tenants = tenant_service.get_user_tenants(user_id)
    
    return tenants

@router.post("/{tenant_id}/invite", response_model=BulkInviteResponse)
async def bulk_invite_users(
    tenant_id: str,
    invite_data: UserInvite,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Bulk invite users to tenant"""
    # Check if user has admin capability for this tenant
    if not require_capability(current_user, "tenant:invite_users", tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to invite users to tenant"
        )
    
    tenant_service = TenantService(db)
    
    try:
        results = tenant_service.bulk_invite_users(
            tenant_id=tenant_id,
            user_emails=invite_data.user_emails,
            role=invite_data.role
        )
        
        return BulkInviteResponse(**results)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{tenant_id}/statistics", response_model=Dict[str, Any])
async def get_tenant_statistics(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tenant statistics"""
    # Check if user has read capability for this tenant
    if not require_capability(current_user, "tenant:read_stats", tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view tenant statistics"
        )
    
    tenant_service = TenantService(db)
    stats = tenant_service.get_tenant_statistics(tenant_id)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return stats

@router.post("/{tenant_id}/config/{key}")
async def set_tenant_config(
    tenant_id: str,
    key: str,
    value: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Set tenant-specific configuration"""
    # Check if user has admin capability for this tenant
    if not require_capability(current_user, "tenant:configure", tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to configure tenant"
        )
    
    tenant_service = TenantService(db)
    success = tenant_service.set_tenant_config(tenant_id, key, value.get("value"))
    
    if success:
        return {"message": f"Configuration '{key}' updated successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

@router.get("/{tenant_id}/config/{key}")
async def get_tenant_config(
    tenant_id: str,
    key: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tenant-specific configuration"""
    # Check if user has read capability for this tenant
    if not require_capability(current_user, "tenant:read_config", tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to read tenant configuration"
        )
    
    tenant_service = TenantService(db)
    config_value = tenant_service.get_tenant_config(tenant_id, key)
    
    if config_value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration key not found"
        )
    
    return {"key": key, "value": config_value}

@router.post("/{from_tenant_id}/transfer/{user_id}/{to_tenant_id}")
async def transfer_user_between_tenants(
    from_tenant_id: str,
    user_id: str,
    to_tenant_id: str,
    new_role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Transfer user from one tenant to another"""
    # Check if user has admin capability for both tenants
    if not (require_capability(current_user, "tenant:manage_users", from_tenant_id) and
            require_capability(current_user, "tenant:manage_users", to_tenant_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to transfer user between tenants"
        )
    
    tenant_service = TenantService(db)
    success = tenant_service.transfer_user_between_tenants(
        user_id=user_id,
        from_tenant_id=from_tenant_id,
        to_tenant_id=to_tenant_id,
        new_role=new_role
    )
    
    if success:
        return {"message": "User transferred successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to transfer user between tenants"
        )