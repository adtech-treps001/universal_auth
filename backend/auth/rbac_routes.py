"""
RBAC API Routes

This module provides API endpoints for role-based access control
including role assignment, capability checking, and role management.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from services.rbac_service import RBACService
from auth.middleware import get_current_user, require_admin

router = APIRouter(prefix="/rbac", tags=["rbac"])

# Request/Response models
class RoleAssignmentRequest(BaseModel):
    user_id: str
    role: str
    tenant_id: str = None

class CapabilityCheckRequest(BaseModel):
    user_id: str
    capability: str
    tenant_id: str = None

class CustomRoleRequest(BaseModel):
    role_name: str
    capabilities: List[str]
    description: str = None

class RoleResponse(BaseModel):
    role: str
    capabilities: List[str]
    direct_capabilities: List[str]
    inherited_from: List[str]

class UserRolesResponse(BaseModel):
    user_id: str
    tenant_id: str = None
    roles: List[str]
    capabilities: List[str]

class CapabilityCheckResponse(BaseModel):
    user_id: str
    capability: str
    tenant_id: str = None
    has_capability: bool

# Dependency
def get_rbac_service(db: Session = Depends(get_db)) -> RBACService:
    return RBACService(db)

@router.post("/assign-role", response_model=dict)
async def assign_role(
    request: RoleAssignmentRequest,
    current_user: dict = Depends(require_admin()),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Assign role to user in tenant context
    
    Requires admin role to assign roles to other users.
    """
    try:
        success = rbac_service.assign_role(
            user_id=request.user_id,
            role=request.role,
            tenant_id=request.tenant_id
        )
        
        if success:
            return {
                "success": True,
                "message": f"Role {request.role} assigned to user {request.user_id}",
                "user_id": request.user_id,
                "role": request.role,
                "tenant_id": request.tenant_id
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to assign role")
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/remove-role")
async def remove_role(
    user_id: str,
    tenant_id: str = None,
    current_user: dict = Depends(require_admin()),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Remove user role from tenant
    
    Requires admin role to remove roles from other users.
    """
    success = rbac_service.remove_role(user_id=user_id, tenant_id=tenant_id)
    
    if success:
        return {
            "success": True,
            "message": f"Role removed from user {user_id}",
            "user_id": user_id,
            "tenant_id": tenant_id
        }
    else:
        raise HTTPException(status_code=404, detail="User role not found")

@router.get("/user-roles/{user_id}", response_model=UserRolesResponse)
async def get_user_roles(
    user_id: str,
    tenant_id: str = None,
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Get user roles and capabilities in tenant context
    
    Users can view their own roles, admins can view any user's roles.
    """
    # Check if user is viewing their own roles or is admin
    if current_user["user_id"] != user_id:
        admin_check = rbac_service.check_capability(
            current_user["user_id"], 
            "admin:users.read", 
            current_user.get("tenant_id")
        )
        if not admin_check:
            raise HTTPException(
                status_code=403, 
                detail="Insufficient permissions to view other user's roles"
            )
    
    roles = rbac_service.get_user_roles(user_id, tenant_id)
    capabilities = list(rbac_service.get_user_capabilities(user_id, tenant_id))
    
    return UserRolesResponse(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles,
        capabilities=capabilities
    )

@router.post("/check-capability", response_model=CapabilityCheckResponse)
async def check_capability(
    request: CapabilityCheckRequest,
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Check if user has specific capability
    
    Users can check their own capabilities, admins can check any user's capabilities.
    """
    # Check if user is checking their own capability or is admin
    if current_user["user_id"] != request.user_id:
        admin_check = rbac_service.check_capability(
            current_user["user_id"], 
            "admin:users.read", 
            current_user.get("tenant_id")
        )
        if not admin_check:
            raise HTTPException(
                status_code=403, 
                detail="Insufficient permissions to check other user's capabilities"
            )
    
    has_capability = rbac_service.check_capability(
        user_id=request.user_id,
        capability=request.capability,
        tenant_id=request.tenant_id
    )
    
    return CapabilityCheckResponse(
        user_id=request.user_id,
        capability=request.capability,
        tenant_id=request.tenant_id,
        has_capability=has_capability
    )

@router.get("/roles", response_model=List[str])
async def list_roles(
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    List all available roles
    
    Any authenticated user can view available roles.
    """
    return rbac_service.list_available_roles()

@router.get("/role/{role_name}", response_model=RoleResponse)
async def get_role_definition(
    role_name: str,
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Get role definition including capabilities
    
    Any authenticated user can view role definitions.
    """
    role_def = rbac_service.get_role_definition(role_name)
    
    if not role_def:
        raise HTTPException(status_code=404, detail=f"Role {role_name} not found")
    
    return RoleResponse(**role_def)

@router.post("/custom-role", response_model=dict)
async def create_custom_role(
    request: CustomRoleRequest,
    current_user: dict = Depends(require_admin()),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Create a custom role with specified capabilities
    
    Requires admin role to create custom roles.
    """
    success = rbac_service.create_custom_role(
        role_name=request.role_name,
        capabilities=request.capabilities,
        description=request.description
    )
    
    if success:
        return {
            "success": True,
            "message": f"Custom role {request.role_name} created successfully",
            "role_name": request.role_name,
            "capabilities": request.capabilities,
            "description": request.description
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail="Failed to create custom role. Role may already exist or capabilities are invalid."
        )

@router.get("/my-permissions", response_model=UserRolesResponse)
async def get_my_permissions(
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Get current user's roles and capabilities
    
    Returns the authenticated user's own permissions.
    """
    user_id = current_user["user_id"]
    tenant_id = current_user.get("tenant_id")
    
    roles = rbac_service.get_user_roles(user_id, tenant_id)
    capabilities = list(rbac_service.get_user_capabilities(user_id, tenant_id))
    
    return UserRolesResponse(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles,
        capabilities=capabilities
    )

@router.post("/validate-capability")
async def validate_capability_format(
    capability: str,
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Validate capability string format
    
    Any authenticated user can validate capability formats.
    """
    is_valid = rbac_service.validate_capability_format(capability)
    
    return {
        "capability": capability,
        "valid": is_valid,
        "message": "Valid capability format" if is_valid else "Invalid capability format"
    }