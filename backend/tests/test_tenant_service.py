"""
Unit Tests for Tenant Service

This module contains comprehensive unit tests for the TenantService
including tenant management, user assignments, and data isolation.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from services.tenant_service import TenantService, Tenant
from models.user import User, TenantMembership
from services.rbac_service import RBACService

class TestTenantService:
    """Test cases for TenantService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_rbac_service(self):
        """Mock RBAC service"""
        return Mock(spec=RBACService)
    
    @pytest.fixture
    def tenant_service(self, mock_db, mock_rbac_service):
        """Create TenantService instance with mocked dependencies"""
        with patch('services.tenant_service.RBACService') as mock_rbac_class:
            mock_rbac_class.return_value = mock_rbac_service
            service = TenantService(mock_db)
            return service
    
    def test_create_tenant_success(self, tenant_service):
        """Test successful tenant creation"""
        # Act
        tenant = tenant_service.create_tenant("Test Tenant", {"key": "value"})
        
        # Assert
        assert tenant.name == "Test Tenant"
        assert tenant.config == {"key": "value"}
        assert tenant.is_active is True
        assert isinstance(tenant.created_at, datetime)
        assert isinstance(tenant.updated_at, datetime)
        assert tenant.tenant_id in tenant_service._tenants
    
    def test_create_tenant_with_custom_id(self, tenant_service):
        """Test tenant creation with custom ID"""
        # Act
        tenant = tenant_service.create_tenant("Test Tenant", tenant_id="custom-id")
        
        # Assert
        assert tenant.tenant_id == "custom-id"
        assert tenant.name == "Test Tenant"
    
    def test_create_tenant_duplicate_id(self, tenant_service):
        """Test tenant creation with duplicate ID fails"""
        # Arrange
        tenant_service.create_tenant("First Tenant", tenant_id="duplicate-id")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Tenant duplicate-id already exists"):
            tenant_service.create_tenant("Second Tenant", tenant_id="duplicate-id")
    
    def test_get_tenant_exists(self, tenant_service):
        """Test getting existing tenant"""
        # Arrange
        created_tenant = tenant_service.create_tenant("Test Tenant")
        
        # Act
        retrieved_tenant = tenant_service.get_tenant(created_tenant.tenant_id)
        
        # Assert
        assert retrieved_tenant is not None
        assert retrieved_tenant.tenant_id == created_tenant.tenant_id
        assert retrieved_tenant.name == "Test Tenant"
    
    def test_get_tenant_not_exists(self, tenant_service):
        """Test getting non-existent tenant returns None"""
        # Act
        tenant = tenant_service.get_tenant("non-existent-id")
        
        # Assert
        assert tenant is None
    
    def test_list_tenants_empty(self, tenant_service):
        """Test listing tenants when none exist"""
        # Act
        tenants = tenant_service.list_tenants()
        
        # Assert
        assert tenants == []
    
    def test_list_tenants_multiple(self, tenant_service):
        """Test listing multiple tenants"""
        # Arrange
        tenant1 = tenant_service.create_tenant("Tenant 1")
        tenant2 = tenant_service.create_tenant("Tenant 2")
        
        # Act
        tenants = tenant_service.list_tenants()
        
        # Assert
        assert len(tenants) == 2
        tenant_ids = [t.tenant_id for t in tenants]
        assert tenant1.tenant_id in tenant_ids
        assert tenant2.tenant_id in tenant_ids
    
    def test_update_tenant_success(self, tenant_service):
        """Test successful tenant update"""
        # Arrange
        tenant = tenant_service.create_tenant("Original Name", {"old": "config"})
        original_updated_at = tenant.updated_at
        
        # Act
        success = tenant_service.update_tenant(
            tenant.tenant_id,
            name="Updated Name",
            config={"new": "config"}
        )
        
        # Assert
        assert success is True
        updated_tenant = tenant_service.get_tenant(tenant.tenant_id)
        assert updated_tenant.name == "Updated Name"
        assert updated_tenant.config == {"new": "config"}
        assert updated_tenant.updated_at > original_updated_at
    
    def test_update_tenant_partial(self, tenant_service):
        """Test partial tenant update"""
        # Arrange
        tenant = tenant_service.create_tenant("Original Name", {"key": "value"})
        
        # Act - Update only name
        success = tenant_service.update_tenant(tenant.tenant_id, name="New Name")
        
        # Assert
        assert success is True
        updated_tenant = tenant_service.get_tenant(tenant.tenant_id)
        assert updated_tenant.name == "New Name"
        assert updated_tenant.config == {"key": "value"}  # Config unchanged
    
    def test_update_tenant_not_exists(self, tenant_service):
        """Test updating non-existent tenant fails"""
        # Act
        success = tenant_service.update_tenant("non-existent", name="New Name")
        
        # Assert
        assert success is False
    
    def test_delete_tenant_success(self, tenant_service, mock_db):
        """Test successful tenant deletion"""
        # Arrange
        tenant = tenant_service.create_tenant("Test Tenant")
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.delete.return_value = 1
        
        # Act
        success = tenant_service.delete_tenant(tenant.tenant_id)
        
        # Assert
        assert success is True
        assert tenant.tenant_id not in tenant_service._tenants
        mock_db.query.assert_called_with(TenantMembership)
        mock_db.commit.assert_called_once()
    
    def test_delete_tenant_not_exists(self, tenant_service):
        """Test deleting non-existent tenant fails"""
        # Act
        success = tenant_service.delete_tenant("non-existent")
        
        # Assert
        assert success is False
    
    def test_add_user_to_tenant_success(self, tenant_service, mock_rbac_service):
        """Test successfully adding user to tenant"""
        # Arrange
        tenant = tenant_service.create_tenant("Test Tenant")
        mock_rbac_service.assign_role.return_value = True
        
        # Act
        success = tenant_service.add_user_to_tenant("user123", tenant.tenant_id, "admin")
        
        # Assert
        assert success is True
        mock_rbac_service.assign_role.assert_called_once_with("user123", "admin", tenant.tenant_id)
    
    def test_add_user_to_tenant_invalid_tenant(self, tenant_service):
        """Test adding user to non-existent tenant fails"""
        # Act & Assert
        with pytest.raises(ValueError, match="Tenant non-existent does not exist"):
            tenant_service.add_user_to_tenant("user123", "non-existent", "user")
    
    def test_remove_user_from_tenant(self, tenant_service, mock_rbac_service):
        """Test removing user from tenant"""
        # Arrange
        tenant = tenant_service.create_tenant("Test Tenant")
        mock_rbac_service.remove_role.return_value = True
        
        # Act
        success = tenant_service.remove_user_from_tenant("user123", tenant.tenant_id)
        
        # Assert
        assert success is True
        mock_rbac_service.remove_role.assert_called_once_with("user123", tenant.tenant_id)
    
    def test_get_tenant_users(self, tenant_service, mock_db):
        """Test getting tenant users"""
        # Arrange
        tenant = tenant_service.create_tenant("Test Tenant")
        
        # Mock database query
        mock_membership = Mock()
        mock_membership.user_id = "user123"
        mock_membership.role = "admin"
        mock_membership.capabilities = ["tenant:read", "tenant:write"]
        mock_membership.created_at = datetime.utcnow()
        mock_membership.last_accessed = datetime.utcnow()
        
        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.email = "user@example.com"
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_membership]
        mock_query.first.return_value = mock_user
        
        # Act
        users = tenant_service.get_tenant_users(tenant.tenant_id)
        
        # Assert
        assert len(users) == 1
        user_info = users[0]
        assert user_info["user_id"] == "user123"
        assert user_info["email"] == "user@example.com"
        assert user_info["role"] == "admin"
        assert user_info["capabilities"] == ["tenant:read", "tenant:write"]
    
    def test_get_user_tenants(self, tenant_service, mock_db):
        """Test getting user's tenants"""
        # Arrange
        tenant1 = tenant_service.create_tenant("Tenant 1")
        tenant2 = tenant_service.create_tenant("Tenant 2")
        
        # Mock database query
        mock_membership1 = Mock()
        mock_membership1.tenant_id = tenant1.tenant_id
        mock_membership1.role = "admin"
        mock_membership1.capabilities = ["tenant:read"]
        mock_membership1.created_at = datetime.utcnow()
        mock_membership1.last_accessed = datetime.utcnow()
        
        mock_membership2 = Mock()
        mock_membership2.tenant_id = tenant2.tenant_id
        mock_membership2.role = "user"
        mock_membership2.capabilities = ["tenant:read"]
        mock_membership2.created_at = datetime.utcnow()
        mock_membership2.last_accessed = datetime.utcnow()
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_membership1, mock_membership2]
        
        # Act
        tenants = tenant_service.get_user_tenants("user123")
        
        # Assert
        assert len(tenants) == 2
        tenant_ids = [t["tenant_id"] for t in tenants]
        assert tenant1.tenant_id in tenant_ids
        assert tenant2.tenant_id in tenant_ids
    
    def test_check_user_tenant_access_has_access(self, tenant_service, mock_db):
        """Test checking user tenant access when user has access"""
        # Arrange
        tenant = tenant_service.create_tenant("Test Tenant")
        
        mock_membership = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_membership
        
        # Act
        has_access = tenant_service.check_user_tenant_access("user123", tenant.tenant_id)
        
        # Assert
        assert has_access is True
    
    def test_check_user_tenant_access_no_access(self, tenant_service, mock_db):
        """Test checking user tenant access when user has no access"""
        # Arrange
        tenant = tenant_service.create_tenant("Test Tenant")
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        # Act
        has_access = tenant_service.check_user_tenant_access("user123", tenant.tenant_id)
        
        # Assert
        assert has_access is False
    
    def test_get_tenant_config_full(self, tenant_service):
        """Test getting full tenant configuration"""
        # Arrange
        config = {"key1": "value1", "key2": "value2"}
        tenant = tenant_service.create_tenant("Test Tenant", config)
        
        # Act
        retrieved_config = tenant_service.get_tenant_config(tenant.tenant_id)
        
        # Assert
        assert retrieved_config == config
    
    def test_get_tenant_config_specific_key(self, tenant_service):
        """Test getting specific configuration key"""
        # Arrange
        config = {"key1": "value1", "key2": "value2"}
        tenant = tenant_service.create_tenant("Test Tenant", config)
        
        # Act
        value = tenant_service.get_tenant_config(tenant.tenant_id, "key1")
        
        # Assert
        assert value == "value1"
    
    def test_get_tenant_config_missing_key(self, tenant_service):
        """Test getting non-existent configuration key"""
        # Arrange
        tenant = tenant_service.create_tenant("Test Tenant", {"key1": "value1"})
        
        # Act
        value = tenant_service.get_tenant_config(tenant.tenant_id, "missing_key")
        
        # Assert
        assert value is None
    
    def test_get_tenant_config_invalid_tenant(self, tenant_service):
        """Test getting config for non-existent tenant"""
        # Act
        config = tenant_service.get_tenant_config("non-existent")
        
        # Assert
        assert config is None
    
    def test_set_tenant_config_success(self, tenant_service):
        """Test setting tenant configuration"""
        # Arrange
        tenant = tenant_service.create_tenant("Test Tenant", {"old_key": "old_value"})
        original_updated_at = tenant.updated_at
        
        # Act
        success = tenant_service.set_tenant_config(tenant.tenant_id, "new_key", "new_value")
        
        # Assert
        assert success is True
        updated_tenant = tenant_service.get_tenant(tenant.tenant_id)
        assert updated_tenant.config["new_key"] == "new_value"
        assert updated_tenant.config["old_key"] == "old_value"  # Existing config preserved
        assert updated_tenant.updated_at > original_updated_at
    
    def test_set_tenant_config_invalid_tenant(self, tenant_service):
        """Test setting config for non-existent tenant"""
        # Act
        success = tenant_service.set_tenant_config("non-existent", "key", "value")
        
        # Assert
        assert success is False
    
    def test_get_tenant_statistics(self, tenant_service, mock_db):
        """Test getting tenant statistics"""
        # Arrange
        tenant = tenant_service.create_tenant("Test Tenant")
        
        # Mock database queries
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5  # 5 active users
        
        # Mock memberships for role distribution
        mock_membership1 = Mock()
        mock_membership1.role = "admin"
        mock_membership2 = Mock()
        mock_membership2.role = "user"
        mock_membership3 = Mock()
        mock_membership3.role = "user"
        
        mock_query.all.return_value = [mock_membership1, mock_membership2, mock_membership3]
        
        # Act
        stats = tenant_service.get_tenant_statistics(tenant.tenant_id)
        
        # Assert
        assert stats["tenant_id"] == tenant.tenant_id
        assert stats["tenant_name"] == "Test Tenant"
        assert stats["active_users"] == 5
        assert stats["role_distribution"] == {"admin": 1, "user": 2}
        assert "created_at" in stats
        assert "updated_at" in stats
    
    def test_get_tenant_statistics_invalid_tenant(self, tenant_service):
        """Test getting statistics for non-existent tenant"""
        # Act
        stats = tenant_service.get_tenant_statistics("non-existent")
        
        # Assert
        assert stats == {}
    
    def test_transfer_user_between_tenants_success(self, tenant_service, mock_db, mock_rbac_service):
        """Test successful user transfer between tenants"""
        # Arrange
        tenant1 = tenant_service.create_tenant("Tenant 1")
        tenant2 = tenant_service.create_tenant("Tenant 2")
        
        # Mock existing membership
        mock_membership = Mock()
        mock_membership.role = "user"
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_membership
        
        mock_rbac_service.remove_role.return_value = True
        mock_rbac_service.assign_role.return_value = True
        
        # Act
        success = tenant_service.transfer_user_between_tenants(
            "user123", tenant1.tenant_id, tenant2.tenant_id, "admin"
        )
        
        # Assert
        assert success is True
        mock_rbac_service.remove_role.assert_called_once_with("user123", tenant1.tenant_id)
        mock_rbac_service.assign_role.assert_called_once_with("user123", "admin", tenant2.tenant_id)
    
    def test_transfer_user_between_tenants_invalid_source(self, tenant_service):
        """Test transfer with invalid source tenant"""
        # Arrange
        tenant2 = tenant_service.create_tenant("Tenant 2")
        
        # Act
        success = tenant_service.transfer_user_between_tenants(
            "user123", "non-existent", tenant2.tenant_id
        )
        
        # Assert
        assert success is False
    
    def test_bulk_invite_users_success(self, tenant_service, mock_db):
        """Test successful bulk user invitation"""
        # Arrange
        tenant = tenant_service.create_tenant("Test Tenant")
        
        # Mock users in database
        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.email = "user1@example.com"
        
        mock_user2 = Mock()
        mock_user2.id = "user2"
        mock_user2.email = "user2@example.com"
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Mock user lookups
        def mock_first_side_effect():
            calls = mock_query.first.call_count
            if calls == 1:
                return mock_user1
            elif calls == 2:
                return mock_user2
            return None
        
        mock_query.first.side_effect = mock_first_side_effect
        
        # Mock tenant access checks
        tenant_service.check_user_tenant_access = Mock(return_value=False)
        tenant_service.add_user_to_tenant = Mock(return_value=True)
        
        # Act
        results = tenant_service.bulk_invite_users(
            tenant.tenant_id,
            ["user1@example.com", "user2@example.com"],
            "user"
        )
        
        # Assert
        assert len(results["successful"]) == 2
        assert len(results["failed"]) == 0
        assert len(results["already_members"]) == 0
    
    def test_bulk_invite_users_mixed_results(self, tenant_service, mock_db):
        """Test bulk invitation with mixed results"""
        # Arrange
        tenant = tenant_service.create_tenant("Test Tenant")
        
        # Mock one existing user, one non-existent
        mock_user = Mock()
        mock_user.id = "user1"
        mock_user.email = "user1@example.com"
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        def mock_first_side_effect():
            calls = mock_query.first.call_count
            if calls == 1:
                return mock_user  # First user exists
            return None  # Second user doesn't exist
        
        mock_query.first.side_effect = mock_first_side_effect
        
        # Mock tenant access check
        tenant_service.check_user_tenant_access = Mock(return_value=False)
        tenant_service.add_user_to_tenant = Mock(return_value=True)
        
        # Act
        results = tenant_service.bulk_invite_users(
            tenant.tenant_id,
            ["user1@example.com", "nonexistent@example.com"],
            "user"
        )
        
        # Assert
        assert len(results["successful"]) == 1
        assert len(results["failed"]) == 1
        assert results["failed"][0]["reason"] == "User not found"
    
    def test_isolate_query_by_tenant(self, tenant_service, mock_db):
        """Test query isolation by tenant"""
        # Arrange
        mock_query = Mock()
        mock_filtered_query = Mock()
        mock_query.filter.return_value = mock_filtered_query
        
        # Act
        isolated_query = tenant_service.isolate_query_by_tenant(
            mock_query, "tenant123", "custom_tenant_field"
        )
        
        # Assert
        mock_query.filter.assert_called_once()
        mock_filtered_query.params.assert_called_once_with(tenant_id="tenant123")

if __name__ == "__main__":
    pytest.main([__file__])