"""
API Key Management Models

This module defines the database models for secure API key storage,
encryption, and management with support for multiple providers.
"""

from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, ForeignKey, JSON, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import uuid
import enum

from database import Base

class APIKeyProvider(enum.Enum):
    """Supported API key providers"""
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    CUSTOM = "custom"

class APIKeyStatus(enum.Enum):
    """API key status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"

class APIKey(Base):
    """API key storage with encryption"""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Key metadata
    key_name = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # APIKeyProvider enum value
    key_type = Column(String, nullable=True)  # 'chat', 'embedding', 'image', etc.
    
    # Encrypted key storage
    encrypted_key = Column(LargeBinary, nullable=False)
    key_hash = Column(String, nullable=False, index=True)  # For verification
    encryption_version = Column(String, default="v1")
    
    # Key configuration
    endpoint_url = Column(String, nullable=True)  # For custom providers
    model_access = Column(JSON, nullable=True)  # List of accessible models
    rate_limits = Column(JSON, nullable=True)  # Rate limiting configuration
    
    # Access control
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    tenant_id = Column(String, nullable=True)
    owner_id = Column(String, nullable=False)  # User who created the key
    
    # Scoping and permissions
    scopes = Column(JSON, nullable=True)  # List of allowed scopes
    allowed_roles = Column(JSON, nullable=True)  # Roles that can use this key
    ip_whitelist = Column(JSON, nullable=True)  # IP address restrictions
    
    # Key lifecycle
    status = Column(String, default=APIKeyStatus.ACTIVE.value)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Rotation and versioning
    version = Column(Integer, default=1)
    previous_key_id = Column(String, nullable=True)  # For key rotation
    rotation_schedule = Column(String, nullable=True)  # 'monthly', 'quarterly', etc.
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # Key-value tags for organization
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="api_keys")
    usage_logs = relationship("APIKeyUsageLog", back_populates="api_key", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, name={self.key_name}, provider={self.provider})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the API key is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Check if the API key is active and usable"""
        return (
            self.status == APIKeyStatus.ACTIVE.value and
            not self.is_expired
        )
    
    def to_dict(self, include_key: bool = False) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data by default)"""
        data = {
            'id': self.id,
            'key_name': self.key_name,
            'provider': self.provider,
            'key_type': self.key_type,
            'endpoint_url': self.endpoint_url,
            'model_access': self.model_access,
            'project_id': self.project_id,
            'tenant_id': self.tenant_id,
            'scopes': self.scopes,
            'status': self.status,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'usage_count': self.usage_count,
            'version': self.version,
            'description': self.description,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_expired': self.is_expired,
            'is_active': self.is_active
        }
        
        if include_key:
            # Only include for authorized access
            data['key_hash'] = self.key_hash
        
        return data

class APIKeyUsageLog(Base):
    """API key usage logging for monitoring and billing"""
    __tablename__ = "api_key_usage_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=False)
    
    # Usage metadata
    used_by = Column(String, nullable=False)  # User ID
    used_at = Column(DateTime, default=func.now())
    
    # Request details
    endpoint = Column(String, nullable=True)
    method = Column(String, nullable=True)
    model_used = Column(String, nullable=True)
    
    # Usage metrics
    tokens_used = Column(Integer, nullable=True)
    cost_estimate = Column(String, nullable=True)  # Decimal as string
    response_time_ms = Column(Integer, nullable=True)
    
    # Request/response info
    request_size = Column(Integer, nullable=True)
    response_size = Column(Integer, nullable=True)
    status_code = Column(Integer, nullable=True)
    
    # Context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    
    # Error tracking
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    api_key = relationship("APIKey", back_populates="usage_logs")
    
    def __repr__(self):
        return f"<APIKeyUsageLog(id={self.id}, key_id={self.api_key_id}, used_at={self.used_at})>"

class APIKeyRotationHistory(Base):
    """History of API key rotations"""
    __tablename__ = "api_key_rotation_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Key references
    old_key_id = Column(String, nullable=False)
    new_key_id = Column(String, nullable=False)
    
    # Rotation metadata
    rotation_type = Column(String, nullable=False)  # 'manual', 'scheduled', 'emergency'
    rotation_reason = Column(Text, nullable=True)
    rotated_by = Column(String, nullable=False)  # User ID
    rotated_at = Column(DateTime, default=func.now())
    
    # Transition details
    overlap_period_hours = Column(Integer, default=24)  # Grace period
    old_key_disabled_at = Column(DateTime, nullable=True)
    
    # Validation
    validation_status = Column(String, default="pending")  # 'pending', 'success', 'failed'
    validation_details = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<APIKeyRotationHistory(old_key={self.old_key_id}, new_key={self.new_key_id})>"

class APIKeyTemplate(Base):
    """Templates for common API key configurations"""
    __tablename__ = "api_key_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Template metadata
    template_name = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    template_type = Column(String, nullable=False)  # 'development', 'production', 'testing'
    
    # Default configuration
    default_scopes = Column(JSON, nullable=True)
    default_rate_limits = Column(JSON, nullable=True)
    default_model_access = Column(JSON, nullable=True)
    default_expiry_days = Column(Integer, nullable=True)
    
    # Template settings
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=False)
    
    def __repr__(self):
        return f"<APIKeyTemplate(name={self.template_name}, provider={self.provider})>"

# Add relationship to Project model
from models.project import Project
Project.api_keys = relationship("APIKey", back_populates="project", cascade="all, delete-orphan")