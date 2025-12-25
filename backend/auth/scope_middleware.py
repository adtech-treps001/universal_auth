"""
Scope Version Middleware

This middleware automatically checks scope versions on API requests
and invalidates sessions with outdated scopes.
"""

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from services.scope_manager import get_scope_manager
from services.session_service import SessionService
from services.rbac_service import RBACService
from jose import jwt
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ScopeVersionMiddleware(BaseHTTPMiddleware):
    """Middleware to check scope versions on authenticated requests"""
    
    def __init__(self, app, db_session_factory, secret_key: str, 
                 excluded_paths: list = None):
        super().__init__(app)
        self.db_session_factory = db_session_factory
        self.secret_key = secret_key
        self.excluded_paths = excluded_paths or [
            "/auth/login",
            "/auth/register", 
            "/auth/callback",
            "/health",
            "/docs",
            "/openapi.json"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request and check scope version if authenticated"""
        
        # Skip scope check for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # No authentication, proceed normally
            return await call_next(request)
        
        token = auth_header.split(" ")[1]
        
        # Create database session
        db = self.db_session_factory()
        try:
            # Validate token and check scope version
            scope_check_result = await self._check_scope_version(db, token)
            
            if scope_check_result["status"] == "invalid":
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "invalid_token",
                        "message": "Token is invalid or expired"
                    }
                )
            elif scope_check_result["status"] == "scope_outdated":
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "scope_outdated",
                        "message": "User permissions have changed. Please refresh your session.",
                        "current_version": scope_check_result["current_version"],
                        "token_version": scope_check_result["token_version"]
                    }
                )
            
            # Add user context to request state
            request.state.user_id = scope_check_result["user_id"]
            request.state.tenant_id = scope_check_result["tenant_id"]
            request.state.capabilities = scope_check_result["capabilities"]
            request.state.scope_version = scope_check_result["scope_version"]
            
            # Proceed with request
            response = await call_next(request)
            
            # Update session last used timestamp
            await self._update_session_activity(db, scope_check_result["session_id"])
            
            return response
            
        except Exception as e:
            logger.error(f"Error in scope middleware: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "message": "Internal server error"
                }
            )
        finally:
            db.close()
    
    async def _check_scope_version(self, db: Session, token: str) -> dict:
        """
        Check token validity and scope version
        
        Returns:
            Dictionary with status and user information
        """
        try:
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            user_id = payload.get('user_id')
            tenant_id = payload.get('tenant_id')
            token_scope_version = payload.get('scope_version', 1)
            token_capabilities = payload.get('capabilities', [])
            
            if not user_id:
                return {"status": "invalid"}
            
            # Get scope manager
            scope_manager = get_scope_manager(db)
            
            # Get current scope version
            current_scope_version = scope_manager.get_user_scope_version(user_id, tenant_id)
            
            # Check if scope version is outdated
            if token_scope_version < current_scope_version:
                return {
                    "status": "scope_outdated",
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "current_version": current_scope_version,
                    "token_version": token_scope_version
                }
            
            # Token is valid and scope is current
            return {
                "status": "valid",
                "user_id": user_id,
                "tenant_id": tenant_id,
                "capabilities": token_capabilities,
                "scope_version": token_scope_version,
                "session_id": None  # We don't have session ID from token
            }
            
        except jwt.ExpiredSignatureError:
            return {"status": "invalid"}
        except jwt.InvalidTokenError:
            return {"status": "invalid"}
        except Exception as e:
            logger.error(f"Error checking scope version: {e}")
            return {"status": "invalid"}
    
    async def _update_session_activity(self, db: Session, session_id: Optional[str]):
        """Update session last used timestamp"""
        if not session_id:
            return
        
        try:
            from models.user import Session as SessionModel
            from datetime import datetime
            
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if session:
                session.last_used = datetime.utcnow()
                session.last_scope_check = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")

class CapabilityRequiredMiddleware(BaseHTTPMiddleware):
    """Middleware to check required capabilities for protected endpoints"""
    
    def __init__(self, app, capability_map: dict = None):
        super().__init__(app)
        self.capability_map = capability_map or {}
    
    async def dispatch(self, request: Request, call_next):
        """Check if user has required capability for endpoint"""
        
        # Get required capability for this endpoint
        endpoint_key = f"{request.method}:{request.url.path}"
        required_capability = self.capability_map.get(endpoint_key)
        
        if not required_capability:
            # No capability requirement, proceed
            return await call_next(request)
        
        # Check if user context is available (set by ScopeVersionMiddleware)
        if not hasattr(request.state, 'capabilities'):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "authentication_required",
                    "message": "Authentication required for this endpoint"
                }
            )
        
        user_capabilities = set(request.state.capabilities)
        
        # Check capability
        if not self._has_capability(user_capabilities, required_capability):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "insufficient_permissions",
                    "message": f"Required capability: {required_capability}",
                    "user_capabilities": list(user_capabilities)
                }
            )
        
        return await call_next(request)
    
    def _has_capability(self, user_capabilities: set, required_capability: str) -> bool:
        """Check if user capabilities include required capability"""
        # Admin wildcard grants all capabilities
        if '*' in user_capabilities:
            return True
        
        # Direct capability match
        if required_capability in user_capabilities:
            return True
        
        # Check for pattern matches (e.g., "app:*" matches "app:login")
        for cap in user_capabilities:
            if cap.endswith('*'):
                prefix = cap[:-1]
                if required_capability.startswith(prefix):
                    return True
        
        return False

def create_scope_middleware(app, db_session_factory, secret_key: str, 
                          excluded_paths: list = None):
    """Factory function to create and configure scope middleware"""
    return ScopeVersionMiddleware(
        app=app,
        db_session_factory=db_session_factory,
        secret_key=secret_key,
        excluded_paths=excluded_paths
    )

def create_capability_middleware(app, capability_map: dict = None):
    """Factory function to create and configure capability middleware"""
    return CapabilityRequiredMiddleware(
        app=app,
        capability_map=capability_map
    )