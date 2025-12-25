"""
JWT Token Management Service

This module provides comprehensive JWT token management including generation,
validation, refresh, and stateless authentication capabilities.

**Implements: Requirements 8.1, 8.2, 8.4**
"""

from jose import jwt
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import os
import json
import redis
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TokenConfig:
    """JWT token configuration"""
    secret_key: str
    algorithm: str = 'HS256'
    access_token_expiry_hours: int = 24
    refresh_token_expiry_days: int = 30
    issuer: str = 'universal-auth'
    audience: List[str] = None
    
    def __post_init__(self):
        if self.audience is None:
            self.audience = ['web', 'mobile', 'api']

class JWTService:
    """JWT token management service"""
    
    def __init__(self, config: TokenConfig, redis_client: Optional[redis.Redis] = None):
        self.config = config
        self.redis_client = redis_client
        
        # Validate configuration
        self._validate_config()
        
        # Initialize key pair for RS256 if needed
        if config.algorithm.startswith('RS'):
            self._initialize_rsa_keys()
    
    def _validate_config(self):
        """Validate JWT configuration"""
        if not self.config.secret_key:
            raise ValueError("JWT secret key is required")
        
        if len(self.config.secret_key) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")
        
        if self.config.algorithm not in ['HS256', 'HS512', 'RS256', 'RS512']:
            raise ValueError(f"Unsupported JWT algorithm: {self.config.algorithm}")
    
    def _initialize_rsa_keys(self):
        """Initialize RSA key pair for RS256/RS512 algorithms"""
        # In production, these should be loaded from secure storage
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        self.private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        self.public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def generate_access_token(self, user_id: str, email: str, roles: List[str], 
                            scopes: List[str], tenant_id: Optional[str] = None,
                            audience: str = 'web', additional_claims: Dict[str, Any] = None) -> str:
        """
        Generate JWT access token
        
        Args:
            user_id: User identifier
            email: User email
            roles: User roles
            scopes: User scopes/permissions
            tenant_id: Tenant identifier (optional)
            audience: Token audience
            additional_claims: Additional claims to include
            
        Returns:
            Encoded JWT access token
        """
        current_time = int(time.time())
        expiry_time = current_time + (self.config.access_token_expiry_hours * 3600)
        
        # Build token payload
        payload = {
            'user_id': user_id,
            'email': email,
            'roles': roles,
            'scopes': scopes,
            'tenant_id': tenant_id,
            'aud': audience,
            'iss': self.config.issuer,
            'iat': current_time,
            'exp': expiry_time,
            'token_type': 'access'
        }
        
        # Add additional claims
        if additional_claims:
            payload.update(additional_claims)
        
        # Generate token
        signing_key = self._get_signing_key()
        token = jwt.encode(payload, signing_key, algorithm=self.config.algorithm)
        
        # Store token metadata in Redis if available
        if self.redis_client:
            self._store_token_metadata(token, payload)
        
        logger.info(f"Generated access token for user {user_id}")
        return token
    
    def generate_refresh_token(self, user_id: str, access_token_jti: str) -> str:
        """
        Generate JWT refresh token
        
        Args:
            user_id: User identifier
            access_token_jti: JTI of the associated access token
            
        Returns:
            Encoded JWT refresh token
        """
        current_time = int(time.time())
        expiry_time = current_time + (self.config.refresh_token_expiry_days * 24 * 3600)
        
        payload = {
            'user_id': user_id,
            'access_token_jti': access_token_jti,
            'iss': self.config.issuer,
            'iat': current_time,
            'exp': expiry_time,
            'token_type': 'refresh'
        }
        
        signing_key = self._get_signing_key()
        token = jwt.encode(payload, signing_key, algorithm=self.config.algorithm)
        
        # Store refresh token in Redis
        if self.redis_client:
            self._store_refresh_token(token, payload)
        
        logger.info(f"Generated refresh token for user {user_id}")
        return token
    
    def validate_token(self, token: str, expected_audience: str = None) -> Dict[str, Any]:
        """
        Validate JWT token
        
        Args:
            token: JWT token to validate
            expected_audience: Expected audience for validation
            
        Returns:
            Validation result with payload or error
        """
        try:
            # Decode token
            verification_key = self._get_verification_key()
            
            decode_options = {
                'verify_signature': True,
                'verify_exp': True,
                'verify_iat': True,
                'verify_iss': True,
                'verify_aud': True if expected_audience else False
            }
            
            payload = jwt.decode(
                token,
                verification_key,
                algorithms=[self.config.algorithm],
                issuer=self.config.issuer,
                audience=expected_audience,
                options=decode_options
            )
            
            # Additional validation
            validation_result = self._validate_token_payload(payload, token)
            if not validation_result['valid']:
                return validation_result
            
            # Check if token is blacklisted
            if self.redis_client and self._is_token_blacklisted(token):
                return {
                    'valid': False,
                    'error': 'Token has been revoked',
                    'payload': None
                }
            
            logger.debug(f"Successfully validated token for user {payload.get('user_id')}")
            return {
                'valid': True,
                'error': None,
                'payload': payload
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token validation failed: expired signature")
            return {
                'valid': False,
                'error': 'Token has expired',
                'payload': None
            }
        except jwt.InvalidIssuerError:
            logger.warning("Token validation failed: invalid issuer")
            return {
                'valid': False,
                'error': 'Invalid token issuer',
                'payload': None
            }
        except jwt.InvalidAudienceError:
            logger.warning("Token validation failed: invalid audience")
            return {
                'valid': False,
                'error': 'Invalid token audience',
                'payload': None
            }
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token validation failed: {str(e)}")
            return {
                'valid': False,
                'error': f'Invalid token: {str(e)}',
                'payload': None
            }
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return {
                'valid': False,
                'error': f'Token validation error: {str(e)}',
                'payload': None
            }
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token or error
        """
        # Validate refresh token
        validation_result = self.validate_token(refresh_token)
        
        if not validation_result['valid']:
            return {
                'success': False,
                'error': validation_result['error'],
                'access_token': None,
                'refresh_token': None
            }
        
        payload = validation_result['payload']
        
        # Verify it's a refresh token
        if payload.get('token_type') != 'refresh':
            return {
                'success': False,
                'error': 'Invalid token type for refresh',
                'access_token': None,
                'refresh_token': None
            }
        
        user_id = payload['user_id']
        
        # Get user information for new token (this would typically query the database)
        user_info = self._get_user_info_for_refresh(user_id)
        if not user_info:
            return {
                'success': False,
                'error': 'User not found or inactive',
                'access_token': None,
                'refresh_token': None
            }
        
        try:
            # Generate new access token
            new_access_token = self.generate_access_token(
                user_id=user_info['user_id'],
                email=user_info['email'],
                roles=user_info['roles'],
                scopes=user_info['scopes'],
                tenant_id=user_info.get('tenant_id'),
                audience=user_info.get('audience', 'web')
            )
            
            # Generate new refresh token
            new_refresh_token = self.generate_refresh_token(user_id, self._extract_jti(new_access_token))
            
            # Blacklist old refresh token
            if self.redis_client:
                self._blacklist_token(refresh_token)
            
            logger.info(f"Successfully refreshed tokens for user {user_id}")
            return {
                'success': True,
                'error': None,
                'access_token': new_access_token,
                'refresh_token': new_refresh_token
            }
            
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return {
                'success': False,
                'error': f'Token refresh failed: {str(e)}',
                'access_token': None,
                'refresh_token': None
            }
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke/blacklist a token
        
        Args:
            token: Token to revoke
            
        Returns:
            True if successfully revoked
        """
        if not self.redis_client:
            logger.warning("Cannot revoke token: Redis not available")
            return False
        
        try:
            # Validate token to get expiry
            validation_result = self.validate_token(token)
            if validation_result['valid']:
                payload = validation_result['payload']
                exp = payload.get('exp')
                
                # Blacklist token until its natural expiry
                if exp:
                    ttl = exp - int(time.time())
                    if ttl > 0:
                        self._blacklist_token(token, ttl)
                        logger.info(f"Token revoked for user {payload.get('user_id')}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Token revocation error: {str(e)}")
            return False
    
    def revoke_all_user_tokens(self, user_id: str) -> bool:
        """
        Revoke all tokens for a specific user
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successfully revoked
        """
        if not self.redis_client:
            logger.warning("Cannot revoke user tokens: Redis not available")
            return False
        
        try:
            # Set user token revocation timestamp
            revocation_key = f"user_token_revocation:{user_id}"
            current_time = int(time.time())
            
            # Set with expiry equal to max token lifetime
            max_expiry = max(
                self.config.access_token_expiry_hours * 3600,
                self.config.refresh_token_expiry_days * 24 * 3600
            )
            
            self.redis_client.setex(revocation_key, max_expiry, current_time)
            logger.info(f"Revoked all tokens for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"User token revocation error: {str(e)}")
            return False
    
    def extract_user_info(self, token: str) -> Dict[str, Any]:
        """
        Extract user information from token
        
        Args:
            token: JWT token
            
        Returns:
            User information or error
        """
        validation_result = self.validate_token(token)
        
        if not validation_result['valid']:
            return {
                'success': False,
                'error': validation_result['error'],
                'user_info': None
            }
        
        payload = validation_result['payload']
        
        user_info = {
            'user_id': payload.get('user_id'),
            'email': payload.get('email'),
            'roles': payload.get('roles', []),
            'scopes': payload.get('scopes', []),
            'tenant_id': payload.get('tenant_id'),
            'audience': payload.get('aud'),
            'issued_at': payload.get('iat'),
            'expires_at': payload.get('exp'),
            'token_type': payload.get('token_type', 'access')
        }
        
        return {
            'success': True,
            'error': None,
            'user_info': user_info
        }
    
    def check_permissions(self, token: str, required_scopes: List[str]) -> bool:
        """
        Check if token has required permissions
        
        Args:
            token: JWT token
            required_scopes: Required scopes
            
        Returns:
            True if token has all required scopes
        """
        user_info_result = self.extract_user_info(token)
        
        if not user_info_result['success']:
            return False
        
        user_scopes = user_info_result['user_info'].get('scopes', [])
        required_scopes_set = set(required_scopes)
        user_scopes_set = set(user_scopes)
        
        return required_scopes_set.issubset(user_scopes_set)
    
    def _get_signing_key(self) -> Union[str, bytes]:
        """Get signing key based on algorithm"""
        if self.config.algorithm.startswith('HS'):
            return self.config.secret_key
        elif self.config.algorithm.startswith('RS'):
            return self.private_key
        else:
            raise ValueError(f"Unsupported algorithm: {self.config.algorithm}")
    
    def _get_verification_key(self) -> Union[str, bytes]:
        """Get verification key based on algorithm"""
        if self.config.algorithm.startswith('HS'):
            return self.config.secret_key
        elif self.config.algorithm.startswith('RS'):
            return self.public_key
        else:
            raise ValueError(f"Unsupported algorithm: {self.config.algorithm}")
    
    def _validate_token_payload(self, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Additional payload validation"""
        errors = []
        
        # Check required claims
        required_claims = ['user_id', 'iss', 'iat', 'exp']
        for claim in required_claims:
            if claim not in payload:
                errors.append(f"Missing required claim: {claim}")
        
        # Check user token revocation
        if self.redis_client and 'user_id' in payload:
            user_id = payload['user_id']
            revocation_key = f"user_token_revocation:{user_id}"
            revocation_time = self.redis_client.get(revocation_key)
            
            if revocation_time:
                revocation_timestamp = int(revocation_time)
                token_issued_at = payload.get('iat', 0)
                
                if token_issued_at < revocation_timestamp:
                    errors.append("Token was issued before user token revocation")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _store_token_metadata(self, token: str, payload: Dict[str, Any]):
        """Store token metadata in Redis"""
        try:
            token_key = f"token_metadata:{self._get_token_hash(token)}"
            metadata = {
                'user_id': payload.get('user_id'),
                'issued_at': payload.get('iat'),
                'expires_at': payload.get('exp'),
                'token_type': payload.get('token_type', 'access')
            }
            
            ttl = payload.get('exp', 0) - int(time.time())
            if ttl > 0:
                self.redis_client.setex(token_key, ttl, json.dumps(metadata))
                
        except Exception as e:
            logger.warning(f"Failed to store token metadata: {str(e)}")
    
    def _store_refresh_token(self, token: str, payload: Dict[str, Any]):
        """Store refresh token in Redis"""
        try:
            refresh_key = f"refresh_token:{payload['user_id']}"
            token_data = {
                'token_hash': self._get_token_hash(token),
                'expires_at': payload.get('exp')
            }
            
            ttl = payload.get('exp', 0) - int(time.time())
            if ttl > 0:
                self.redis_client.setex(refresh_key, ttl, json.dumps(token_data))
                
        except Exception as e:
            logger.warning(f"Failed to store refresh token: {str(e)}")
    
    def _blacklist_token(self, token: str, ttl: int = None):
        """Blacklist a token"""
        try:
            blacklist_key = f"blacklisted_token:{self._get_token_hash(token)}"
            
            if ttl is None:
                # Default TTL based on token type
                ttl = self.config.access_token_expiry_hours * 3600
            
            self.redis_client.setex(blacklist_key, ttl, "1")
            
        except Exception as e:
            logger.warning(f"Failed to blacklist token: {str(e)}")
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        try:
            blacklist_key = f"blacklisted_token:{self._get_token_hash(token)}"
            return self.redis_client.exists(blacklist_key)
        except Exception as e:
            logger.warning(f"Failed to check token blacklist: {str(e)}")
            return False
    
    def _get_token_hash(self, token: str) -> str:
        """Get hash of token for storage keys"""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    def _extract_jti(self, token: str) -> str:
        """Extract JTI from token (or generate one)"""
        # For simplicity, using token hash as JTI
        return self._get_token_hash(token)
    
    def _get_user_info_for_refresh(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information for token refresh (mock implementation)"""
        # In a real implementation, this would query the database
        # For now, return mock data
        return {
            'user_id': user_id,
            'email': f'user_{user_id}@example.com',
            'roles': ['user'],
            'scopes': ['read', 'write'],
            'tenant_id': None,
            'audience': 'web'
        }

# Factory function for creating JWT service
def create_jwt_service(secret_key: str = None, algorithm: str = 'HS256', 
                      redis_url: str = None) -> JWTService:
    """
    Create JWT service instance
    
    Args:
        secret_key: JWT secret key (defaults to environment variable)
        algorithm: JWT algorithm
        redis_url: Redis connection URL
        
    Returns:
        Configured JWT service instance
    """
    if secret_key is None:
        secret_key = os.getenv('JWT_SECRET_KEY')
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY environment variable is required")
    
    config = TokenConfig(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expiry_hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRY_HOURS', '24')),
        refresh_token_expiry_days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRY_DAYS', '30')),
        issuer=os.getenv('JWT_ISSUER', 'universal-auth')
    )
    
    redis_client = None
    if redis_url:
        redis_client = redis.from_url(redis_url)
    elif os.getenv('REDIS_URL'):
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
    
    return JWTService(config, redis_client)