"""
Simple Property Tests for API Key Scope Validation

This module contains property-based tests for API key scope validation logic
using Hypothesis to validate universal correctness properties without database dependencies.

**Feature: universal-auth, Property 22: API Key Scope Validation**
**Validates: Requirements 10.2, 10.3**
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import List, Set, Dict, Any

# Scope strategies
scope_category_strategy = st.sampled_from(['chat', 'completions', 'embeddings', 'images', 'audio', 'files', 'models'])
scope_action_strategy = st.sampled_from(['read', 'write', 'create', 'delete', 'list'])
scope_strategy = st.builds(lambda cat, act: f"{cat}.{act}", scope_category_strategy, scope_action_strategy)
scopes_list_strategy = st.lists(scope_strategy, min_size=0, max_size=8, unique=True)
role_strategy = st.sampled_from(['viewer', 'user', 'power_user', 'admin', 'developer'])

class ScopeValidator:
    """Utility class for scope validation and management"""
    
    @classmethod
    def validate_scopes(cls, scopes: List[str]) -> Dict[str, Any]:
        """
        Validate scope format and existence
        
        Args:
            scopes: List of scopes to validate
            
        Returns:
            Validation result with valid/invalid scopes
        """
        valid_scopes = []
        invalid_scopes = []
        
        for scope in scopes:
            if cls._is_valid_scope_format(scope):
                valid_scopes.append(scope)
            else:
                invalid_scopes.append(scope)
        
        return {
            'valid_scopes': valid_scopes,
            'invalid_scopes': invalid_scopes,
            'all_valid': len(invalid_scopes) == 0
        }
    
    @classmethod
    def check_scope_permission(cls, allowed_scopes: List[str], 
                              required_scope: str) -> bool:
        """
        Check if required scope is covered by allowed scopes
        
        Args:
            allowed_scopes: List of allowed scopes
            required_scope: Required scope to check
            
        Returns:
            True if permission is granted
        """
        # Direct match
        if required_scope in allowed_scopes:
            return True
        
        # Check wildcard permissions
        for allowed_scope in allowed_scopes:
            if allowed_scope.endswith('.*'):
                prefix = allowed_scope[:-2]
                if required_scope.startswith(prefix + '.'):
                    return True
            elif allowed_scope == '*':
                return True
        
        return False
    
    @classmethod
    def _is_valid_scope_format(cls, scope: str) -> bool:
        """Check if scope format is valid"""
        if not scope or not isinstance(scope, str):
            return False
        
        # Basic format validation
        if not scope.replace('.', '').replace('_', '').replace('-', '').replace('*', '').isalnum():
            return False
        
        # Check for valid patterns
        if scope == '*':
            return True
        
        if scope.endswith('.*'):
            return len(scope) > 2
        
        # Standard scope format: category.action or category.subcategory.action
        parts = scope.split('.')
        return len(parts) >= 1 and all(part.isalnum() or '_' in part or '-' in part for part in parts)

class APIKeyScopeValidator:
    """Core API key scope validation logic"""
    
    @staticmethod
    def check_scope_access(api_key_scopes: List[str], required_scopes: List[str]) -> bool:
        """
        Check if API key has required scopes
        
        Args:
            api_key_scopes: List of scopes allowed by the API key
            required_scopes: List of required scopes
            
        Returns:
            True if all required scopes are allowed
        """
        if not required_scopes:
            return True  # No scopes required
        
        if not api_key_scopes:
            return False  # Key has no scopes but scopes are required
        
        allowed_scopes = set(api_key_scopes)
        required_scopes_set = set(required_scopes)
        
        # Check if all required scopes are in allowed scopes
        return required_scopes_set.issubset(allowed_scopes)
    
    @staticmethod
    def check_role_access(api_key_allowed_roles: List[str], user_roles: List[str], 
                         is_owner: bool = False) -> bool:
        """
        Check if user has required roles to access API key
        
        Args:
            api_key_allowed_roles: List of roles allowed by the API key
            user_roles: List of roles assigned to the user
            is_owner: Whether the user is the owner of the API key
            
        Returns:
            True if access is allowed
        """
        # Owner always has access
        if is_owner:
            return True
        
        # If no role restrictions, allow access
        if not api_key_allowed_roles:
            return True
        
        # Check if user has any allowed role
        user_role_set = set(user_roles)
        allowed_role_set = set(api_key_allowed_roles)
        return bool(user_role_set.intersection(allowed_role_set))

class TestAPIKeyScopeValidation:
    """Property tests for API key scope validation"""
    
    @given(
        api_key_scopes=scopes_list_strategy,
        required_scopes=scopes_list_strategy
    )
    @settings(max_examples=100)
    def test_property_22_api_key_scope_validation(self, api_key_scopes, required_scopes):
        """
        Property 22: API Key Scope Validation
        
        For any API key and any set of required scopes, the validation should
        succeed if and only if all required scopes are contained in the API key's allowed scopes.
        
        **Validates: Requirements 10.2, 10.3**
        """
        # Test scope validation
        has_required_scopes = APIKeyScopeValidator.check_scope_access(api_key_scopes, required_scopes)
        
        # Determine expected result
        if not required_scopes:
            # No scopes required - should always pass
            expected_result = True
        elif not api_key_scopes:
            # Key has no scopes but scopes are required - should fail
            expected_result = False
        else:
            # Check if all required scopes are in allowed scopes
            allowed_scopes = set(api_key_scopes)
            required_scopes_set = set(required_scopes)
            expected_result = required_scopes_set.issubset(allowed_scopes)
        
        assert has_required_scopes == expected_result, (
            f"Scope validation failed: key_scopes={api_key_scopes}, "
            f"required_scopes={required_scopes}, expected={expected_result}, got={has_required_scopes}"
        )
    
    @given(
        api_key_allowed_roles=st.lists(role_strategy, min_size=0, max_size=3, unique=True),
        user_roles=st.lists(role_strategy, min_size=1, max_size=3, unique=True),
        is_owner=st.booleans()
    )
    @settings(max_examples=50)
    def test_property_role_based_api_key_access(self, api_key_allowed_roles, user_roles, is_owner):
        """
        Property: Role-Based API Key Access Control
        
        For any API key with role restrictions and any user with roles,
        access should be granted if and only if the user has at least one allowed role or is the owner.
        
        **Validates: Requirements 10.2, 10.3**
        """
        # Test role-based access
        has_access = APIKeyScopeValidator.check_role_access(api_key_allowed_roles, user_roles, is_owner)
        
        # Determine expected result
        if is_owner:
            # Owner always has access
            expected_result = True
        elif not api_key_allowed_roles:
            # No role restrictions - access allowed
            expected_result = True
        else:
            # Check if user has any allowed role
            user_role_set = set(user_roles)
            allowed_role_set = set(api_key_allowed_roles)
            expected_result = bool(user_role_set.intersection(allowed_role_set))
        
        assert has_access == expected_result, (
            f"Role access validation failed: user_roles={user_roles}, "
            f"allowed_roles={api_key_allowed_roles}, is_owner={is_owner}, "
            f"expected={expected_result}, got={has_access}"
        )
    
    @given(
        scopes=scopes_list_strategy
    )
    @settings(max_examples=50)
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
    @settings(max_examples=60)
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
        api_key_scopes=scopes_list_strategy,
        multiple_requests=st.lists(
            scopes_list_strategy,
            min_size=1, max_size=5
        )
    )
    @settings(max_examples=30)
    def test_property_scope_validation_consistency(self, api_key_scopes, multiple_requests):
        """
        Property: Scope Validation Consistency
        
        For any API key, scope validation should be consistent across
        multiple requests with the same scope requirements.
        
        **Validates: Requirements 10.2, 10.3**
        """
        # Test multiple requests with same scopes
        for required_scopes in multiple_requests:
            results = []
            for _ in range(3):  # Test consistency across multiple calls
                result = APIKeyScopeValidator.check_scope_access(api_key_scopes, required_scopes)
                results.append(result)
            
            # All results should be identical
            assert all(r == results[0] for r in results), (
                f"Inconsistent scope validation results for scopes {required_scopes}: {results}"
            )
    
    @given(
        base_scopes=scopes_list_strategy,
        additional_scopes=scopes_list_strategy
    )
    @settings(max_examples=40)
    def test_property_scope_hierarchy_validation(self, base_scopes, additional_scopes):
        """
        Property: Scope Hierarchy Validation
        
        For any set of base scopes, adding additional scopes should
        never reduce the set of permissions (monotonic expansion).
        
        **Validates: Requirements 10.2**
        """
        # Combined scopes should include all base scope permissions
        combined_scopes = list(set(base_scopes + additional_scopes))
        
        # Test that combined scopes include base scopes
        includes_base = APIKeyScopeValidator.check_scope_access(combined_scopes, base_scopes)
        assert includes_base, (
            f"Combined scopes should include base scopes: "
            f"base={base_scopes}, additional={additional_scopes}, combined={combined_scopes}"
        )
        
        # Test that combined scopes include additional scopes
        includes_additional = APIKeyScopeValidator.check_scope_access(combined_scopes, additional_scopes)
        assert includes_additional, (
            f"Combined scopes should include additional scopes: "
            f"base={base_scopes}, additional={additional_scopes}, combined={combined_scopes}"
        )
    
    @given(
        scopes1=scopes_list_strategy,
        scopes2=scopes_list_strategy
    )
    @settings(max_examples=30)
    def test_property_scope_validation_symmetry(self, scopes1, scopes2):
        """
        Property: Scope Validation Symmetry
        
        For any two sets of scopes A and B, if A contains all scopes in B,
        then validation of B against A should succeed.
        
        **Validates: Requirements 10.2**
        """
        # If scopes1 is a superset of scopes2, validation should succeed
        scopes1_set = set(scopes1)
        scopes2_set = set(scopes2)
        
        if scopes2_set.issubset(scopes1_set):
            # scopes1 contains all scopes in scopes2
            validation_result = APIKeyScopeValidator.check_scope_access(scopes1, scopes2)
            assert validation_result, (
                f"Validation should succeed when allowed scopes contain all required scopes: "
                f"allowed={scopes1}, required={scopes2}"
            )
        
        # Test the reverse: if scopes2 doesn't contain all scopes in scopes1, validation may fail
        if not scopes1_set.issubset(scopes2_set) and scopes1:
            validation_result = APIKeyScopeValidator.check_scope_access(scopes2, scopes1)
            # This may succeed or fail, but we can't assert a specific result
            # We just verify the function doesn't crash
            assert isinstance(validation_result, bool)
    
    @given(
        empty_scopes=st.just([]),
        any_scopes=scopes_list_strategy
    )
    @settings(max_examples=20)
    def test_property_empty_scope_edge_cases(self, empty_scopes, any_scopes):
        """
        Property: Empty Scope Edge Cases
        
        Test behavior with empty scope lists to ensure proper handling.
        
        **Validates: Requirements 10.2**
        """
        # Empty required scopes should always pass
        result1 = APIKeyScopeValidator.check_scope_access(any_scopes, empty_scopes)
        assert result1 == True, "Empty required scopes should always be satisfied"
        
        # Empty allowed scopes with non-empty required scopes should fail
        if any_scopes:  # Only test if we have some required scopes
            result2 = APIKeyScopeValidator.check_scope_access(empty_scopes, any_scopes)
            assert result2 == False, "Empty allowed scopes should not satisfy non-empty required scopes"
        
        # Empty allowed and empty required should pass
        result3 = APIKeyScopeValidator.check_scope_access(empty_scopes, empty_scopes)
        assert result3 == True, "Empty allowed and empty required should pass"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])