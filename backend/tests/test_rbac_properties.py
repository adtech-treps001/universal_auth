"""
Property-Based Tests for RBAC System

This module contains property-based tests that validate universal correctness
properties for the role-based access control system using Hypothesis.

Feature: universal-auth, Properties 11, 12: RBAC functionality
"""

import pytest
import tempfile
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hypothesis import given, strategies as st, assume, settings
from models.user import Base, User, TenantMembership
from services.rbac_service import RBACService, RBACConfig
from datetime import datetime


def create_test_rbac_service():
    """Create RBAC service with in-memory database for property testing"""
    # Create test config
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
        config_path = f.name
    
    # Create database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    return RBACService(session, config_path), session


class TestRBACProperties:
    """Property-based tests for RBAC System correctness"""
    
    # Strategy for generating valid role names
    valid_roles = st.sampled_from(['viewer', 'user', 'power_user', 'admin'])
    
    # Strategy for generating user IDs
    user_ids = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    
    # Strategy for generating tenant IDs
    tenant_ids = st.one_of(
        st.none(),
        st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    
    # Strategy for generating capability strings
    valid_capabilities = st.one_of(
        st.just('*'),
        st.sampled_from([
            'app:login', 'app:profile.read', 'app:profile.write',
            'integrations:connect', 'admin:users.read', 'admin:users.write',
            'admin:users.delete', 'admin:roles.manage'
        ])
    )
    
    @given(
        user_id=user_ids,
        role=valid_roles,
        tenant_id=tenant_ids
    )
    @settings(max_examples=20, deadline=3000)
    def test_role_capability_mapping_consistency_property(self, user_id, role, tenant_id):
        """
        Property 11: Role-Capability Mapping Consistency
        
        For any user role assignment, the system should grant exactly the 
        capabilities defined for that role in the RBAC configuration, 
        no more and no less.
        
        **Feature: universal-auth, Property 11: Role-Capability Mapping Consistency**
        **Validates: Requirements 4.1**
        """
        rbac_service, session = create_test_rbac_service()
        
        try:
            # Create test user
            user = User(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
            session.commit()
            
            # Assign role to user
            success = rbac_service.assign_role(user_id, role, tenant_id)
            assert success is True, f"Failed to assign role {role} to user {user_id}"
            
            # Get user capabilities
            user_capabilities = rbac_service.get_user_capabilities(user_id, tenant_id)
            
            # Get expected capabilities from configuration
            expected_capabilities = rbac_service.config.get_role_capabilities(role)
            
            # Verify exact match
            assert user_capabilities == expected_capabilities, \
                f"User capabilities {user_capabilities} don't match expected {expected_capabilities} for role {role}"
            
            # Verify each expected capability is present
            for capability in expected_capabilities:
                assert rbac_service.check_capability(user_id, capability, tenant_id), \
                    f"User should have capability {capability} for role {role}"
            
            # For non-admin roles, verify user doesn't have admin capabilities
            if role != 'admin':
                admin_capabilities = ['admin:users.delete', 'admin:roles.manage', 'admin:system.config']
                for admin_cap in admin_capabilities:
                    if admin_cap not in expected_capabilities:
                        assert not rbac_service.check_capability(user_id, admin_cap, tenant_id), \
                            f"User with role {role} should not have admin capability {admin_cap}"
            
        finally:
            session.close()
    
    @given(
        user_id=user_ids,
        capability=valid_capabilities,
        tenant_id=tenant_ids
    )
    @settings(max_examples=25, deadline=3000)
    def test_authorization_verification_accuracy_property(self, user_id, capability, tenant_id):
        """
        Property 12: Authorization Verification Accuracy
        
        For any protected resource access attempt, the system should verify 
        user capabilities against the required permissions and allow access 
        only when capabilities are sufficient.
        
        **Feature: universal-auth, Property 12: Authorization Verification Accuracy**
        **Validates: Requirements 4.2**
        """
        rbac_service, session = create_test_rbac_service()
        
        try:
            # Create test user
            user = User(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
            session.commit()
            
            # Test with no role assigned - should have no capabilities
            has_capability_no_role = rbac_service.check_capability(user_id, capability, tenant_id)
            assert has_capability_no_role is False, \
                f"User without role should not have capability {capability}"
            
            # Test each role assignment
            for role in ['viewer', 'user', 'power_user', 'admin']:
                # Assign role
                rbac_service.assign_role(user_id, role, tenant_id)
                
                # Get role's capabilities
                role_capabilities = rbac_service.config.get_role_capabilities(role)
                
                # Check capability
                has_capability = rbac_service.check_capability(user_id, capability, tenant_id)
                
                # Determine if user should have this capability
                should_have_capability = rbac_service.config.has_capability(role_capabilities, capability)
                
                assert has_capability == should_have_capability, \
                    f"Capability check mismatch for role {role} and capability {capability}: " \
                    f"expected {should_have_capability}, got {has_capability}"
                
                # Verify consistency with get_user_capabilities
                user_capabilities = rbac_service.get_user_capabilities(user_id, tenant_id)
                capability_in_list = rbac_service.config.has_capability(user_capabilities, capability)
                
                assert has_capability == capability_in_list, \
                    f"Inconsistency between check_capability and get_user_capabilities for {capability}"
            
        finally:
            session.close()
    
    @given(
        user_id=user_ids,
        role1=valid_roles,
        role2=valid_roles,
        tenant_id=tenant_ids
    )
    @settings(max_examples=15, deadline=3000)
    def test_role_update_consistency_property(self, user_id, role1, role2, tenant_id):
        """
        Property: Role updates should be consistent and atomic
        
        For any user role update, the system should atomically replace 
        the old role with the new role and update capabilities accordingly.
        
        **Feature: universal-auth, Property 11: Role-Capability Mapping Consistency**
        **Validates: Requirements 4.1**
        """
        rbac_service, session = create_test_rbac_service()
        
        try:
            # Create test user
            user = User(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
            session.commit()
            
            # Assign first role
            rbac_service.assign_role(user_id, role1, tenant_id)
            
            # Get capabilities for first role
            capabilities1 = rbac_service.get_user_capabilities(user_id, tenant_id)
            expected1 = rbac_service.config.get_role_capabilities(role1)
            assert capabilities1 == expected1
            
            # Update to second role
            rbac_service.assign_role(user_id, role2, tenant_id)
            
            # Get capabilities for second role
            capabilities2 = rbac_service.get_user_capabilities(user_id, tenant_id)
            expected2 = rbac_service.config.get_role_capabilities(role2)
            assert capabilities2 == expected2
            
            # Verify user has exactly one role
            user_roles = rbac_service.get_user_roles(user_id, tenant_id)
            assert len(user_roles) == 1, f"User should have exactly one role, got {user_roles}"
            assert role2 in user_roles, f"User should have role {role2}, got {user_roles}"
            assert role1 not in user_roles or role1 == role2, \
                f"User should not have old role {role1} unless it's the same as new role"
            
        finally:
            session.close()
    
    @given(
        user_id=user_ids,
        role=valid_roles,
        tenant1=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        tenant2=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=15, deadline=3000)
    def test_tenant_isolation_property(self, user_id, role, tenant1, tenant2):
        """
        Property: Tenant isolation should be maintained
        
        For any user with roles in different tenants, capabilities should 
        be isolated per tenant context.
        
        **Feature: universal-auth, Property 12: Authorization Verification Accuracy**
        **Validates: Requirements 4.2**
        """
        assume(tenant1 != tenant2)  # Ensure different tenants
        
        rbac_service, session = create_test_rbac_service()
        
        try:
            # Create test user
            user = User(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
            session.commit()
            
            # Assign role in tenant1 only
            rbac_service.assign_role(user_id, role, tenant1)
            
            # Check capabilities in tenant1
            capabilities_t1 = rbac_service.get_user_capabilities(user_id, tenant1)
            expected_caps = rbac_service.config.get_role_capabilities(role)
            assert capabilities_t1 == expected_caps, \
                f"User should have role capabilities in tenant1"
            
            # Check capabilities in tenant2 (should be empty)
            capabilities_t2 = rbac_service.get_user_capabilities(user_id, tenant2)
            assert len(capabilities_t2) == 0, \
                f"User should have no capabilities in tenant2, got {capabilities_t2}"
            
            # Check specific capability in both tenants
            test_capability = list(expected_caps)[0] if expected_caps else 'app:login'
            
            has_cap_t1 = rbac_service.check_capability(user_id, test_capability, tenant1)
            has_cap_t2 = rbac_service.check_capability(user_id, test_capability, tenant2)
            
            if '*' in expected_caps or test_capability in expected_caps:
                assert has_cap_t1 is True, f"User should have {test_capability} in tenant1"
            
            assert has_cap_t2 is False, f"User should not have {test_capability} in tenant2"
            
        finally:
            session.close()
    
    @given(
        user_id=user_ids,
        role=valid_roles
    )
    @settings(max_examples=15, deadline=3000)
    def test_role_removal_cleanup_property(self, user_id, role):
        """
        Property: Role removal should clean up all associated capabilities
        
        For any user role removal, the system should remove all capabilities 
        associated with that role.
        
        **Feature: universal-auth, Property 11: Role-Capability Mapping Consistency**
        **Validates: Requirements 4.1**
        """
        rbac_service, session = create_test_rbac_service()
        
        try:
            # Create test user
            user = User(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
            session.commit()
            
            tenant_id = "test_tenant"
            
            # Assign role
            rbac_service.assign_role(user_id, role, tenant_id)
            
            # Verify user has capabilities
            capabilities_before = rbac_service.get_user_capabilities(user_id, tenant_id)
            expected_caps = rbac_service.config.get_role_capabilities(role)
            assert capabilities_before == expected_caps
            
            # Remove role
            success = rbac_service.remove_role(user_id, tenant_id)
            assert success is True
            
            # Verify user has no capabilities
            capabilities_after = rbac_service.get_user_capabilities(user_id, tenant_id)
            assert len(capabilities_after) == 0, \
                f"User should have no capabilities after role removal, got {capabilities_after}"
            
            # Verify user has no roles
            roles_after = rbac_service.get_user_roles(user_id, tenant_id)
            assert len(roles_after) == 0, \
                f"User should have no roles after removal, got {roles_after}"
            
            # Test specific capability checks
            for capability in expected_caps:
                if capability != '*':  # Skip wildcard for specific tests
                    has_capability = rbac_service.check_capability(user_id, capability, tenant_id)
                    assert has_capability is False, \
                        f"User should not have capability {capability} after role removal"
            
        finally:
            session.close()
    
    @given(
        user_id=user_ids,
        capabilities=st.lists(
            st.text(min_size=3, max_size=20).filter(lambda x: ':' in x and len(x.split(':')) == 2),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    @settings(max_examples=10, deadline=3000)
    def test_custom_role_capability_consistency_property(self, user_id, capabilities):
        """
        Property: Custom roles should maintain capability consistency
        
        For any custom role creation, the system should grant exactly 
        the specified capabilities to users with that role.
        
        **Feature: universal-auth, Property 11: Role-Capability Mapping Consistency**
        **Validates: Requirements 4.1**
        """
        rbac_service, session = create_test_rbac_service()
        
        try:
            # Create test user
            user = User(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
            session.commit()
            
            # Create custom role
            custom_role_name = f"custom_role_{user_id[:10]}"
            success = rbac_service.create_custom_role(custom_role_name, capabilities)
            
            if success:
                # Assign custom role to user
                rbac_service.assign_role(user_id, custom_role_name, "test_tenant")
                
                # Get user capabilities
                user_capabilities = rbac_service.get_user_capabilities(user_id, "test_tenant")
                expected_capabilities = set(capabilities)
                
                assert user_capabilities == expected_capabilities, \
                    f"Custom role capabilities mismatch: expected {expected_capabilities}, got {user_capabilities}"
                
                # Test each capability individually
                for capability in capabilities:
                    has_capability = rbac_service.check_capability(user_id, capability, "test_tenant")
                    assert has_capability is True, \
                        f"User should have custom capability {capability}"
                
                # Test that user doesn't have capabilities not in the custom role
                test_other_caps = ['admin:system.delete', 'other:capability']
                for other_cap in test_other_caps:
                    if other_cap not in capabilities:
                        has_other = rbac_service.check_capability(user_id, other_cap, "test_tenant")
                        assert has_other is False, \
                            f"User should not have capability {other_cap} not in custom role"
            
        finally:
            session.close()
    
    @given(
        user_id=user_ids,
        role=valid_roles
    )
    @settings(max_examples=10, deadline=3000)
    def test_role_hierarchy_inheritance_property(self, user_id, role):
        """
        Property: Role hierarchy inheritance should be consistent
        
        For any role assignment, the system should grant all capabilities 
        from the assigned role and all roles it inherits from.
        
        **Feature: universal-auth, Property 11: Role-Capability Mapping Consistency**
        **Validates: Requirements 4.1**
        """
        rbac_service, session = create_test_rbac_service()
        
        try:
            # Create test user
            user = User(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
            session.commit()
            
            # Assign role
            rbac_service.assign_role(user_id, role, "test_tenant")
            
            # Get user capabilities
            user_capabilities = rbac_service.get_user_capabilities(user_id, "test_tenant")
            
            # Get role hierarchy
            role_hierarchy = rbac_service.config.role_hierarchy.get(role, set())
            
            # Collect all capabilities from role and inherited roles
            all_expected_capabilities = set()
            for inherited_role in role_hierarchy:
                if inherited_role in rbac_service.config.roles:
                    role_caps = set(rbac_service.config.roles[inherited_role].get('capabilities', []))
                    all_expected_capabilities.update(role_caps)
            
            # Handle admin wildcard
            if '*' in all_expected_capabilities:
                all_expected_capabilities = {'*'}
            
            assert user_capabilities == all_expected_capabilities, \
                f"Role inheritance mismatch for {role}: expected {all_expected_capabilities}, got {user_capabilities}"
            
            # Test specific inherited capabilities
            if role in ['user', 'power_user', 'admin']:
                # These roles should inherit viewer capabilities
                assert rbac_service.check_capability(user_id, 'app:login', "test_tenant"), \
                    f"Role {role} should inherit app:login from viewer"
                assert rbac_service.check_capability(user_id, 'app:profile.read', "test_tenant"), \
                    f"Role {role} should inherit app:profile.read from viewer"
            
            if role in ['power_user', 'admin']:
                # These roles should inherit user capabilities
                assert rbac_service.check_capability(user_id, 'app:profile.write', "test_tenant"), \
                    f"Role {role} should inherit app:profile.write from user"
            
        finally:
            session.close()


class TestRBACConfigurationProperties:
    """Property-based tests for RBAC Configuration consistency"""
    
    def test_configuration_structure_consistency(self):
        """
        Property: RBAC configuration should have consistent structure
        
        The configuration should have valid role definitions and 
        all referenced capabilities should be properly formatted.
        """
        rbac_service, session = create_test_rbac_service()
        
        try:
            config = rbac_service.config
            
            # All roles should have capabilities defined
            for role_name, role_def in config.roles.items():
                assert 'capabilities' in role_def, f"Role {role_name} missing capabilities"
                assert isinstance(role_def['capabilities'], list), \
                    f"Role {role_name} capabilities should be a list"
            
            # Role hierarchy should be consistent
            for role, inherited_roles in config.role_hierarchy.items():
                assert role in inherited_roles, f"Role {role} should inherit from itself"
                
                # All inherited roles should exist in configuration
                for inherited_role in inherited_roles:
                    if inherited_role != role:
                        assert inherited_role in config.roles, \
                            f"Inherited role {inherited_role} not found in configuration"
            
            # Capability format validation
            for role_name, role_def in config.roles.items():
                for capability in role_def['capabilities']:
                    if capability != '*':
                        assert rbac_service.validate_capability_format(capability), \
                            f"Invalid capability format: {capability} in role {role_name}"
            
        finally:
            session.close()