"""
Tenant Service

This module provides multi-tenant functionality including tenant management,
data isolation, and tenant-specific configurations.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from datetime import datetime
from models.user import User, TenantMembership
from services.rbac_service import RBACService
import uuid

class Tenant:
    """Tenant model for multi-tenant support"""
    
    def __init__(self, tenant_id: str, name: str, config: Dict[str, Any] = None):
        self.tenant_id = tenant_id
        self.name = name
        self.config = config or {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.is_active = True

class TenantService:
    """Service for multi-tenant management and data isolation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.rbac_service = RBACService(db)
        self._tenants = {}  # In-memory tenant registry
    
    def create_tenant(self, name: str, config: Dict[str, Any] = None, tenant_id: str = None) -> Tenant:
        """
        Create a new tenant
        
        Args:
            name: Tenant name
            config: Tenant-specific configuration
            tenant_id: Optional custom tenant ID
            
        Returns:
            Created tenant instance
        """
        if not tenant_id:
            tenant_id = str(uuid.uuid4())
        
        if tenant_id in self._tenants:
            raise ValueError(f"Tenant {tenant_id} already exists")
        
        tenant = Tenant(tenant_id, name, config)
        self._tenants[tenant_id] = tenant
        
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """
        Get tenant by ID
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Tenant instance or None
        """
        return self._tenants.get(tenant_id)
    
    def list_tenants(self) -> List[Tenant]:
        """
        List all tenants
        
        Returns:
            List of tenant instances
        """
        return list(self._tenants.values())
    
    def update_tenant(self, tenant_id: str, name: str = None, config: Dict[str, Any] = None) -> bool:
        """
        Update tenant information
        
        Args:
            tenant_id: Tenant ID
            name: New tenant name (optional)
            config: New tenant configuration (optional)
            
        Returns:
            Success status
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        
        if name:
            tenant.name = name
        if config:
            tenant.config = config
        
        tenant.updated_at = datetime.utcnow()
        return True
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """
        Delete tenant and all associated data
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Success status
        """
        if tenant_id not in self._tenants:
            return False
        
        # Remove all tenant memberships
        self.db.query(TenantMembership).filter(
            TenantMembership.tenant_id == tenant_id
        ).delete()
        
        # Remove tenant from registry
        del self._tenants[tenant_id]
        
        self.db.commit()
        return True
    
    def add_user_to_tenant(self, user_id: str, tenant_id: str, role: str = "user") -> bool:
        """
        Add user to tenant with specified role
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            role: User role in tenant
            
        Returns:
            Success status
        """
        if tenant_id not in self._tenants:
            raise ValueError(f"Tenant {tenant_id} does not exist")
        
        # Use RBAC service to assign role
        return self.rbac_service.assign_role(user_id, role, tenant_id)
    
    def remove_user_from_tenant(self, user_id: str, tenant_id: str) -> bool:
        """
        Remove user from tenant
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            
        Returns:
            Success status
        """
        return self.rbac_service.remove_role(user_id, tenant_id)
    
    def get_tenant_users(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Get all users in tenant
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            List of user information with roles
        """
        memberships = self.db.query(TenantMembership).filter(
            and_(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.is_active == True
            )
        ).all()
        
        users = []
        for membership in memberships:
            user = self.db.query(User).filter(User.id == membership.user_id).first()
            if user:
                users.append({
                    "user_id": user.id,
                    "email": user.email,
                    "role": membership.role,
                    "capabilities": membership.capabilities,
                    "joined_at": membership.created_at,
                    "last_accessed": membership.last_accessed
                })
        
        return users
    
    def get_user_tenants(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all tenants user belongs to
        
        Args:
            user_id: User ID
            
        Returns:
            List of tenant information with user roles
        """
        memberships = self.db.query(TenantMembership).filter(
            and_(
                TenantMembership.user_id == user_id,
                TenantMembership.is_active == True
            )
        ).all()
        
        tenants = []
        for membership in memberships:
            if membership.tenant_id != "global":
                tenant = self.get_tenant(membership.tenant_id)
                if tenant:
                    tenants.append({
                        "tenant_id": tenant.tenant_id,
                        "tenant_name": tenant.name,
                        "role": membership.role,
                        "capabilities": membership.capabilities,
                        "joined_at": membership.created_at,
                        "last_accessed": membership.last_accessed
                    })
        
        return tenants
    
    def check_user_tenant_access(self, user_id: str, tenant_id: str) -> bool:
        """
        Check if user has access to tenant
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            
        Returns:
            True if user has access
        """
        membership = self.db.query(TenantMembership).filter(
            and_(
                TenantMembership.user_id == user_id,
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.is_active == True
            )
        ).first()
        
        return membership is not None
    
    def get_tenant_config(self, tenant_id: str, key: str = None) -> Any:
        """
        Get tenant-specific configuration
        
        Args:
            tenant_id: Tenant ID
            key: Configuration key (optional)
            
        Returns:
            Configuration value or entire config
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None
        
        if key:
            return tenant.config.get(key)
        return tenant.config
    
    def set_tenant_config(self, tenant_id: str, key: str, value: Any) -> bool:
        """
        Set tenant-specific configuration
        
        Args:
            tenant_id: Tenant ID
            key: Configuration key
            value: Configuration value
            
        Returns:
            Success status
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        tenant.config[key] = value
        tenant.updated_at = datetime.utcnow()
        return True
    
    def isolate_query_by_tenant(self, query, tenant_id: str, tenant_field: str = "tenant_id"):
        """
        Add tenant isolation to SQLAlchemy query
        
        Args:
            query: SQLAlchemy query object
            tenant_id: Tenant ID to filter by
            tenant_field: Field name for tenant ID in the model
            
        Returns:
            Modified query with tenant isolation
        """
        return query.filter(text(f"{tenant_field} = :tenant_id")).params(tenant_id=tenant_id)
    
    def get_tenant_statistics(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get tenant statistics
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Dictionary with tenant statistics
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return {}
        
        # Count active users
        active_users = self.db.query(TenantMembership).filter(
            and_(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.is_active == True
            )
        ).count()
        
        # Count by role
        role_counts = {}
        memberships = self.db.query(TenantMembership).filter(
            and_(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.is_active == True
            )
        ).all()
        
        for membership in memberships:
            role = membership.role
            role_counts[role] = role_counts.get(role, 0) + 1
        
        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "active_users": active_users,
            "role_distribution": role_counts,
            "created_at": tenant.created_at,
            "updated_at": tenant.updated_at,
            "config_keys": list(tenant.config.keys())
        }
    
    def transfer_user_between_tenants(self, user_id: str, from_tenant_id: str, 
                                    to_tenant_id: str, new_role: str = None) -> bool:
        """
        Transfer user from one tenant to another
        
        Args:
            user_id: User ID
            from_tenant_id: Source tenant ID
            to_tenant_id: Destination tenant ID
            new_role: New role in destination tenant (optional)
            
        Returns:
            Success status
        """
        # Check if both tenants exist
        if from_tenant_id not in self._tenants or to_tenant_id not in self._tenants:
            return False
        
        # Get current membership
        current_membership = self.db.query(TenantMembership).filter(
            and_(
                TenantMembership.user_id == user_id,
                TenantMembership.tenant_id == from_tenant_id,
                TenantMembership.is_active == True
            )
        ).first()
        
        if not current_membership:
            return False
        
        # Use current role if new role not specified
        role = new_role or current_membership.role
        
        # Remove from source tenant
        self.remove_user_from_tenant(user_id, from_tenant_id)
        
        # Add to destination tenant
        return self.add_user_to_tenant(user_id, to_tenant_id, role)
    
    def bulk_invite_users(self, tenant_id: str, user_emails: List[str], 
                         role: str = "user") -> Dict[str, Any]:
        """
        Bulk invite users to tenant
        
        Args:
            tenant_id: Tenant ID
            user_emails: List of user email addresses
            role: Role to assign to invited users
            
        Returns:
            Dictionary with invitation results
        """
        if tenant_id not in self._tenants:
            raise ValueError(f"Tenant {tenant_id} does not exist")
        
        results = {
            "successful": [],
            "failed": [],
            "already_members": []
        }
        
        for email in user_emails:
            # Find user by email
            user = self.db.query(User).filter(User.email == email).first()
            
            if not user:
                results["failed"].append({"email": email, "reason": "User not found"})
                continue
            
            # Check if already a member
            if self.check_user_tenant_access(user.id, tenant_id):
                results["already_members"].append({"email": email, "user_id": user.id})
                continue
            
            # Add to tenant
            try:
                success = self.add_user_to_tenant(user.id, tenant_id, role)
                if success:
                    results["successful"].append({"email": email, "user_id": user.id, "role": role})
                else:
                    results["failed"].append({"email": email, "reason": "Failed to add to tenant"})
            except Exception as e:
                results["failed"].append({"email": email, "reason": str(e)})
        
        return results