"""
OPA Middleware

This module provides middleware for integrating OPA policy evaluation
with FastAPI routes and authorization decisions.
"""

import asyncio
from typing import Optional, Dict, Any, List
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from services.opa_service import OPAService, PolicyInput, PolicyDecision, get_opa_service
from services.rbac_service import RBACService
from auth.middleware import get_current_user
from database import get_db
import logging

logger = logging.getLogger(__name__)

class OPAMiddleware:
    """Middleware for OPA policy evaluation"""
    
    def __init__(self, opa_service: OPAService, db: Session):
        self.opa_service = opa_service
        self.rbac_service = RBACService(db)
    
    async def evaluate_authorization(
        self, 
        user: Dict[str, Any], 
        request: Request,
        required_capability: Optional[str] = None
    ) -> PolicyDecision:
        """
        Evaluate authorization policy for a request
        
        Args:
            user: Current user context
            request: FastAPI request object
            required_capability: Optional specific capability to check
            
        Returns:
            PolicyDecision with authorization result
        """
        # Get user capabilities from RBAC service
        user_id = user["user_id"]
        tenant_id = user.get("tenant_id")
        
        capabilities = self.rbac_service.get_user_capabilities(user_id, tenant_id)
        tenant_memberships = {}
        
        if tenant_id:
            # Get tenant membership details
            membership = self.rbac_service.get_tenant_membership(user_id, tenant_id)
            if membership:
                tenant_memberships[tenant_id] = {
                    "role": membership.role,
                    "is_active": membership.is_active,
                    "capabilities": membership.capabilities or []
                }
        
        # Create policy input
        policy_input = PolicyInput(
            user={
                "user_id": user_id,
                "email": user.get("email"),
                "capabilities": capabilities,
                "tenant_memberships": tenant_memberships
            },
            method=request.method,
            path=request.url.path,
            tenant_id=tenant_id,
            required_capability=required_capability
        )
        
        # Evaluate authorization policy
        return await self.opa_service.check_authorization(policy_input)
    
    async def evaluate_api_access(
        self, 
        user: Dict[str, Any], 
        request: Request,
        rate_limit: Optional[Dict[str, Any]] = None
    ) -> PolicyDecision:
        """
        Evaluate API access policy for a request
        
        Args:
            user: Current user context
            request: FastAPI request object
            rate_limit: Optional rate limiting data
            
        Returns:
            PolicyDecision with API access result
        """
        # Get user capabilities
        user_id = user["user_id"]
        tenant_id = user.get("tenant_id")
        capabilities = self.rbac_service.get_user_capabilities(user_id, tenant_id)
        
        user_data = {
            "user_id": user_id,
            "email": user.get("email"),
            "capabilities": capabilities
        }
        
        return await self.opa_service.check_api_access(
            user_data, 
            request.method, 
            request.url.path,
            rate_limit
        )
    
    async def evaluate_tenant_access(
        self, 
        user: Dict[str, Any], 
        tenant_id: str
    ) -> PolicyDecision:
        """
        Evaluate tenant access policy
        
        Args:
            user: Current user context
            tenant_id: Tenant ID to check access for
            
        Returns:
            PolicyDecision with tenant access result
        """
        # Get user capabilities and tenant memberships
        user_id = user["user_id"]
        capabilities = self.rbac_service.get_user_capabilities(user_id)
        
        tenant_memberships = {}
        membership = self.rbac_service.get_tenant_membership(user_id, tenant_id)
        if membership:
            tenant_memberships[tenant_id] = {
                "role": membership.role,
                "is_active": membership.is_active,
                "capabilities": membership.capabilities or []
            }
        
        user_data = {
            "user_id": user_id,
            "email": user.get("email"),
            "capabilities": capabilities,
            "tenant_memberships": tenant_memberships
        }
        
        return await self.opa_service.check_tenant_access(user_data, tenant_id)
    
    async def evaluate_ui_visibility(
        self, 
        user: Dict[str, Any], 
        ui_component: str
    ) -> PolicyDecision:
        """
        Evaluate UI component visibility policy
        
        Args:
            user: Current user context
            ui_component: UI component identifier
            
        Returns:
            PolicyDecision with UI visibility result
        """
        # Get user capabilities
        user_id = user["user_id"]
        tenant_id = user.get("tenant_id")
        capabilities = self.rbac_service.get_user_capabilities(user_id, tenant_id)
        
        user_data = {
            "user_id": user_id,
            "email": user.get("email"),
            "capabilities": capabilities
        }
        
        return await self.opa_service.check_ui_visibility(user_data, ui_component)
    
    async def evaluate_resource_access(
        self, 
        user: Dict[str, Any], 
        resource: str, 
        action: str,
        tenant_id: Optional[str] = None
    ) -> PolicyDecision:
        """
        Evaluate resource access policy
        
        Args:
            user: Current user context
            resource: Resource identifier
            action: Action to perform on resource
            tenant_id: Optional tenant context
            
        Returns:
            PolicyDecision with resource access result
        """
        # Get user capabilities
        user_id = user["user_id"]
        if not tenant_id:
            tenant_id = user.get("tenant_id")
        
        capabilities = self.rbac_service.get_user_capabilities(user_id, tenant_id)
        
        user_data = {
            "user_id": user_id,
            "email": user.get("email"),
            "capabilities": capabilities
        }
        
        return await self.opa_service.check_resource_access(
            user_data, resource, action, tenant_id
        )

# FastAPI dependencies
async def get_opa_middleware(
    opa_service: OPAService = Depends(get_opa_service),
    db: Session = Depends(get_db)
) -> OPAMiddleware:
    """Get OPA middleware instance"""
    return OPAMiddleware(opa_service, db)

def require_opa_authorization(required_capability: Optional[str] = None):
    """
    FastAPI dependency to require OPA authorization
    
    Args:
        required_capability: Optional specific capability to check
        
    Returns:
        Dependency function
    """
    async def dependency(
        request: Request,
        current_user: dict = Depends(get_current_user),
        opa_middleware: OPAMiddleware = Depends(get_opa_middleware)
    ):
        decision = await opa_middleware.evaluate_authorization(
            current_user, request, required_capability
        )
        
        if not decision.allow:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: {decision.reason or 'Insufficient permissions'}"
            )
        
        return current_user
    
    return dependency

def require_opa_api_access(rate_limit: Optional[Dict[str, Any]] = None):
    """
    FastAPI dependency to require OPA API access authorization
    
    Args:
        rate_limit: Optional rate limiting data
        
    Returns:
        Dependency function
    """
    async def dependency(
        request: Request,
        current_user: dict = Depends(get_current_user),
        opa_middleware: OPAMiddleware = Depends(get_opa_middleware)
    ):
        decision = await opa_middleware.evaluate_api_access(
            current_user, request, rate_limit
        )
        
        if not decision.allow:
            raise HTTPException(
                status_code=403,
                detail=f"API access denied: {decision.reason or 'Insufficient permissions'}"
            )
        
        return current_user
    
    return dependency

def require_opa_tenant_access(tenant_id: str):
    """
    FastAPI dependency to require OPA tenant access authorization
    
    Args:
        tenant_id: Tenant ID to check access for
        
    Returns:
        Dependency function
    """
    async def dependency(
        current_user: dict = Depends(get_current_user),
        opa_middleware: OPAMiddleware = Depends(get_opa_middleware)
    ):
        decision = await opa_middleware.evaluate_tenant_access(current_user, tenant_id)
        
        if not decision.allow:
            raise HTTPException(
                status_code=403,
                detail=f"Tenant access denied: {decision.reason or 'Insufficient permissions'}"
            )
        
        return current_user
    
    return dependency

# Utility functions
async def check_opa_authorization(
    user: Dict[str, Any],
    request: Request,
    required_capability: Optional[str] = None,
    opa_service: Optional[OPAService] = None,
    db: Optional[Session] = None
) -> PolicyDecision:
    """
    Check OPA authorization for a user and request
    
    Args:
        user: User context
        request: FastAPI request object
        required_capability: Optional specific capability to check
        opa_service: Optional OPA service instance
        db: Optional database session
        
    Returns:
        PolicyDecision with authorization result
    """
    if not opa_service:
        opa_service = await get_opa_service()
    
    if not db:
        # This would need to be handled differently in a real application
        # For now, we'll raise an error
        raise ValueError("Database session required for OPA authorization check")
    
    middleware = OPAMiddleware(opa_service, db)
    return await middleware.evaluate_authorization(user, request, required_capability)

async def check_opa_ui_visibility(
    user: Dict[str, Any],
    ui_component: str,
    opa_service: Optional[OPAService] = None,
    db: Optional[Session] = None
) -> PolicyDecision:
    """
    Check OPA UI visibility for a user and component
    
    Args:
        user: User context
        ui_component: UI component identifier
        opa_service: Optional OPA service instance
        db: Optional database session
        
    Returns:
        PolicyDecision with UI visibility result
    """
    if not opa_service:
        opa_service = await get_opa_service()
    
    if not db:
        raise ValueError("Database session required for OPA UI visibility check")
    
    middleware = OPAMiddleware(opa_service, db)
    return await middleware.evaluate_ui_visibility(user, ui_component)