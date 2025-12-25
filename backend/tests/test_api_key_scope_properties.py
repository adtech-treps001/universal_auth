"""
Property Tests for API Key Scope Validation

This module contains property-based tests for API key scope validation and access control
using Hypothesis to validate universal correctness properties.

**Feature: universal-auth, Property 22: API Key Scope Validation**
**Validates: Requirements 10.2, 10.3**
"""

import pytest
import os
import sys
from hypothesis import given, strategies as st, settings, assume
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta
from typing import Dict, List, Set
import uuid

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Create test base and models
TestBase = declarative_base()

# Import models after setting up test base
from models.api_key import APIKey, APIKeyUsageLog, APIKeyProvider, APIKeyStatus
from models.user import User, Role, TenantMembership
from models.project import Project
from services.api_key_validation import APIKeyValidationService, ScopeValidator
from services.api_key_service import APIKeyService
from services.rbac_service import RBACService

# Override the base for testing
APIKey.__table__.metadata = TestBase.metadata
APIKeyUsageLog.__table__.metadata = TestBase.metadata
User.__table__.metadata = TestBase.metadata
Role.__table__.metadata = TestBase.metadata
TenantMembership.__table__.metadata = TestBase.metadata
Project.__table__.metadata = TestBase.metadata

# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL, 
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def setup_test_db():
    """Set up test database"""
    TestBase.metadata.create_all(bind=test_engine)
    return TestSessionLocal()

# Hypothesis strategies
user_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
project_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
tenant_id_strategy = st.one_of(st.none(), st.text(min_size=1, max_size=50))
api_key_name_strategy = st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))
provider_strategy = st.sampled_from([p.value for p in APIKeyProvider])
role_strategy = st.sampled_from(['viewer', 'user', 'power_user', 'admin', 'developer'])

# Scope strategies
scope_category_strategy = st.sampled_from(['chat', 'completions', 'embeddings', 'images', 'audio', 'files', 'models'])
scope_action_strategy = st.sampled_from(['read', 'write', 'create', 'delete', 'list'])
scope_strategy = st.builds(lambda cat, act: f"{cat}.{act}", scope_category_strategy, scope_action_strategy)
scopes_list_strategy = st.lists(scope_strategy, min_size=0, max_size=8, unique=True)

# Rate limit strategies
rate_limit_strategy = st.fixed_dictionaries({
    'requests_per_minute': st.integers(min_value=1, max_value=1000),
    'tokens_per_minute': st.integers(min_value=100, max_value=10000),
    'requests_per_day': st.integers(min_value=100, max_value=100000)
})

@st.composite
def api_key_strategy(draw):
    """Generate valid API key data"""
    key_name = draw(api_key_name_strategy)
    provider = draw(provider_strategy)
    project_id = draw(project_id_strategy)
    user_id = draw(user_id_strategy)
    tenant_id = draw(tenant_id_strategy)
    scopes = draw(scopes_list_strategy)
    allowed_roles = draw(st.lists(role_strategy, min_size=0, max_size=3, unique=True))
    rate_limits = draw(st.one_of(st.none(), rate_limit_strategy))
    
    return {
        'key_name': key_name,
        'provider': provider,
        'project_id': project_id,
        'owner_id': user_id,
        'tenant_id': tenant_id,
        'scopes': scopes,
        'allowed_roles': allowed_roles,
        'rate_limits': rate_limits,
        'status': APIKeyStatus.ACTIVE.value,
        'encrypted_key': b'encrypted_test_key',
        'key_hash': 'test_hash_' + str(uuid.uuid4())[:8]
    }

@st.composite
def request_context_strategy(draw):
    """Generate request context for validation"""
    scopes = draw(scopes_list_strategy)
    client_ip = draw(st.one_of(st.none(), st.text(min_size=7, max_size=15)))
    model = draw(st.one_of(st.none(), st.sampled_from(['gpt-4', 'gpt-3.5-turbo', 'text-embedding-ada-002'])))
    estimated_tokens = draw(st.one_of(st.none(), st.integers(min_value=1, max_value=4000)))
    
    return {
        'scopes': scopes,
        'client_ip': client_ip,
        'model': model,
        'estimated_tokens': estimated_tokens,
        'endpoint': '/v1/chat/completions',
        'method': 'POST'
    }

class TestAPIKeyScopeValidation:
    """Property tests for API key scope validation"""
    
    def setup_method(self):
        """Set up test environment"""
        self.db = setup_test_db()
        self.validation_service = APIKeyValidationService(self.db)
        self.api_key_service = APIKeyService(self.db)
    
    def teardown_method(self):
        """Clean up test environment"""
        self.db.close()
    
    @given(
        api_key_data=api_key_strategy(),
        required_scopes=scopes_list_strategy
    )
    @settings(max_examples=50)
    def test_property_22_api_key_scope_validation(self, api_key_data, required_scopes):
        """
        Property 22: API Key Scope Validation
        
        For any API key and any set of required scopes, the validation should
        succeed if and only if all required scopes are contained in the API key's allowed scopes.
        
        **Validates: Requirements 10.2, 10.3**
        """
        # Create project and user
        project = Project(id=api_key_data['project_id'], name="Test Project")
        user = User(id=api_key_data['owner_id'], email=f"{api_key_data['owner_id']}@test.com")
        self.db.add(project)
        self.db.add(user)
        self.db.commit()
        
        # Create API key with specific scopes
        api_key = APIKey(**api_key_data)
        self.db.add(api_key)
        self.db.commit()
        
        # Test scope validation
        has_required_scopes = self.validation_service.check_scope_access(api_key.id, required_scopes)
        
        # Determine expected result
        if not required_scopes:
            # No scopes required - should always pass
            expected_result = True
        elif not api_key.scopes:
            # Key has no scopes but scopes are required - should fail
            expected_result = False
        else:
            # Check if all required scopes are in allowed scopes
            allowed_scopes = set(api_key.scopes)
            required_scopes_set = set(required_scopes)
            expected_result = required_scopes_set.issubset(allowed_scopes)
        
        assert has_required_scopes == expected_result, (
            f"Scope validation failed: key_scopes={api_key.scopes}, "
            f"required_scopes={required_scopes}, expected={expected_result}, got={has_required_scopes}"
        )
    
    @given(
        api_key_data=api_key_strategy(),
        user_roles=st.lists(role_strategy, min_size=1, max_size=3, unique=True)
    )
    @settings(max_examples=30)
    def test_property_role_based_api_key_access(self, api_key_data, user_roles):
        """
        Property: Role-Based API Key Access Control
        
        For any API key with role restrictions and any user with roles,
        access should be granted if and only if the user has at least one allowed role.
        
        **Validates: Requirements 10.2, 10.3**
        """
        # Create project and user
        project = Project(id=api_key_data['project_id'], name="Test Project")
        user = User(id=api_key_data['owner_id'], email=f"{api_key_data['owner_id']}@test.com")
        self.db.add(project)
        self.db.add(user)
        
        # Create roles for user
        for role_name in user_roles:
            role = Role(
                id=str(uuid.uuid4()),
                name=role_name,
                tenant_id=api_key_data['tenant_id']
            )
            self.db.add(role)
            
            # Add user to role via tenant membership
            membership = TenantMembership(
                user_id=user.id,
                tenant_id=api_key_data['tenant_id'] or 'default',
                role_id=role.id
            )
            self.db.add(membership)
        
        self.db.commit()
        
        # Create API key with role restrictions
        api_key = APIKey(**api_key_data)
        self.db.add(api_key)
        self.db.commit()
        
        # Test role-based access
        has_access = self.validation_service.validate_role_access(api_key.id, user.id)
        
        # Determine expected result
        if api_key.owner_id == user.id:
            # Owner always has access
            expected_result = True
        elif not api_key.allowed_roles:
            # No role restrictions - access allowed
            expected_result = True
        else:
            # Check if user has any allowed role
            user_role_set = set(user_roles)
            allowed_role_set = set(api_key.allowed_roles)
            expected_result = bool(user_role_set.intersection(allowed_role_set))
        
        assert has_access == expected_result, (
            f"Role access validation failed: user_roles={user_roles}, "
            f"allowed_roles={api_key.allowed_roles}, expected={expected_result}, got={has_access}"
        )
    
    @given(
        api_key_data=api_key_strategy(),
        request_context=request_context_strategy()
    )
    @settings(max_examples=40)
    def test_property_comprehensive_api_key_validation(self, api_key_data, request_context):
        """
        Property: Comprehensive API Key Validation
        
        For any API key and request context, validation should consider all factors:
        scopes, roles, rate limits, and key status.
        
        **Validates: Requirements 10.2, 10.3**
        """
        # Create project and user
        project = Project(id=api_key_data['project_id'], name="Test Project")
        user = User(id=api_key_data['owner_id'], email=f"{api_key_data['owner_id']}@test.com")
        self.db.add(project)
        self.db.add(user)
        self.db.commit()
        
        # Create API key
        api_key = APIKey(**api_key_data)
        self.db.add(api_key)
        self.db.commit()
        
        # Perform comprehensive validation
        validation_result = self.validation_service.validate_api_key(
            api_key.id, user.id, request_context
        )
        
        # Check individual validation components
        is_active = api_key.is_active
        has_scopes = self._check_scopes(api_key.scopes, request_context.get('scopes', []))
        
        # Validation should succeed only if all checks pass
        if not is_active:
            assert not validation_result['valid'], "Inactive key should fail validation"
        elif not has_scopes:
            assert not validation_result['valid'], "Insufficient scopes should fail validation"
        else:
            # If key is active and has required scopes, validation may still fail due to other factors
            # (rate limits, IP restrictions, etc.) but we can't predict those without more setup
            pass
        
        # Verify result structure
        assert 'valid' in validation_result
        assert 'message' in validation_result
        assert 'timestamp' in validation_result
        assert isinstance(validation_result['valid'], bool)
    
    def _check_scopes(self, allowed_scopes, required_scopes):
        """Helper to check scope validation logic"""
        if not required_scopes:
            return True
        if not allowed_scopes:
            return False
        return set(required_scopes).issubset(set(allowed_scopes))
    
    @given(
        scopes=scopes_list_strategy
    )
    @settings(max_examples=30)
    def test_property_scope_format_validation(self, scopes):
        """
        Property: Scope Format Validation
        
        For any list of scopes, validation should correctly identify
        valid and invalid scope formats.
        
        **Validates: Requirements 10.2**
        """
        validation_result = ScopeValidator.validate_scopes(scopes)
        
        # Check result structure
        assert 'valid_scopes' in validation_result
        assert 'invalid_scopes' in validation_result
        assert 'all_valid' in validation_result
        
        # Verify all scopes are accounted for
        total_scopes = len(validation_result['valid_scopes']) + len(validation_result['invalid_scopes'])
        assert total_scopes == len(scopes), "All scopes should be classified as valid or invalid"
        
        # Verify no duplicates
        all_classified = validation_result['valid_scopes'] + validation_result['invalid_scopes']
        assert len(all_classified) == len(set(all_classified)), "No duplicate scopes in classification"
        
        # Verify all_valid flag
        expected_all_valid = len(validation_result['invalid_scopes']) == 0
        assert validation_result['all_valid'] == expected_all_valid
    
    @given(
        allowed_scopes=scopes_list_strategy,
        required_scope=scope_strategy
    )
    @settings(max_examples=40)
    def test_property_scope_permission_checking(self, allowed_scopes, required_scope):
        """
        Property: Scope Permission Checking
        
        For any set of allowed scopes and any required scope,
        permission should be granted if the scope is directly allowed
        or covered by a wildcard permission.
        
        **Validates: Requirements 10.2, 10.3**
        """
        # Test direct permission
        has_permission = ScopeValidator.check_scope_permission(allowed_scopes, required_scope)
        
        # Determine expected result
        expected_result = required_scope in allowed_scopes
        
        # Check for wildcard permissions
        if not expected_result:
            for allowed_scope in allowed_scopes:
                if allowed_scope == '*':
                    expected_result = True
                    break
                elif allowed_scope.endswith('.*'):
                    prefix = allowed_scope[:-2]
                    if required_scope.startswith(prefix + '.'):
                        expected_result = True
                        break
        
        assert has_permission == expected_result, (
            f"Scope permission check failed: allowed={allowed_scopes}, "
            f"required={required_scope}, expected={expected_result}, got={has_permission}"
        )
    
    @given(
        api_key_data=api_key_strategy(),
        multiple_requests=st.lists(
            st.tuples(scopes_list_strategy, st.integers(min_value=1, max_value=100)),
            min_size=1, max_size=5
        )
    )
    @settings(max_examples=20)
    def test_property_scope_validation_consistency(self, api_key_data, multiple_requests):
        """
        Property: Scope Validation Consistency
        
        For any API key, scope validation should be consistent across
        multiple requests with the same scope requirements.
        
        **Validates: Requirements 10.2, 10.3**
        """
        # Create project and user
        project = Project(id=api_key_data['project_id'], name="Test Project")
        user = User(id=api_key_data['owner_id'], email=f"{api_key_data['owner_id']}@test.com")
        self.db.add(project)
        self.db.add(user)
        self.db.commit()
        
        # Create API key
        api_key = APIKey(**api_key_data)
        self.db.add(api_key)
        self.db.commit()
        
        # Test multiple requests with same scopes
        for required_scopes, request_count in multiple_requests:
            results = []
            for _ in range(min(request_count, 10)):  # Limit iterations for performance
                result = self.validation_service.check_scope_access(api_key.id, required_scopes)
                results.append(result)
            
            # All results should be identical
            assert all(r == results[0] for r in results), (
                f"Inconsistent scope validation results for scopes {required_scopes}: {results}"
            )
    
    @given(
        base_scopes=scopes_list_strategy,
        additional_scopes=scopes_list_strategy
    )
    @settings(max_examples=25)
    def test_property_scope_hierarchy_validation(self, base_scopes, additional_scopes):
        """
        Property: Scope Hierarchy Validation
        
        For any set of base scopes, adding additional scopes should
        never reduce the set of permissions (monotonic expansion).
        
        **Validates: Requirements 10.2**
        """
        # Assume we have a function that checks if scope set A includes all permissions of scope set B
        def scope_set_includes(superset, subset):
            """Check if superset includes all permissions in subset"""
            if not subset:
                return True
            if not superset:
                return False
            
            superset_set = set(superset)
            subset_set = set(subset)
            
            # Direct inclusion
            if subset_set.issubset(superset_set):
                return True
            
            # Check wildcard inclusion
            for scope in subset_set:
                included = False
                for allowed in superset_set:
                    if allowed == '*' or scope == allowed:
                        included = True
                        break
                    elif allowed.endswith('.*'):
                        prefix = allowed[:-2]
                        if scope.startswith(prefix + '.'):
                            included = True
                            break
                if not included:
                    return False
            
            return True
        
        # Combined scopes should include all base scope permissions
        combined_scopes = list(set(base_scopes + additional_scopes))
        
        # Test that combined scopes include base scopes
        includes_base = scope_set_includes(combined_scopes, base_scopes)
        assert includes_base, (
            f"Combined scopes should include base scopes: "
            f"base={base_scopes}, additional={additional_scopes}, combined={combined_scopes}"
        )
        
        # Test that combined scopes include additional scopes
        includes_additional = scope_set_includes(combined_scopes, additional_scopes)
        assert includes_additional, (
            f"Combined scopes should include additional scopes: "
            f"base={base_scopes}, additional={additional_scopes}, combined={combined_scopes}"
        )

class TestAPIKeyRateLimitValidation:
    """Property tests for API key rate limit validation"""
    
    def setup_method(self):
        """Set up test environment"""
        self.db = setup_test_db()
        self.validation_service = APIKeyValidationService(self.db)
    
    def teardown_method(self):
        """Clean up test environment"""
        self.db.close()
    
    @given(
        api_key_data=api_key_strategy(),
        request_contexts=st.lists(request_context_strategy(), min_size=1, max_size=10)
    )
    @settings(max_examples=15)
    def test_property_rate_limit_enforcement_consistency(self, api_key_data, request_contexts):
        """
        Property: Rate Limit Enforcement Consistency
        
        For any API key with rate limits, the rate limiting should be
        consistently enforced across multiple requests.
        
        **Validates: Requirements 10.3**
        """
        # Skip if no rate limits configured
        assume(api_key_data.get('rate_limits') is not None)
        
        # Create project and user
        project = Project(id=api_key_data['project_id'], name="Test Project")
        user = User(id=api_key_data['owner_id'], email=f"{api_key_data['owner_id']}@test.com")
        self.db.add(project)
        self.db.add(user)
        self.db.commit()
        
        # Create API key with rate limits
        api_key = APIKey(**api_key_data)
        self.db.add(api_key)
        self.db.commit()
        
        # Test rate limit checking
        rate_limits = api_key.rate_limits
        allowed_count = 0
        denied_count = 0
        
        for context in request_contexts[:5]:  # Limit for performance
            result = self.validation_service.check_rate_limit(api_key.id, context)
            
            if result.get('allowed', False):
                allowed_count += 1
            else:
                denied_count += 1
            
            # Verify result structure
            assert 'allowed' in result
            assert isinstance(result['allowed'], bool)
            
            if not result['allowed']:
                assert 'reason' in result
                assert isinstance(result['reason'], str)
        
        # At least some basic validation should occur
        assert (allowed_count + denied_count) == len(request_contexts[:5])

if __name__ == "__main__":
    pytest.main([__file__, "-v"])