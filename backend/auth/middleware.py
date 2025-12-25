"""
Authorization Middleware

This module provides middleware for checking user capabilities and
enforcing role-based access control on API endpoints.
"""

from typing import Optional, List, Callable, Any
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from services.rbac_service import RBACService
from database import get_db
from jose import jwt
import os

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = "HS256"

security = HTTPBearer()

class AuthorizationMiddleware:
    """Middleware for authorization checks"""
    
    def __init__(self, db: Session):
        self.rbac_service = RBACService(db)
    
    def decode_token(self, token: str) -> dict:
        """
        Decode JWT token and extract user information
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload dictionary
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
        """
        Get current user from JWT token
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            User information dictionary
        """
        token = credentials.credentials
        payload = self.decode_token(token)
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        return {
            "user_id": user_id,
            "tenant_id": payload.get("tenant_id"),
            "email": payload.get("email"),
            "roles": payload.get("roles", [])
        }
    
    def require_capability(self, capability: str, tenant_specific: bool = True):
        """
        Decorator to require specific capability for endpoint access
        
        Args:
            capability: Required capability string
            tenant_specific: Whether to check tenant-specific capabilities
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Get current user from request context
                request = kwargs.get('request') or args[0] if args else None
                if not request or not hasattr(request.state, 'user'):
                    raise HTTPException(status_code=401, detail="Authentication required")
                
                user = request.state.user
                user_id = user["user_id"]
                tenant_id = user["tenant_id"] if tenant_specific else None
                
                # Check capability
                if not self.rbac_service.check_capability(user_id, capability, tenant_id):
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Insufficient permissions. Required capability: {capability}"
                    )
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def require_role(self, role: str, tenant_specific: bool = True):
        """
        Decorator to require specific role for endpoint access
        
        Args:
            role: Required role name
            tenant_specific: Whether to check tenant-specific roles
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Get current user from request context
                request = kwargs.get('request') or args[0] if args else None
                if not request or not hasattr(request.state, 'user'):
                    raise HTTPException(status_code=401, detail="Authentication required")
                
                user = request.state.user
                user_id = user["user_id"]
                tenant_id = user["tenant_id"] if tenant_specific else None
                
                # Check role
                user_roles = self.rbac_service.get_user_roles(user_id, tenant_id)
                if role not in user_roles:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Insufficient permissions. Required role: {role}"
                    )
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def require_admin(self, tenant_specific: bool = True):
        """
        Decorator to require admin role for endpoint access
        
        Args:
            tenant_specific: Whether to check tenant-specific admin role
            
        Returns:
            Decorator function
        """
        return self.require_role("admin", tenant_specific)

# Dependency functions for FastAPI
def get_rbac_service(db: Session = Depends(get_db)) -> RBACService:
    """Get RBAC service instance"""
    return RBACService(db)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """Get current authenticated user"""
    middleware = AuthorizationMiddleware(db)
    return middleware.get_current_user(credentials)

def require_capability(capability: str, tenant_specific: bool = True):
    """
    FastAPI dependency to require specific capability
    
    Args:
        capability: Required capability string
        tenant_specific: Whether to check tenant-specific capabilities
        
    Returns:
        Dependency function
    """
    def dependency(
        current_user: dict = Depends(get_current_user),
        rbac_service: RBACService = Depends(get_rbac_service)
    ):
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"] if tenant_specific else None
        
        if not rbac_service.check_capability(user_id, capability, tenant_id):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required capability: {capability}"
            )
        
        return current_user
    
    return dependency

def require_role(role: str, tenant_specific: bool = True):
    """
    FastAPI dependency to require specific role
    
    Args:
        role: Required role name
        tenant_specific: Whether to check tenant-specific roles
        
    Returns:
        Dependency function
    """
    def dependency(
        current_user: dict = Depends(get_current_user),
        rbac_service: RBACService = Depends(get_rbac_service)
    ):
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"] if tenant_specific else None
        
        user_roles = rbac_service.get_user_roles(user_id, tenant_id)
        if role not in user_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {role}"
            )
        
        return current_user
    
    return dependency

def require_admin(tenant_specific: bool = True):
    """
    FastAPI dependency to require admin role
    
    Args:
        tenant_specific: Whether to check tenant-specific admin role
        
    Returns:
        Dependency function
    """
    return require_role("admin", tenant_specific)

# Backward compatibility alias
require_permission = require_capability

# Capability checking functions
def check_user_capability(
    user_id: str,
    capability: str,
    tenant_id: str = None,
    rbac_service: RBACService = None,
    db: Session = None
) -> bool:
    """
    Check if user has specific capability
    
    Args:
        user_id: User ID
        capability: Required capability
        tenant_id: Tenant ID (optional)
        rbac_service: RBAC service instance (optional)
        db: Database session (optional)
        
    Returns:
        True if user has capability
    """
    if not rbac_service:
        if not db:
            raise ValueError("Either rbac_service or db must be provided")
        rbac_service = RBACService(db)
    
    return rbac_service.check_capability(user_id, capability, tenant_id)

def check_user_role(
    user_id: str,
    role: str,
    tenant_id: str = None,
    rbac_service: RBACService = None,
    db: Session = None
) -> bool:
    """
    Check if user has specific role
    
    Args:
        user_id: User ID
        role: Required role
        tenant_id: Tenant ID (optional)
        rbac_service: RBAC service instance (optional)
        db: Database session (optional)
        
    Returns:
        True if user has role
    """
    if not rbac_service:
        if not db:
            raise ValueError("Either rbac_service or db must be provided")
        rbac_service = RBACService(db)
    
    user_roles = rbac_service.get_user_roles(user_id, tenant_id)
    return role in user_roles