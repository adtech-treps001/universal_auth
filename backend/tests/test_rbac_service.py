"""
Tests for RBAC Service

This module contains unit tests for the role-based access control service,
testing role assignment, capability checking, and hierarchical inheritance.
"""

import pytest
import tempfile
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.user import Base, User, TenantMembership
from services.rbac_service import RBACService, RBACConfig

@pytest.fixture
def test_rbac_config():
    """Create test RBAC configuration"""
    config_data = {
        'roles': {
            'viewer': {
                'capabilities': ['app:login', 'app:profile.read']
            },
            'user': {
                'capabilities': ['app:login', 'app:profile.read', 'app:profile.write']
            },
            'power_user': {
                'capabilities': ['app:login', 'app:profile.read', 'app:profile.write', 'integrations:connect']
            },
            'admin': {
                'capabilities': ['*']
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        return f.name

@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()

@pytest.fixture
def rbac_service(db_session, test_rbac_config):
    """Create RBAC service with test database session and config"""
    return RBACService(db_session, test_rbac_config)

@pytest.fixture
def test_user(db_session):
    """Create test user"""
    user = User(email="test@example.com")
    db_session.add(user)
    db_session.commit()
    return user

class TestRBACConfig:
    """Test cases for RBAC Configuration"""
    
    def test_config_loading(self, test_rbac_config):
        """Test loading RBAC configuration from file"""
        config = RBACConfig(test_rbac_config)
        
        assert 'viewer' in config.roles
        assert 'user' in config.roles
        assert 'power_user' in config.roles
        assert 'admin' in config.roles
    
    def test_role_hierarchy(self, test_rbac_config):
        """Test role hierarchy building"""
        config = RBACConfig(test_rbac_config)
        
        # Admin should inherit from all roles
        admin_inherited = config.role_hierarchy['admin']
        assert 'viewer' in admin_inherited
        assert 'user' in admin_inherited
        assert 'power_user' in admin_inherited
        assert 'admin' in admin_inherited
        
        # User should inherit from viewer
        user_inherited = config.role_hierarchy['user']
        assert 'viewer' in user_inherited
        assert 'user' in user_inherited
    
    def test_get_role_capabilities(self, test_rbac_config):
        """Test getting role capabilities with inheritance"""
        config = RBACConfig(test_rbac_config)
        
        # Viewer capabilities
        viewer_caps = config.get_role_capabilities('viewer')
        assert 'app:login' in viewer_caps
        assert 'app:profile.read' in viewer_caps
        
        # User capabilities (should include viewer capabilities)
        user_caps = config.get_role_capabilities('user')
        assert 'app:login' in user_caps
        assert 'app:profile.read' in user_caps
        assert 'app:profile.write' in user_caps
        
        # Admin capabilities (wildcard)
        admin_caps = config.get_role_capabilities('admin')
        assert '*' in admin_caps
    
    def test_has_capability(self, test_rbac_config):
        """Test capability checking logic"""
        config = RBACConfig(test_rbac_config)
        
        # Direct capability match
        user_caps = {'app:login', 'app:profile.read'}
        assert config.has_capability(user_caps, 'app:login') is True
        assert config.has_capability(user_caps, 'app:profile.write') is False
        
        # Wildcard admin capability
        admin_caps = {'*'}
        assert config.has_capability(admin_caps, 'any:capability') is True
        
        # Pattern matching
        pattern_caps = {'app:*'}
        assert config.has_capability(pattern_caps, 'app:login') is True
        assert config.has_capability(pattern_caps, 'integrations:connect') is False

class TestRBACService:
    """Test cases for RBAC Service"""
    
    def test_assign_role(self, rbac_service, test_user):
        """Test assigning role to user"""
        success = rbac_service.assign_role(test_user.id, 'user', 'tenant1')
        assert success is True
        
        # Check role was assigned
        roles = rbac_service.get_user_roles(test_user.id, 'tenant1')
        assert 'user' in roles
    
    def test_assign_invalid_role(self, rbac_service, test_user):
        """Test assigning invalid role raises error"""
        with pytest.raises(ValueError, match="Role invalid_role not configured"):
            rbac_service.assign_role(test_user.id, 'invalid_role', 'tenant1')
    
    def test_update_existing_role(self, rbac_service, test_user):
        """Test updating existing role assignment"""
        # Assign initial role
        rbac_service.assign_role(test_user.id, 'viewer', 'tenant1')
        roles = rbac_service.get_user_roles(test_user.id, 'tenant1')
        assert 'viewer' in roles
        
        # Update to different role
        rbac_service.assign_role(test_user.id, 'user', 'tenant1')
        roles = rbac_service.get_user_roles(test_user.id, 'tenant1')
        assert 'user' in roles
        assert 'viewer' not in roles
    
    def test_get_user_roles_global(self, rbac_service, test_user):
        """Test getting global user roles"""
        rbac_service.assign_role(test_user.id, 'admin', None)  # Global role
        
        roles = rbac_service.get_user_roles(test_user.id, None)
        assert 'admin' in roles
    
    def test_get_user_roles_tenant_specific(self, rbac_service, test_user):
        """Test getting tenant-specific user roles"""
        rbac_service.assign_role(test_user.id, 'user', 'tenant1')
        rbac_service.assign_role(test_user.id, 'admin', None)  # Global role
        
        # Should get both tenant and global roles
        roles = rbac_service.get_user_roles(test_user.id, 'tenant1')
        assert 'user' in roles
        assert 'admin' in roles
        
        # Different tenant should only get global roles
        roles = rbac_service.get_user_roles(test_user.id, 'tenant2')
        assert 'admin' in roles
        assert 'user' not in roles
    
    def test_get_user_capabilities(self, rbac_service, test_user):
        """Test getting user capabilities"""
        rbac_service.assign_role(test_user.id, 'user', 'tenant1')
        
        capabilities = rbac_service.get_user_capabilities(test_user.id, 'tenant1')
        assert 'app:login' in capabilities
        assert 'app:profile.read' in capabilities
        assert 'app:profile.write' in capabilities
    
    def test_check_capability(self, rbac_service, test_user):
        """Test checking user capability"""
        rbac_service.assign_role(test_user.id, 'user', 'tenant1')
        
        # User should have these capabilities
        assert rbac_service.check_capability(test_user.id, 'app:login', 'tenant1') is True
        assert rbac_service.check_capability(test_user.id, 'app:profile.write', 'tenant1') is True
        
        # User should not have admin capabilities
        assert rbac_service.check_capability(test_user.id, 'admin:users.delete', 'tenant1') is False
    
    def test_check_capability_admin_wildcard(self, rbac_service, test_user):
        """Test admin wildcard capability checking"""
        rbac_service.assign_role(test_user.id, 'admin', 'tenant1')
        
        # Admin should have any capability
        assert rbac_service.check_capability(test_user.id, 'any:capability', 'tenant1') is True
        assert rbac_service.check_capability(test_user.id, 'admin:users.delete', 'tenant1') is True
    
    def test_remove_role(self, rbac_service, test_user):
        """Test removing user role"""
        rbac_service.assign_role(test_user.id, 'user', 'tenant1')
        
        # Verify role exists
        roles = rbac_service.get_user_roles(test_user.id, 'tenant1')
        assert 'user' in roles
        
        # Remove role
        success = rbac_service.remove_role(test_user.id, 'tenant1')
        assert success is True
        
        # Verify role removed
        roles = rbac_service.get_user_roles(test_user.id, 'tenant1')
        assert 'user' not in roles
    
    def test_remove_nonexistent_role(self, rbac_service, test_user):
        """Test removing non-existent role"""
        success = rbac_service.remove_role(test_user.id, 'tenant1')
        assert success is False
    
    def test_get_role_definition(self, rbac_service):
        """Test getting role definition"""
        role_def = rbac_service.get_role_definition('user')
        
        assert role_def['role'] == 'user'
        assert 'app:login' in role_def['capabilities']
        assert 'app:profile.write' in role_def['capabilities']
        assert 'viewer' in role_def['inherited_from']
    
    def test_get_invalid_role_definition(self, rbac_service):
        """Test getting invalid role definition"""
        role_def = rbac_service.get_role_definition('invalid_role')
        assert role_def == {}
    
    def test_list_available_roles(self, rbac_service):
        """Test listing available roles"""
        roles = rbac_service.list_available_roles()
        
        assert 'viewer' in roles
        assert 'user' in roles
        assert 'power_user' in roles
        assert 'admin' in roles
    
    def test_validate_capability_format(self, rbac_service):
        """Test capability format validation"""
        # Valid formats
        assert rbac_service.validate_capability_format('app:login') is True
        assert rbac_service.validate_capability_format('admin:*') is True
        assert rbac_service.validate_capability_format('*') is True
        assert rbac_service.validate_capability_format('namespace_1:action-2') is True
        
        # Invalid formats
        assert rbac_service.validate_capability_format('') is False
        assert rbac_service.validate_capability_format('no_colon') is False
        assert rbac_service.validate_capability_format('too:many:colons') is False
        assert rbac_service.validate_capability_format('app:') is False
        assert rbac_service.validate_capability_format(':action') is False
        assert rbac_service.validate_capability_format('app:action@invalid') is False
    
    def test_create_custom_role(self, rbac_service):
        """Test creating custom role"""
        capabilities = ['custom:read', 'custom:write']
        success = rbac_service.create_custom_role('custom_role', capabilities, 'Test custom role')
        
        assert success is True
        
        # Verify role was created
        roles = rbac_service.list_available_roles()
        assert 'custom_role' in roles
        
        # Verify role definition
        role_def = rbac_service.get_role_definition('custom_role')
        assert role_def['role'] == 'custom_role'
        assert 'custom:read' in role_def['capabilities']
        assert 'custom:write' in role_def['capabilities']
    
    def test_create_duplicate_custom_role(self, rbac_service):
        """Test creating duplicate custom role fails"""
        capabilities = ['custom:read']
        
        # Create first role
        success = rbac_service.create_custom_role('duplicate_role', capabilities)
        assert success is True
        
        # Try to create duplicate
        success = rbac_service.create_custom_role('duplicate_role', capabilities)
        assert success is False
    
    def test_create_custom_role_invalid_capabilities(self, rbac_service):
        """Test creating custom role with invalid capabilities fails"""
        invalid_capabilities = ['invalid_format', 'app:valid']
        
        success = rbac_service.create_custom_role('invalid_role', invalid_capabilities)
        assert success is False
    
    def test_role_inheritance_capabilities(self, rbac_service, test_user):
        """Test that role inheritance works correctly for capabilities"""
        rbac_service.assign_role(test_user.id, 'power_user', 'tenant1')
        
        capabilities = rbac_service.get_user_capabilities(test_user.id, 'tenant1')
        
        # Should have viewer capabilities (inherited)
        assert 'app:login' in capabilities
        assert 'app:profile.read' in capabilities
        
        # Should have user capabilities (inherited)
        assert 'app:profile.write' in capabilities
        
        # Should have power_user capabilities (direct)
        assert 'integrations:connect' in capabilities
    
    def test_multiple_tenant_isolation(self, rbac_service, test_user):
        """Test that tenant roles are properly isolated"""
        rbac_service.assign_role(test_user.id, 'user', 'tenant1')
        rbac_service.assign_role(test_user.id, 'admin', 'tenant2')
        
        # Check tenant1 capabilities
        assert rbac_service.check_capability(test_user.id, 'app:profile.write', 'tenant1') is True
        assert rbac_service.check_capability(test_user.id, 'admin:users.delete', 'tenant1') is False
        
        # Check tenant2 capabilities
        assert rbac_service.check_capability(test_user.id, 'admin:users.delete', 'tenant2') is True
        
        # Check roles are isolated
        tenant1_roles = rbac_service.get_user_roles(test_user.id, 'tenant1')
        tenant2_roles = rbac_service.get_user_roles(test_user.id, 'tenant2')
        
        assert 'user' in tenant1_roles
        assert 'admin' not in tenant1_roles
        assert 'admin' in tenant2_roles
        assert 'user' not in tenant2_roles