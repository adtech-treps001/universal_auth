"""
User Models

This module defines the database models for users, profiles, and provider accounts
using SQLAlchemy ORM for the Universal Auth System with encrypted sensitive fields.
"""

from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

Base = declarative_base()

class User(Base):
    """Main user model"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=True, index=True)
    phone = Column(String, unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    session_count = Column(Integer, default=0)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    provider_accounts = relationship("ProviderAccount", back_populates="user", cascade="all, delete-orphan")
    tenant_memberships = relationship("TenantMembership", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, phone={self.phone})>"

class UserProfile(Base):
    """User profile with progressive profiling support"""
    __tablename__ = "user_profiles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Basic profile fields
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    
    # Progressive profiling fields
    company = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    location = Column(String, nullable=True)
    website = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    language = Column(String, default="en")
    
    # Custom fields (JSON)
    custom_fields = Column(JSON, default=dict)
    
    # Profile completion tracking
    completion_percentage = Column(Integer, default=0)
    required_fields_completed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, completion={self.completion_percentage}%)>"

class ProviderAccount(Base):
    """OAuth provider account linked to user with encrypted tokens"""
    __tablename__ = "provider_accounts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Provider information
    provider = Column(String, nullable=False)  # google, github, linkedin, etc.
    provider_user_id = Column(String, nullable=False)
    provider_username = Column(String, nullable=True)
    provider_email = Column(String, nullable=True)
    
    # Encrypted tokens
    _access_token = Column("access_token", Text, nullable=True)
    _refresh_token = Column("refresh_token", Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    # Provider-specific data
    provider_data = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_used = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="provider_accounts")
    
    @hybrid_property
    def access_token(self):
        """Decrypt access token when accessed"""
        if self._access_token:
            from services.encryption import encryption_service
            return encryption_service.decrypt(self._access_token)
        return None
    
    @access_token.setter
    def access_token(self, value):
        """Encrypt access token when set"""
        if value:
            from services.encryption import encryption_service
            self._access_token = encryption_service.encrypt(value)
        else:
            self._access_token = None
    
    @hybrid_property
    def refresh_token(self):
        """Decrypt refresh token when accessed"""
        if self._refresh_token:
            from services.encryption import encryption_service
            return encryption_service.decrypt(self._refresh_token)
        return None
    
    @refresh_token.setter
    def refresh_token(self, value):
        """Encrypt refresh token when set"""
        if value:
            from services.encryption import encryption_service
            self._refresh_token = encryption_service.encrypt(value)
        else:
            self._refresh_token = None
    
    def __repr__(self):
        return f"<ProviderAccount(user_id={self.user_id}, provider={self.provider})>"

class TenantMembership(Base):
    """User membership in tenants with roles"""
    __tablename__ = "tenant_memberships"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String, nullable=False)
    
    # Role and permissions
    role = Column(String, nullable=False, default="user")
    capabilities = Column(JSON, default=list)  # List of capability strings
    
    # Status
    is_active = Column(Boolean, default=True)
    invited_by = Column(String, nullable=True)  # User ID who invited
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_accessed = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="tenant_memberships")
    
    def __repr__(self):
        return f"<TenantMembership(user_id={self.user_id}, tenant_id={self.tenant_id}, role={self.role})>"

class Session(Base):
    """User session tracking with encrypted tokens"""
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String, nullable=True)
    
    # Encrypted session data
    _access_token = Column("access_token", Text, nullable=False)
    _refresh_token = Column("refresh_token", Text, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    
    # Capabilities and scope
    capabilities = Column(JSON, default=list)
    scope_version = Column(Integer, default=1)
    last_scope_check = Column(DateTime, default=func.now())
    
    # Session metadata
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    device_info = Column(JSON, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_used = Column(DateTime, default=func.now())
    
    @hybrid_property
    def access_token(self):
        """Decrypt access token when accessed"""
        if self._access_token:
            from services.encryption import encryption_service
            return encryption_service.decrypt(self._access_token)
        return None
    
    @access_token.setter
    def access_token(self, value):
        """Encrypt access token when set"""
        if value:
            from services.encryption import encryption_service
            self._access_token = encryption_service.encrypt(value)
        else:
            self._access_token = None
    
    @hybrid_property
    def refresh_token(self):
        """Decrypt refresh token when accessed"""
        if self._refresh_token:
            from services.encryption import encryption_service
            return encryption_service.decrypt(self._refresh_token)
        return None
    
    @refresh_token.setter
    def refresh_token(self, value):
        """Encrypt refresh token when set"""
        if value:
            from services.encryption import encryption_service
            self._refresh_token = encryption_service.encrypt(value)
        else:
            self._refresh_token = None
    
    def __repr__(self):
        return f"<Session(user_id={self.user_id}, expires_at={self.expires_at})>"

class APIKey(Base):
    """Encrypted API key storage for external services"""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String, nullable=True)
    
    # Key information
    name = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # openai, gemini, custom
    _api_key = Column("api_key", Text, nullable=False)
    
    # Scopes and permissions
    scopes = Column(JSON, default=list)
    role_permissions = Column(JSON, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)
    
    @hybrid_property
    def api_key(self):
        """Decrypt API key when accessed"""
        if self._api_key:
            from services.encryption import encryption_service
            return encryption_service.decrypt(self._api_key)
        return None
    
    @api_key.setter
    def api_key(self, value):
        """Encrypt API key when set"""
        if value:
            from services.encryption import encryption_service
            self._api_key = encryption_service.encrypt(value)
        else:
            self._api_key = None
    
    def __repr__(self):
        return f"<APIKey(name={self.name}, provider={self.provider})>"