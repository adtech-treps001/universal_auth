"""
RBAC Service

This module provides role-based access control functionality including
role assignment, capability checking, and hierarchical role inheritance.
"""

from typing import Dict, Any, Optional, List, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
from models.user import User, TenantMembership
import yaml
import os

class RBACConfig:
    """Configuration for RBAC system"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '../../config/auth/rbac.yaml')
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.roles = config.get('roles', {})
        self.role_hierarchy = self._build_role_hierarchy()
    
    def _build_role_hierarchy(self) -> Dict[str, Set[str]]:
        """Build role hierarchy for inheritance"""
        hierarchy = {}
        
        # Define role hierarchy (higher roles inherit from lower roles)
        role_levels = {
            'viewer': 0,
            'user': 1,
            'power_user': 2,
            'admin': 3
        }
        
        for role, level in role_levels.items():
            inherited_roles = set()
            for other_role, other_level in role_levels.items():
                if other_level <= level:
                    inherited_roles.add(other_role)
            hierarchy[role] = inherited_roles
        
        return hierarchy
    
    def get_role_capabilities(self, role: str) -> Set[str]:
        """Get all capabilities for a role including inherited ones"""
        if role not in self.roles:
            return set()
        
        capabilities = set(self.roles[role].get('capabilities', []))
        
        # Handle wildcard admin capabilities - return only wildcard
        if '*' in capabilities:
            return {'*'}
        
        # Add inherited capabilities
        if role in self.role_hierarchy:
            for inherited_role in self.role_hierarchy[role]:
                if inherited_role != role and inherited_role in self.roles:
                    inherited_caps = set(self.roles[inherited_role].get('capabilities', []))
                    # Don't inherit if inherited role has wildcard
                    if '*' not in inherited_caps:
                        capabilities.update(inherited_caps)
        
        return capabilities
    
    def has_capability(self, user_capabilities: Set[str], required_capability: str) -> bool:
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

class RBACService:
    """Service for role-based access control"""
    
    def __init__(self, db: Session, config_path: str = None, scope_manager=None):
        self.db = db
        self.config = RBACConfig(config_path)
        self.scope_manager = scope_manager
    
    def assign_role(self, user_id: str, role: str, tenant_id: str = None) -> bool:
        """
        Assign role to user in tenant context
        
        Args:
            user_id: User ID
            role: Role name
            tenant_id: Tenant ID (None for global role)
            
        Returns:
            Success status
        """
        if role not in self.config.roles:
            raise ValueError(f"Role {role} not configured")
        
        tenant_id_value = tenant_id or "global"
        
        # Check if membership already exists
        existing = self.db.query(TenantMembership).filter(
            and_(
                TenantMembership.user_id == user_id,
                TenantMembership.tenant_id == tenant_id_value
            )
        ).first()
        
        if existing:
            # Update existing membership
            existing.role = role
            existing.capabilities = list(self.config.get_role_capabilities(role))
            existing.updated_at = datetime.utcnow()
            existing.is_active = True  # Ensure it's active
        else:
            # Create new membership
            membership = TenantMembership(
                user_id=user_id,
                tenant_id=tenant_id_value,
                role=role,
                capabilities=list(self.config.get_role_capabilities(role))
            )
            self.db.add(membership)
        
        self.db.commit()
        
        # Update scope version if scope manager is available
        if self.scope_manager:
            capabilities = list(self.config.get_role_capabilities(role))
            roles = [role]
            self.scope_manager.update_user_scope(user_id, capabilities, roles, tenant_id)
        
        return True
    
    def get_user_roles(self, user_id: str, tenant_id: str = None) -> List[str]:
        """
        Get user roles in tenant context
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID (None for global roles)
            
        Returns:
            List of role names
        """
        query = self.db.query(TenantMembership).filter(
            TenantMembership.user_id == user_id,
            TenantMembership.is_active == True
        )
        
        if tenant_id:
            query = query.filter(
                or_(
                    TenantMembership.tenant_id == tenant_id,
                    TenantMembership.tenant_id == "global"
                )
            )
        else:
            query = query.filter(TenantMembership.tenant_id == "global")
        
        memberships = query.all()
        # Remove duplicates by converting to set and back to list
        return list(set(m.role for m in memberships))
    
    def get_user_capabilities(self, user_id: str, tenant_id: str = None) -> Set[str]:
        """
        Get all user capabilities in tenant context
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID (None for global capabilities)
            
        Returns:
            Set of capability strings
        """
        query = self.db.query(TenantMembership).filter(
            TenantMembership.user_id == user_id,
            TenantMembership.is_active == True
        )
        
        if tenant_id:
            query = query.filter(
                or_(
                    TenantMembership.tenant_id == tenant_id,
                    TenantMembership.tenant_id == "global"
                )
            )
        else:
            query = query.filter(TenantMembership.tenant_id == "global")
        
        memberships = query.all()
        capabilities = set()
        
        for membership in memberships:
            # Use stored capabilities directly
            member_caps = set(membership.capabilities or [])
            if '*' in member_caps:
                return {'*'}  # Admin wildcard overrides everything
            capabilities.update(member_caps)
        
        return capabilities
    
    def check_capability(self, user_id: str, capability: str, tenant_id: str = None) -> bool:
        """
        Check if user has required capability
        
        Args:
            user_id: User ID
            capability: Required capability
            tenant_id: Tenant ID (None for global check)
            
        Returns:
            True if user has capability
        """
        user_capabilities = self.get_user_capabilities(user_id, tenant_id)
        return self.config.has_capability(user_capabilities, capability)
    
    def remove_role(self, user_id: str, tenant_id: str = None) -> bool:
        """
        Remove user role from tenant
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID (None for global role)
            
        Returns:
            Success status
        """
        membership = self.db.query(TenantMembership).filter(
            and_(
                TenantMembership.user_id == user_id,
                TenantMembership.tenant_id == (tenant_id or "global")
            )
        ).first()
        
        if membership:
            membership.is_active = False
            membership.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Update scope version if scope manager is available
            if self.scope_manager:
                # Get remaining capabilities after role removal
                remaining_capabilities = list(self.get_user_capabilities(user_id, tenant_id))
                remaining_roles = self.get_user_roles(user_id, tenant_id)
                self.scope_manager.update_user_scope(user_id, remaining_capabilities, remaining_roles, tenant_id)
            
            return True
        
        return False
    
    def get_role_definition(self, role: str) -> Dict[str, Any]:
        """
        Get role definition including capabilities
        
        Args:
            role: Role name
            
        Returns:
            Role definition dictionary
        """
        if role not in self.config.roles:
            return {}
        
        return {
            'role': role,
            'capabilities': list(self.config.get_role_capabilities(role)),
            'direct_capabilities': self.config.roles[role].get('capabilities', []),
            'inherited_from': list(self.config.role_hierarchy.get(role, set()) - {role})
        }
    
    def list_available_roles(self) -> List[str]:
        """
        List all available roles
        
        Returns:
            List of role names
        """
        return list(self.config.roles.keys())
    
    def validate_capability_format(self, capability: str) -> bool:
        """
        Validate capability string format
        
        Args:
            capability: Capability string to validate
            
        Returns:
            True if valid format
        """
        if not capability or not isinstance(capability, str):
            return False
        
        # Allow wildcard
        if capability == '*':
            return True
        
        # Check format: namespace:action or namespace:*
        parts = capability.split(':')
        if len(parts) != 2:
            return False
        
        namespace, action = parts
        if not namespace or not action:
            return False
        
        # Validate characters (alphanumeric, underscore, dash, dot)
        import re
        pattern = r'^[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.*-]+$'
        return bool(re.match(pattern, capability))
    
    def create_custom_role(self, role_name: str, capabilities: List[str], description: str = None) -> bool:
        """
        Create a custom role (runtime only, not persisted to config)
        
        Args:
            role_name: Name of the new role
            capabilities: List of capabilities for the role
            description: Optional role description
            
        Returns:
            Success status
        """
        # Validate role name
        if not role_name or role_name in self.config.roles:
            return False
        
        # Validate all capabilities
        for cap in capabilities:
            if not self.validate_capability_format(cap):
                return False
        
        # Add to runtime config
        self.config.roles[role_name] = {
            'capabilities': capabilities,
            'description': description or f"Custom role: {role_name}",
            'custom': True
        }
        
        return True