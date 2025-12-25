"""
Property-Based Tests for OPA Policy Evaluation

This module contains property-based tests that validate universal correctness
properties for the Open Policy Agent (OPA) integration using Hypothesis.

Feature: universal-auth, Property 19: OPA Policy Evaluation Consistency
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime
from typing import Dict, Any, List

from services.opa_service import OPAService, PolicyInput, PolicyDecision


class TestOPAPolicyEvaluationProperties:
    """Property-based tests for OPA Policy Evaluation consistency"""
    
    # Strategy for generating user data
    user_data_strategy = st.fixed_dictionaries({
        'id': st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        'email': st.emails(),
        'capabilities': st.lists(
            st.one_of(
                st.just('*'),
                st.sampled_from([
                    'app:login', 'user:update_profile', 'auth:oauth', 
                    'tenant:create', 'rbac:assign_role', 'ui:admin_panel'
                ])
            ),
            min_size=0,
            max_size=5,
            unique=True
        )
    })
    
    # Strategy for generating policy packages
    policy_packages = st.sampled_from(['authz', 'tenant', 'api'])
    
    # Strategy for generating capabilities
    capabilities = st.sampled_from([
        'app:login', 'user:update_profile', 'auth:oauth',
        'tenant:create', 'rbac:assign_role', 'ui:admin_panel'
    ])
    
    @given(
        user_data=user_data_strategy,
        package=policy_packages,
        required_capability=capabilities
    )
    @settings(max_examples=5, deadline=3000)
    def test_opa_policy_evaluation_consistency_property(self, user_data, package, required_capability):
        """
        Property 19: OPA Policy Evaluation Consistency
        
        For any authorization request, the OPA sidecar should evaluate policies 
        using the current policy bundle version and return consistent decisions 
        for identical input conditions.
        
        **Feature: universal-auth, Property 19: OPA Policy Evaluation Consistency**
        **Validates: Requirements 4.2, 4.3**
        """
        async def run_test():
            # Determine expected result
            expected_result = self._determine_expected_result(user_data, required_capability)
            
            mock_response_data = {
                'result': expected_result,
                'reason': 'Policy evaluation completed',
                'policy_version': 'v1.0.0'
            }
            
            # Create a proper async context manager mock
            async_context_mock = AsyncMock()
            async_context_mock.status = 200
            async_context_mock.json = AsyncMock(return_value=mock_response_data)
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session.post.return_value = async_context_mock
                mock_session_class.return_value = mock_session
                
                opa_service = OPAService()
                
                # Create policy input
                policy_input = PolicyInput(
                    user=user_data,
                    required_capability=required_capability
                )
                
                # Evaluate policy multiple times with identical input
                results = []
                for _ in range(3):
                    result = await opa_service.evaluate_policy(package, policy_input)
                    results.append(result)
                
                # Verify consistency across multiple evaluations
                first_result = results[0]
                for i, result in enumerate(results[1:], 1):
                    assert result.allow == first_result.allow, \
                        f"Inconsistent policy decision on evaluation {i+1}: " \
                        f"expected {first_result.allow}, got {result.allow}"
                
                # Verify the decision matches expected logic
                assert first_result.allow == expected_result, \
                    f"Policy decision doesn't match expected logic: " \
                    f"expected {expected_result}, got {first_result.allow} " \
                    f"for capability {required_capability} with user capabilities {user_data.get('capabilities', [])}"
        
        asyncio.run(run_test())
    
    @given(
        user_data=user_data_strategy,
        capability=capabilities
    )
    @settings(max_examples=5, deadline=3000)
    def test_authorization_consistency_property(self, user_data, capability):
        """
        Property: Authorization decisions should be consistent
        
        For any authorization request with identical parameters, 
        the system should return the same authorization decision.
        
        **Feature: universal-auth, Property 19: OPA Policy Evaluation Consistency**
        **Validates: Requirements 4.2, 4.3**
        """
        async def run_test():
            expected_result = self._determine_expected_result(user_data, capability)
            
            mock_response_data = {
                'result': expected_result,
                'reason': f'Authorization evaluation for {capability}',
                'policy_version': 'v1.0.0'
            }
            
            async_context_mock = AsyncMock()
            async_context_mock.status = 200
            async_context_mock.json = AsyncMock(return_value=mock_response_data)
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session.post.return_value = async_context_mock
                mock_session_class.return_value = mock_session
                
                opa_service = OPAService()
                
                # Test authorization multiple times
                results = []
                for _ in range(3):
                    result = await opa_service.check_authorization(PolicyInput(
                        user=user_data,
                        required_capability=capability
                    ))
                    results.append(result)
                
                # Verify consistency
                first_result = results[0]
                for i, result in enumerate(results[1:], 1):
                    assert result.allow == first_result.allow, \
                        f"Inconsistent authorization decision on evaluation {i+1}"
                
                # Verify expected result
                assert first_result.allow == expected_result, \
                    f"Authorization result mismatch for capability {capability}: " \
                    f"expected {expected_result}, got {first_result.allow}"
        
        asyncio.run(run_test())
    
    @given(
        user_data=user_data_strategy,
        package=policy_packages
    )
    @settings(max_examples=3, deadline=3000)
    def test_policy_error_handling_consistency_property(self, user_data, package):
        """
        Property: Policy evaluation error handling should be consistent
        
        For any policy evaluation that encounters an error, the system 
        should consistently return a deny decision with appropriate error information.
        
        **Feature: universal-auth, Property 19: OPA Policy Evaluation Consistency**
        **Validates: Requirements 4.2, 4.3**
        """
        async def run_test():
            async_context_mock = AsyncMock()
            async_context_mock.status = 500  # Server error
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session.post.return_value = async_context_mock
                mock_session_class.return_value = mock_session
                
                opa_service = OPAService()
                
                policy_input = PolicyInput(
                    user=user_data,
                    required_capability="test:capability"
                )
                
                # Test error handling multiple times
                results = []
                for _ in range(3):
                    result = await opa_service.evaluate_policy(package, policy_input)
                    results.append(result)
                
                # Verify consistent error handling
                for result in results:
                    assert result.allow is False, \
                        f"Error scenario should always deny access, got {result.allow}"
                    assert result.reason is not None, \
                        "Error scenario should provide reason"
                    assert "500" in result.reason, \
                        f"Error reason should mention status code 500, got: {result.reason}"
                
                # Verify consistency across multiple error evaluations
                first_result = results[0]
                for i, result in enumerate(results[1:], 1):
                    assert result.allow == first_result.allow, \
                        f"Inconsistent error handling on evaluation {i+1}"
        
        asyncio.run(run_test())
    
    @given(user_data=user_data_strategy)
    @settings(max_examples=3, deadline=3000)
    def test_opa_service_timeout_consistency_property(self, user_data):
        """
        Property: OPA service timeout handling should be consistent
        
        For any timeout scenario, the system should consistently 
        return a deny decision with timeout information.
        
        **Feature: universal-auth, Property 19: OPA Policy Evaluation Consistency**
        **Validates: Requirements 4.2, 4.3**
        """
        async def run_test():
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                
                # Mock timeout exception
                mock_session.post.side_effect = asyncio.TimeoutError()
                mock_session_class.return_value = mock_session
                
                opa_service = OPAService(timeout=1)  # Short timeout
                
                policy_input = PolicyInput(
                    user=user_data,
                    required_capability='test:capability'
                )
                
                # Test timeout handling multiple times
                results = []
                for _ in range(3):
                    result = await opa_service.evaluate_policy('authz', policy_input)
                    results.append(result)
                
                # Verify consistent timeout handling
                for result in results:
                    assert result.allow is False, "Timeout should result in deny"
                    assert 'timeout' in result.reason.lower(), \
                        f"Timeout reason should mention timeout, got: {result.reason}"
                
                # Verify consistency across timeout scenarios
                first_result = results[0]
                for i, result in enumerate(results[1:], 1):
                    assert result.allow == first_result.allow, \
                        f"Inconsistent timeout handling on evaluation {i+1}"
                    assert result.reason == first_result.reason, \
                        f"Inconsistent timeout reason on evaluation {i+1}"
        
        asyncio.run(run_test())
    
    @given(user_data=user_data_strategy)
    @settings(max_examples=3, deadline=3000)
    def test_opa_health_check_consistency_property(self, user_data):
        """
        Property: OPA health check should be consistent
        
        For any health check request, the system should return 
        consistent health status based on OPA service availability.
        
        **Feature: universal-auth, Property 19: OPA Policy Evaluation Consistency**
        **Validates: Requirements 4.2, 4.3**
        """
        async def run_test():
            # Test healthy scenario
            async_context_mock_healthy = AsyncMock()
            async_context_mock_healthy.status = 200
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session.get.return_value = async_context_mock_healthy
                mock_session_class.return_value = mock_session
                
                opa_service = OPAService()
                
                # Test health check multiple times
                health_results = []
                for _ in range(3):
                    health = await opa_service.health_check()
                    health_results.append(health)
                
                # Verify consistent health status
                for health in health_results:
                    assert health is True, "Healthy OPA should return True"
                
                # Verify all results are identical
                assert all(h == health_results[0] for h in health_results), \
                    "Health check results should be consistent"
        
        asyncio.run(run_test())
    
    @given(
        user_data=user_data_strategy,
        action=st.one_of(st.none(), st.text(min_size=1, max_size=10)),
        resource=st.one_of(st.none(), st.text(min_size=1, max_size=10))
    )
    @settings(max_examples=5, deadline=3000)
    def test_policy_input_serialization_consistency_property(self, user_data, action, resource):
        """
        Property: Policy input serialization should be consistent
        
        For any policy input data, serialization to dictionary should 
        be consistent and preserve all non-None values.
        
        **Feature: universal-auth, Property 19: OPA Policy Evaluation Consistency**
        **Validates: Requirements 4.2, 4.3**
        """
        policy_input = PolicyInput(
            user=user_data,
            action=action,
            resource=resource
        )
        
        # Serialize multiple times
        serializations = []
        for _ in range(3):
            serialized = policy_input.to_dict()
            serializations.append(serialized)
        
        # Verify consistency across serializations
        first_serialization = serializations[0]
        for i, serialization in enumerate(serializations[1:], 1):
            assert serialization == first_serialization, \
                f"Inconsistent serialization on attempt {i+1}"
        
        # Verify all non-None values are preserved
        assert 'user' in first_serialization, "User data should always be present"
        assert first_serialization['user'] == user_data, "User data should be preserved"
        
        if action is not None:
            assert 'action' in first_serialization, "Non-None action should be preserved"
            assert first_serialization['action'] == action, "Action value should match"
        else:
            assert 'action' not in first_serialization, "None action should be excluded"
        
        if resource is not None:
            assert 'resource' in first_serialization, "Non-None resource should be preserved"
            assert first_serialization['resource'] == resource, "Resource value should match"
        else:
            assert 'resource' not in first_serialization, "None resource should be excluded"
    
    def _determine_expected_result(self, user_data: Dict[str, Any], required_capability: str) -> bool:
        """Determine expected policy result based on user capabilities"""
        user_capabilities = user_data.get('capabilities', [])
        
        # Admin wildcard access
        if '*' in user_capabilities:
            return True
        
        # Direct capability match
        if required_capability in user_capabilities:
            return True
        
        # Wildcard pattern matching
        for capability in user_capabilities:
            if capability.endswith('*'):
                prefix = capability[:-1]
                if required_capability.startswith(prefix):
                    return True
        
        return False


class TestOPAServiceIntegration:
    """Integration tests for OPA service functionality"""
    
    def test_policy_decision_structure_consistency(self):
        """
        Property: PolicyDecision objects should have consistent structure
        
        All PolicyDecision objects should have the required fields
        and proper types regardless of how they are created.
        
        **Feature: universal-auth, Property 19: OPA Policy Evaluation Consistency**
        **Validates: Requirements 4.2, 4.3**
        """
        # Test PolicyDecision creation from OPA response
        opa_response = {
            'result': True,
            'reason': 'Access granted',
            'policy_version': 'v1.0.0'
        }
        
        decision = PolicyDecision.from_opa_response(opa_response)
        
        # Verify structure
        assert isinstance(decision.allow, bool), "Allow field should be boolean"
        assert isinstance(decision.reason, str), "Reason field should be string"
        assert isinstance(decision.policy_version, str), "Policy version should be string"
        assert isinstance(decision.evaluated_at, datetime), "Evaluated at should be datetime"
        
        # Test direct creation
        direct_decision = PolicyDecision(
            allow=False,
            reason="Access denied",
            policy_version="v1.0.0"
        )
        
        assert isinstance(direct_decision.allow, bool), "Direct creation allow should be boolean"
        assert direct_decision.reason == "Access denied", "Direct creation reason should match"
        assert direct_decision.policy_version == "v1.0.0", "Direct creation version should match"
    
    def test_policy_input_validation_consistency(self):
        """
        Property: PolicyInput validation should be consistent
        
        PolicyInput objects should consistently validate and serialize
        their data regardless of input variations.
        
        **Feature: universal-auth, Property 19: OPA Policy Evaluation Consistency**
        **Validates: Requirements 4.2, 4.3**
        """
        user_data = {
            'id': 'test_user',
            'capabilities': ['app:login', 'user:profile']
        }
        
        # Test with minimal data
        minimal_input = PolicyInput(user=user_data)
        minimal_dict = minimal_input.to_dict()
        
        assert 'user' in minimal_dict, "User should always be present"
        assert len(minimal_dict) == 1, "Only user should be present for minimal input"
        
        # Test with full data
        full_input = PolicyInput(
            user=user_data,
            action="read",
            resource="profile",
            tenant_id="tenant_123",
            required_capability="user:profile"
        )
        full_dict = full_input.to_dict()
        
        expected_keys = {'user', 'action', 'resource', 'tenant_id', 'required_capability'}
        assert set(full_dict.keys()) == expected_keys, \
            f"Full input should have all keys: {expected_keys}"
        
        # Verify data integrity
        assert full_dict['user'] == user_data, "User data should be preserved"
        assert full_dict['action'] == "read", "Action should be preserved"
        assert full_dict['resource'] == "profile", "Resource should be preserved"
        assert full_dict['tenant_id'] == "tenant_123", "Tenant ID should be preserved"
        assert full_dict['required_capability'] == "user:profile", "Required capability should be preserved"