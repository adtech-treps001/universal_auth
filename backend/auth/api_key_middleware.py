"""
API Key Validation Middleware

Middleware for automatic API key validation on protected endpoints.
"""

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List, Callable
import logging
import re
from datetime import datetime

from database import get_db
from services.api_key_validation import APIKeyValidationService
from auth.middleware import get_current_user
from models.user import User

logger = logging.getLogger(__name__)

class APIKeyMiddleware:
    """Middleware for API key validation"""
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
        self.protected_patterns = [
            r'^/api/ai/.*',  # AI endpoints
            r'^/api/models/.*',  # Model endpoints
            r'^/api/completions/.*',  # Completion endpoints
            r'^/api/embeddings/.*',  # Embedding endpoints
        ]
    
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        """Validate API key for protected endpoints"""
        
        # Check if endpoint requires API key validation
        if not self._requires_api_key_validation(request.url.path):
            return
        
        # Extract API key from headers
        api_key_id = self._extract_api_key_id(request, credentials)
        if not api_key_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required for this endpoint"
            )
        
        # Validate API key
        validation_service = APIKeyValidationService(db)
        
        # Build request context
        request_context = self._build_request_context(request, current_user)
        
        # Perform validation
        result = validation_service.validate_api_key(
            key_id=api_key_id,
            user_id=current_user.id,
            request_context=request_context
        )
        
        if not result['valid']:
            # Log failed validation
            validation_service.log_validation_attempt(
                key_id=api_key_id,
                user_id=current_user.id,
                success=False,
                reason=result['message'],
                request_context=request_context
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=result['message']
            )
        
        # Add validation result to request state
        request.state.api_key_validation = result
        request.state.api_key_id = api_key_id
        
        # Log successful validation
        validation_service.log_validation_attempt(
            key_id=api_key_id,
            user_id=current_user.id,
            success=True,
            request_context=request_context
        )
    
    def _requires_api_key_validation(self, path: str) -> bool:
        """Check if path requires API key validation"""
        for pattern in self.protected_patterns:
            if re.match(pattern, path):
                return True
        return False
    
    def _extract_api_key_id(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials]
    ) -> Optional[str]:
        """Extract API key ID from request"""
        
        # Try X-API-Key header first
        api_key_id = request.headers.get('X-API-Key')
        if api_key_id:
            return api_key_id
        
        # Try Authorization header with Bearer token
        if credentials and credentials.scheme.lower() == 'bearer':
            # Assume the token is the API key ID
            return credentials.credentials
        
        # Try query parameter
        api_key_id = request.query_params.get('api_key')
        if api_key_id:
            return api_key_id
        
        return None
    
    def _build_request_context(self, request: Request, current_user: User) -> Dict[str, Any]:
        """Build request context for validation"""
        
        # Extract scopes from request
        scopes = self._extract_required_scopes(request)
        
        # Extract model from request
        model = self._extract_model_name(request)
        
        # Estimate token usage (basic estimation)
        estimated_tokens = self._estimate_token_usage(request)
        
        return {
            'client_ip': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent'),
            'session_id': getattr(current_user, 'session_id', None),
            'endpoint': request.url.path,
            'method': request.method,
            'scopes': scopes,
            'model': model,
            'estimated_tokens': estimated_tokens
        }
    
    def _extract_required_scopes(self, request: Request) -> List[str]:
        """Extract required scopes based on endpoint"""
        
        path = request.url.path
        method = request.method.upper()
        
        # Map endpoints to required scopes
        scope_mappings = {
            r'^/api/ai/chat/completions': ['chat.completions'],
            r'^/api/ai/completions': ['completions'],
            r'^/api/ai/embeddings': ['embeddings'],
            r'^/api/ai/images': ['images'],
            r'^/api/ai/audio': ['audio'],
            r'^/api/models': ['models'],
            r'^/api/files': ['files'],
            r'^/api/fine-tuning': ['fine_tuning'],
            r'^/api/moderations': ['moderations']
        }
        
        for pattern, scopes in scope_mappings.items():
            if re.match(pattern, path):
                return scopes
        
        # Default scope based on method
        if method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return ['write']
        else:
            return ['read']
    
    def _extract_model_name(self, request: Request) -> Optional[str]:
        """Extract model name from request"""
        
        # Try query parameter
        model = request.query_params.get('model')
        if model:
            return model
        
        # Try to extract from request body (for POST requests)
        if request.method.upper() == 'POST':
            # This would require parsing the request body
            # For now, return None and let the actual endpoint handle it
            pass
        
        return None
    
    def _estimate_token_usage(self, request: Request) -> Optional[int]:
        """Estimate token usage for rate limiting"""
        
        # Basic estimation based on content length
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                # Rough estimation: 1 token per 4 characters
                return int(content_length) // 4
            except ValueError:
                pass
        
        # Default estimation for different endpoints
        path = request.url.path
        if '/chat/completions' in path:
            return 100  # Default for chat completions
        elif '/completions' in path:
            return 50   # Default for text completions
        elif '/embeddings' in path:
            return 10   # Default for embeddings
        
        return None

class APIKeyDependency:
    """Dependency for API key validation in specific endpoints"""
    
    def __init__(self, required_scopes: List[str] = None, required_model: str = None):
        self.required_scopes = required_scopes or []
        self.required_model = required_model
    
    async def __call__(
        self,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Validate API key with specific requirements"""
        
        # Extract API key ID
        api_key_id = self._extract_api_key_id(request)
        if not api_key_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        # Build request context
        request_context = {
            'client_ip': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent'),
            'session_id': getattr(current_user, 'session_id', None),
            'endpoint': request.url.path,
            'method': request.method,
            'scopes': self.required_scopes,
            'model': self.required_model
        }
        
        # Validate API key
        validation_service = APIKeyValidationService(db)
        result = validation_service.validate_api_key(
            key_id=api_key_id,
            user_id=current_user.id,
            request_context=request_context
        )
        
        if not result['valid']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=result['message']
            )
        
        return result
    
    def _extract_api_key_id(self, request: Request) -> Optional[str]:
        """Extract API key ID from request"""
        
        # Try X-API-Key header
        api_key_id = request.headers.get('X-API-Key')
        if api_key_id:
            return api_key_id
        
        # Try Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Try query parameter
        return request.query_params.get('api_key')

# Convenience functions for common use cases
def require_api_key(scopes: List[str] = None, model: str = None):
    """Decorator for requiring API key validation"""
    return Depends(APIKeyDependency(required_scopes=scopes, required_model=model))

def require_chat_api_key():
    """Require API key with chat completion access"""
    return require_api_key(scopes=['chat.completions'])

def require_embedding_api_key():
    """Require API key with embedding access"""
    return require_api_key(scopes=['embeddings'])

def require_image_api_key():
    """Require API key with image generation access"""
    return require_api_key(scopes=['images'])

def require_model_api_key(model_name: str):
    """Require API key with access to specific model"""
    return require_api_key(model=model_name)

# Rate limiting decorator
class RateLimitDependency:
    """Dependency for rate limiting checks"""
    
    def __init__(self, requests_per_minute: int = None, tokens_per_minute: int = None):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
    
    async def __call__(
        self,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        """Check rate limits"""
        
        # Extract API key ID
        api_key_id = request.headers.get('X-API-Key')
        if not api_key_id:
            return  # No API key, skip rate limiting
        
        # Build request context
        request_context = {
            'client_ip': request.client.host if request.client else None,
            'endpoint': request.url.path,
            'method': request.method
        }
        
        # Check rate limits
        validation_service = APIKeyValidationService(db)
        result = validation_service.check_rate_limit(
            key_id=api_key_id,
            request_context=request_context
        )
        
        if not result['allowed']:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=result['reason'],
                headers={
                    'X-RateLimit-Limit': str(result.get('limit', 0)),
                    'X-RateLimit-Remaining': str(result.get('remaining_requests', 0)),
                    'X-RateLimit-Reset': str(result.get('reset_time', 0))
                }
            )

def rate_limit(requests_per_minute: int = None, tokens_per_minute: int = None):
    """Decorator for rate limiting"""
    return Depends(RateLimitDependency(requests_per_minute, tokens_per_minute))