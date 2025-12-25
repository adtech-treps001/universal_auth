"""
Session Service

This module provides session management functionality with dynamic scope
version tracking and automatic invalidation when scopes change.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import and_
from datetime import datetime, timedelta
from models.user import Session, User
from services.scope_manager import get_scope_manager
from services.rbac_service import RBACService
from jose import jwt
import uuid
import logging

logger = logging.getLogger(__name__)

class SessionService:
    """Service for managing user sessions with scope tracking"""
    
    def __init__(self, db: DBSession, secret_key: str, rbac_service: RBACService = None):
        self.db = db
        self.secret_key = secret_key
        self.rbac_service = rbac_service
        self.scope_manager = get_scope_manager(db)
        
        # JWT configuration
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
    
    def create_session(self, user_id: str, tenant_id: str = None, 
                      device_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new user session with current scope version
        
        Args:
            user_id: User ID
            tenant_id: Tenant context
            device_info: Device information
            
        Returns:
            Session data with tokens
        """
        # Get user capabilities and roles
        if self.rbac_service:
            capabilities = list(self.rbac_service.get_user_capabilities(user_id, tenant_id))
            roles = self.rbac_service.get_user_roles(user_id, tenant_id)
        else:
            capabilities = []
            roles = []
        
        # Get current scope version
        scope_version = self.scope_manager.get_user_scope_version(user_id, tenant_id)
        
        # Update scope version with current capabilities
        current_version = self.scope_manager.update_user_scope(
            user_id, capabilities, roles, tenant_id
        )
        
        # Generate tokens
        access_token = self._generate_access_token(user_id, tenant_id, capabilities, current_version)
        refresh_token = self._generate_refresh_token(user_id, tenant_id)
        
        # Create session record
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes),
            capabilities=capabilities,
            scope_version=current_version,
            device_info=device_info or {},
            is_active=True
        )
        
        self.db.add(session)
        self.db.commit()
        
        logger.info(f"Created session {session.id} for user {user_id} with scope version {current_version}")
        
        return {
            'session_id': session.id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': session.expires_at,
            'scope_version': current_version,
            'capabilities': capabilities
        }
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate session and check scope version
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data if valid, None if invalid
        """
        session = self.db.query(Session).filter(
            Session.id == session_id,
            Session.is_active == True
        ).first()
        
        if not session:
            return None
        
        # Check if session is expired
        if session.expires_at < datetime.utcnow():
            session.is_active = False
            self.db.commit()
            logger.info(f"Session {session_id} expired")
            return None
        
        # Check scope version
        current_scope_version = self.scope_manager.get_user_scope_version(
            session.user_id, session.tenant_id
        )
        
        if session.scope_version < current_scope_version:
            # Session has outdated scope, invalidate it
            session.is_active = False
            self.db.commit()
            logger.info(f"Session {session_id} invalidated due to scope version mismatch")
            return None
        
        # Update last used timestamp
        session.last_used = datetime.utcnow()
        session.last_scope_check = datetime.utcnow()
        self.db.commit()
        
        return {
            'session_id': session.id,
            'user_id': session.user_id,
            'tenant_id': session.tenant_id,
            'capabilities': session.capabilities,
            'scope_version': session.scope_version,
            'expires_at': session.expires_at
        }
    
    def refresh_session(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh session with updated scope version
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New session data if successful
        """
        try:
            # Decode refresh token
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            tenant_id = payload.get('tenant_id')
            
            if not user_id:
                return None
            
            # Find session with this refresh token
            session = self.db.query(Session).filter(
                Session.user_id == user_id,
                Session.tenant_id == tenant_id,
                Session.is_active == True
            ).first()
            
            if not session or session.refresh_token != refresh_token:
                return None
            
            # Get current capabilities and scope version
            if self.rbac_service:
                capabilities = list(self.rbac_service.get_user_capabilities(user_id, tenant_id))
                roles = self.rbac_service.get_user_roles(user_id, tenant_id)
            else:
                capabilities = session.capabilities
                roles = []
            
            # Update scope version
            current_version = self.scope_manager.update_user_scope(
                user_id, capabilities, roles, tenant_id
            )
            
            # Generate new tokens
            new_access_token = self._generate_access_token(user_id, tenant_id, capabilities, current_version)
            new_refresh_token = self._generate_refresh_token(user_id, tenant_id)
            
            # Update session
            session.access_token = new_access_token
            session.refresh_token = new_refresh_token
            session.expires_at = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
            session.capabilities = capabilities
            session.scope_version = current_version
            session.last_scope_check = datetime.utcnow()
            session.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Refreshed session {session.id} with scope version {current_version}")
            
            return {
                'session_id': session.id,
                'access_token': new_access_token,
                'refresh_token': new_refresh_token,
                'expires_at': session.expires_at,
                'scope_version': current_version,
                'capabilities': capabilities
            }
            
        except jwt.InvalidTokenError:
            logger.warning("Invalid refresh token provided")
            return None
        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a specific session
        
        Args:
            session_id: Session ID
            
        Returns:
            Success status
        """
        session = self.db.query(Session).filter(Session.id == session_id).first()
        if session:
            session.is_active = False
            session.updated_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Invalidated session {session_id}")
            return True
        return False
    
    def invalidate_user_sessions(self, user_id: str, tenant_id: str = None, 
                               exclude_session_id: str = None) -> int:
        """
        Invalidate all sessions for a user
        
        Args:
            user_id: User ID
            tenant_id: Tenant context (None for all tenants)
            exclude_session_id: Session ID to exclude from invalidation
            
        Returns:
            Number of sessions invalidated
        """
        query = self.db.query(Session).filter(
            Session.user_id == user_id,
            Session.is_active == True
        )
        
        if tenant_id:
            query = query.filter(Session.tenant_id == tenant_id)
        
        if exclude_session_id:
            query = query.filter(Session.id != exclude_session_id)
        
        sessions = query.all()
        count = 0
        
        for session in sessions:
            session.is_active = False
            session.updated_at = datetime.utcnow()
            count += 1
        
        self.db.commit()
        logger.info(f"Invalidated {count} sessions for user {user_id}")
        return count
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions
        
        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = self.db.query(Session).filter(
            Session.expires_at < datetime.utcnow(),
            Session.is_active == True
        ).all()
        
        count = 0
        for session in expired_sessions:
            session.is_active = False
            session.updated_at = datetime.utcnow()
            count += 1
        
        self.db.commit()
        logger.info(f"Cleaned up {count} expired sessions")
        return count
    
    def get_user_sessions(self, user_id: str, tenant_id: str = None) -> List[Dict[str, Any]]:
        """
        Get active sessions for a user
        
        Args:
            user_id: User ID
            tenant_id: Tenant context
            
        Returns:
            List of session information
        """
        query = self.db.query(Session).filter(
            Session.user_id == user_id,
            Session.is_active == True
        )
        
        if tenant_id:
            query = query.filter(Session.tenant_id == tenant_id)
        
        sessions = query.all()
        
        return [
            {
                'session_id': session.id,
                'tenant_id': session.tenant_id,
                'created_at': session.created_at,
                'last_used': session.last_used,
                'expires_at': session.expires_at,
                'scope_version': session.scope_version,
                'device_info': session.device_info
            }
            for session in sessions
        ]
    
    def _generate_access_token(self, user_id: str, tenant_id: str, 
                             capabilities: List[str], scope_version: int) -> str:
        """Generate JWT access token"""
        payload = {
            'user_id': user_id,
            'tenant_id': tenant_id,
            'capabilities': capabilities,
            'scope_version': scope_version,
            'exp': datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def _generate_refresh_token(self, user_id: str, tenant_id: str) -> str:
        """Generate JWT refresh token"""
        payload = {
            'user_id': user_id,
            'tenant_id': tenant_id,
            'exp': datetime.utcnow() + timedelta(days=self.refresh_token_expire_days),
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def decode_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate access token
        
        Args:
            token: JWT access token
            
        Returns:
            Token payload if valid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            if payload.get('type') != 'access':
                return None
            return payload
        except jwt.InvalidTokenError:
            return None
    
    def check_session_scope_version(self, session_id: str) -> bool:
        """
        Check if session scope version is current
        
        Args:
            session_id: Session ID
            
        Returns:
            True if scope version is current
        """
        session = self.db.query(Session).filter(
            Session.id == session_id,
            Session.is_active == True
        ).first()
        
        if not session:
            return False
        
        current_version = self.scope_manager.get_user_scope_version(
            session.user_id, session.tenant_id
        )
        
        return session.scope_version >= current_version