"""
Property Tests for Dynamic Scope Management

This module contains property-based tests for the dynamic scope management system
using Hypothesis to validate universal correctness properties.
"""

import pytest
import os
import sys
from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
from typing import Dict, List, Set
import uuid

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Create test base and models
TestBase = declarative_base()

# Import models after setting up test base
from models.user import User, Session, TenantMembership
from services.scope_manager import ScopeVersionManager, ScopeChange
from services.scope_config import ScopeConfig

# Override the base for testing
User.__table__.metadata = TestBase.metadata
Session.__table__.metadata = TestBase.metadata
TenantMembership.__table__.metadata = TestBase.metadata

# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def setup_test_db():
    """Set up test database"""
    TestBase.metadata.create_all(bind=test_engine)
    return TestSessionLocal()

# Hypothesis strategies
user_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
tenant_id_strategy = st.one_of(st.none(), st.text(min_size=1, max_size=50))
capability_strategy = st.text(min_size=3, max_size=30).filter(lambda x: ':' in x and len(x.split(':')) == 2)
role_strategy = st.sampled_from(['viewer', 'user', 'power_user', 'admin'])
version_strategy = st.integers(min_value=1, max_value=1000)

@st.composite
def scope_change_strategy(draw):
    """Generate valid scope change data"""
    user_id = draw(user_id_strategy)
    tenant_id = draw(tenant_id_strategy)
    old_version = draw(version_strategy)
    new_version = draw(st.integers(min_value=old_version + 1, max_value=old_version + 10))
    capabilities = draw(st.lists(capability_strategy, min_size=0, max_size=10, unique=True))
    roles = draw(st.lists(role_strategy, min_size=0, max_size=3, unique=True))
    change_type = draw(st.sampled_from(['added', 'removed', 'modified']))
    
    return ScopeChange(
        user_id=user_id,
        tenant_id=tenant_id,
        old_version=old_version,
        new_version=new_version,
        changed_capabilities=capabilities,
        changed_roles=roles,
        change_type=change_type,
        timestamp=datetime.utcnow()
    )

class TestScopeVersionManagement:
    """Property tests for scope version management"""
    
    def setup_method(self):
        """Set up test environment"""
        self.db = setup_test_db()
        self.scope_manager = ScopeVersionManager(self.db)
    
    def teardown_method(self):
        """Clean up test environment"""
        self.db.close()
    
    @given(
        user_id=user_id_strategy,
        tenant_id=tenant_id_strategy,
        capabilities=st.lists(capability_strategy, min_size=0, max_size=10, unique=True),
        roles=st.lists(role_strategy, min_size=0, max_size=3, unique=True)
    )
    @settings(max_examples=50)
    def test_property_18_scope_version_monotonic_increase(self, user_id, tenant_id, capabilities, roles):
        """
        Property 18: Dynamic Scope Version Management
        
        Validates that scope versions always increase monotonically for a user
        and that version changes are properly tracked.
        """
        # Get initial version
        initial_version = self.scope_manager.get_user_scope_version(user_id, tenant_id)
        
        # Update scope multiple times
        versions = [initial_version]
        for i in range(3):
            # Modify capabilities slightly each time
            modified_capabilities = capabilities + [f"test:action_{i}"]
            new_version = self.scope_manager.update_user_scope(
                user_id, modified_capabilities, roles, tenant_id
            )
            versions.append(new_version)
        
        # Verify monotonic increase
        for i in range(1, len(versions)):
            assert versions[i] >= versions[i-1], f"Version decreased: {versions[i-1]} -> {versions[i]}"
        
        # Verify final version is greater than initial
        final_version = self.scope_manager.get_user_scope_version(user_id, tenant_id)
        assert final_version >= initial_version, "Final version should be >= initial version"
    
    @given(
        user_id=user_id_strategy,
        tenant_id=tenant_id_strategy,
        capabilities=st.lists(capability_strategy, min_size=1, max_size=5, unique=True),
        roles=st.lists(role_strategy, min_size=1, max_size=2, unique=True)
    )
    @settings(max_examples=30)
    def test_property_scope_change_detection(self, user_id, tenant_id, capabilities, roles):
        """
        Property: Scope Change Detection Accuracy
        
        Validates that scope changes are accurately detected and only
        trigger version increments when actual changes occur.
        """
        # Set initial scope
        initial_version = self.scope_manager.update_user_scope(
            user_id, capabilities, roles, tenant_id
        )
        
        # Update with same scope - should not increment version
        same_version = self.scope_manager.update_user_scope(
            user_id, capabilities, roles, tenant_id
        )
        assert same_version == initial_version, "Version should not change for identical scope"
        
        # Update with different capabilities - should increment version
        new_capabilities = capabilities + ["test:new_action"]
        new_version = self.scope_manager.update_user_scope(
            user_id, new_capabilities, roles, tenant_id
        )
        assert new_version > initial_version, "Version should increment for scope changes"
        
        # Update with different roles - should increment version
        new_roles = roles + ["admin"] if "admin" not in roles else roles[:-1]
        newer_version = self.scope_manager.update_user_scope(
            user_id, new_capabilities, new_roles, tenant_id
        )
        assert newer_version > new_version, "Version should increment for role changes"
    
    @given(
        user_id=user_id_strategy,
        tenant_id=tenant_id_strategy,
        session_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=20)
    def test_property_session_invalidation_consistency(self, user_id, tenant_id, session_count):
        """
        Property: Session Invalidation Consistency
        
        Validates that session invalidation works consistently across
        multiple sessions and scope version changes.
        """
        # Create user
        user = User(id=user_id, email=f"{user_id}@test.com")
        self.db.add(user)
        self.db.commit()
        
        # Create multiple sessions with different scope versions
        sessions = []
        for i in range(session_count):
            session = Session(
                id=str(uuid.uuid4()),
                user_id=user_id,
                tenant_id=tenant_id,
                access_token=f"token_{i}",
                expires_at=datetime.utcnow() + timedelta(hours=1),
                scope_version=i + 1,
                is_active=True
            )
            sessions.append(session)
            self.db.add(session)
        
        self.db.commit()
        
        # Update user scope to higher version
        new_version = session_count + 5
        self.scope_manager.update_user_scope(
            user_id, ["test:capability"], ["user"], tenant_id
        )
        
        # Invalidate sessions with outdated scope versions
        invalidated_count = self.scope_manager.invalidate_user_sessions(
            user_id, tenant_id, new_version
        )
        
        # Verify all sessions were invalidated (since they all have lower versions)
        assert invalidated_count == session_count, f"Expected {session_count} invalidated, got {invalidated_count}"
        
        # Verify sessions are marked as inactive
        active_sessions = self.db.query(Session).filter(
            Session.user_id == user_id,
            Session.is_active == True
        ).count()
        assert active_sessions == 0, "All sessions should be inactive"
    
    @given(
        users=st.lists(
            st.tuples(user_id_strategy, tenant_id_strategy),
            min_size=2, max_size=5, unique=True
        )
    )
    @settings(max_examples=15)
    def test_property_scope_isolation_between_users(self, users):
        """
        Property: Scope Version Isolation
        
        Validates that scope version changes for one user do not
        affect scope versions for other users.
        """
        # Set initial scope versions for all users
        initial_versions = {}
        for user_id, tenant_id in users:
            version = self.scope_manager.update_user_scope(
                user_id, ["test:read"], ["user"], tenant_id
            )
            initial_versions[(user_id, tenant_id)] = version
        
        # Update scope for first user only
        first_user_id, first_tenant_id = users[0]
        new_version = self.scope_manager.update_user_scope(
            first_user_id, ["test:read", "test:write"], ["power_user"], first_tenant_id
        )
        
        # Verify first user's version increased
        assert new_version > initial_versions[(first_user_id, first_tenant_id)]
        
        # Verify other users' versions unchanged
        for user_id, tenant_id in users[1:]:
            current_version = self.scope_manager.get_user_scope_version(user_id, tenant_id)
            expected_version = initial_versions[(user_id, tenant_id)]
            assert current_version == expected_version, f"User {user_id} version changed unexpectedly"
    
    @given(
        user_id=user_id_strategy,
        tenant_ids=st.lists(st.text(min_size=1, max_size=20), min_size=2, max_size=4, unique=True)
    )
    @settings(max_examples=15)
    def test_property_tenant_scope_isolation(self, user_id, tenant_ids):
        """
        Property: Tenant Scope Isolation
        
        Validates that scope versions are properly isolated between
        different tenants for the same user.
        """
        # Set different scope versions for same user in different tenants
        tenant_versions = {}
        for i, tenant_id in enumerate(tenant_ids):
            capabilities = [f"tenant_{i}:read", f"tenant_{i}:write"]
            version = self.scope_manager.update_user_scope(
                user_id, capabilities, ["user"], tenant_id
            )
            tenant_versions[tenant_id] = version
        
        # Update scope for first tenant only
        first_tenant = tenant_ids[0]
        new_capabilities = [f"tenant_0:read", f"tenant_0:write", f"tenant_0:admin"]
        new_version = self.scope_manager.update_user_scope(
            user_id, new_capabilities, ["admin"], first_tenant
        )
        
        # Verify first tenant's version increased
        assert new_version > tenant_versions[first_tenant]
        
        # Verify other tenants' versions unchanged
        for tenant_id in tenant_ids[1:]:
            current_version = self.scope_manager.get_user_scope_version(user_id, tenant_id)
            expected_version = tenant_versions[tenant_id]
            assert current_version == expected_version, f"Tenant {tenant_id} version changed unexpectedly"

class TestScopePollingAndInvalidation:
    """Property tests for scope polling and session invalidation"""
    
    def setup_method(self):
        """Set up test environment"""
        self.db = setup_test_db()
        # Create config with shorter intervals for testing
        config = ScopeConfig()
        config.polling.interval_seconds = 1
        config.version_checking.max_age_minutes = 1
        self.scope_manager = ScopeVersionManager(self.db, config)
    
    def teardown_method(self):
        """Clean up test environment"""
        self.db.close()
    
    @given(
        user_id=user_id_strategy,
        tenant_id=tenant_id_strategy,
        initial_capabilities=st.lists(capability_strategy, min_size=1, max_size=3, unique=True)
    )
    @settings(max_examples=20)
    def test_property_20_scope_polling_and_invalidation(self, user_id, tenant_id, initial_capabilities):
        """
        Property 20: Scope Polling and Invalidation
        
        Validates that the scope polling mechanism correctly identifies
        sessions that need updates and invalidates outdated sessions.
        """
        # Create user
        user = User(id=user_id, email=f"{user_id}@test.com")
        self.db.add(user)
        self.db.commit()
        
        # Set initial scope
        initial_version = self.scope_manager.update_user_scope(
            user_id, initial_capabilities, ["user"], tenant_id
        )
        
        # Create session with current scope version
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            access_token="test_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            scope_version=initial_version,
            last_scope_check=datetime.utcnow() - timedelta(minutes=2),  # Old check
            is_active=True
        )
        self.db.add(session)
        self.db.commit()
        
        # Update user scope to trigger version change
        new_capabilities = initial_capabilities + ["test:new_action"]
        new_version = self.scope_manager.update_user_scope(
            user_id, new_capabilities, ["power_user"], tenant_id
        )
        
        # Verify version increased
        assert new_version > initial_version
        
        # Get sessions needing scope update
        sessions_to_update = self.scope_manager.get_sessions_needing_scope_update()
        
        # Should find our session since it has old scope version and old check time
        session_found = any(
            s['user_id'] == user_id and s['tenant_id'] == tenant_id
            for s in sessions_to_update
        )
        assert session_found, "Session with outdated scope should be found"
        
        # Invalidate outdated sessions
        invalidated_count = self.scope_manager.invalidate_user_sessions(
            user_id, tenant_id, new_version
        )
        
        # Should have invalidated our session
        assert invalidated_count == 1, f"Expected 1 session invalidated, got {invalidated_count}"
        
        # Verify session is now inactive
        updated_session = self.db.query(Session).filter(Session.id == session.id).first()
        assert not updated_session.is_active, "Session should be inactive after invalidation"
    
    @given(
        user_id=user_id_strategy,
        tenant_id=tenant_id_strategy,
        change_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=15)
    def test_property_scope_change_event_processing(self, user_id, tenant_id, change_count):
        """
        Property: Scope Change Event Processing
        
        Validates that scope change events are properly created,
        tracked, and marked as processed.
        """
        initial_capabilities = ["test:read"]
        
        # Create multiple scope changes
        for i in range(change_count):
            capabilities = initial_capabilities + [f"test:action_{i}"]
            self.scope_manager.update_user_scope(
                user_id, capabilities, ["user"], tenant_id
            )
        
        # Get pending scope changes
        pending_changes = self.scope_manager.get_pending_scope_changes()
        
        # Should have created change events
        user_changes = [
            change for change in pending_changes
            if change.user_id == user_id and change.tenant_id == tenant_id
        ]
        assert len(user_changes) >= change_count, f"Expected >= {change_count} changes, got {len(user_changes)}"
        
        # Verify change events have proper structure
        for change in user_changes:
            assert change.user_id == user_id
            assert change.tenant_id == tenant_id
            assert change.new_version > change.old_version
            assert change.change_type in ['added', 'removed', 'modified']
            assert isinstance(change.changed_capabilities, list)
            assert isinstance(change.changed_roles, list)
    
    @given(
        user_id=user_id_strategy,
        tenant_id=tenant_id_strategy,
        session_versions=st.lists(st.integers(min_value=1, max_value=10), min_size=2, max_size=5)
    )
    @settings(max_examples=15)
    def test_property_selective_session_invalidation(self, user_id, tenant_id, session_versions):
        """
        Property: Selective Session Invalidation
        
        Validates that only sessions with outdated scope versions
        are invalidated, while current sessions remain active.
        """
        # Create user
        user = User(id=user_id, email=f"{user_id}@test.com")
        self.db.add(user)
        self.db.commit()
        
        # Create sessions with different scope versions
        sessions = []
        for i, version in enumerate(session_versions):
            session = Session(
                id=str(uuid.uuid4()),
                user_id=user_id,
                tenant_id=tenant_id,
                access_token=f"token_{i}",
                expires_at=datetime.utcnow() + timedelta(hours=1),
                scope_version=version,
                is_active=True
            )
            sessions.append(session)
            self.db.add(session)
        
        self.db.commit()
        
        # Set minimum required version to middle value
        min_version = max(session_versions) - 1 if len(session_versions) > 1 else max(session_versions)
        
        # Invalidate sessions with outdated versions
        invalidated_count = self.scope_manager.invalidate_user_sessions(
            user_id, tenant_id, min_version
        )
        
        # Count expected invalidations
        expected_invalidations = sum(1 for v in session_versions if v < min_version)
        assert invalidated_count == expected_invalidations, f"Expected {expected_invalidations} invalidations, got {invalidated_count}"
        
        # Verify correct sessions were invalidated
        for session in sessions:
            updated_session = self.db.query(Session).filter(Session.id == session.id).first()
            if session.scope_version < min_version:
                assert not updated_session.is_active, f"Session with version {session.scope_version} should be inactive"
            else:
                assert updated_session.is_active, f"Session with version {session.scope_version} should remain active"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])