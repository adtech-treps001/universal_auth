"""
Property Tests for JWT Token Management

This module contains property-based tests for JWT token validation and management
using Hypothesis to validate universal correctness properties.

**Feature: universal-auth, Property 16: JWT Token Validation**
**Validates: Requirements 8.1, 8.2, 8.4**
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Dict, Any, List, Optional
from jose import jwt
import time
from datetime import datetime, timedelta
import json

# JWT strategies
user_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
email_strategy = st.emails()
role_strategy = st.sampled_from(['user', 'admin', 'moderator', 'viewer', 'developer'])
scope_strategy = st.sampled_from(['read', 'write', 'admin', 'api', 'profile'])
algorithm_strategy = st.sampled_from(['HS256', 'HS512', 'RS256'])
secret_key_strategy = st.text(min_size=32, max_size=128)

# Token payload strategies
token_payload_strategy = st.fixed_dictionaries({
    'user_id': user_id_strategy,
    'email': email_strategy,
    'roles': st.lists(role_strategy, min_size=1, max_size=3, unique=True),
    'scopes': st.lists(scope_strategy, min_size=1, max_size=5, unique=True),
    'tenant_id': st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    'exp': st.integers(min_value=int(time.time()), max_value=int(time.time()) + 86400),  # Valid for up to 24 hours
    'iat': st.integers(min_value=int(time.time()) - 3600, max_value=int(time.time())),  # Issued up to 1 hour ago
    'iss': st.just('universal-auth'),
    'aud': st.sampled_from(['web', 'mobile', 'api'])
})

class JWTTokenManager:
    """Core JWT token management logic"""
    
    DEFAULT_ALGORITHM = 'HS256'
    DEFAULT_EXPIRY_HOURS = 24
    REQUIRED_CLAIMS = ['user_id', 'exp', 'iat', 'iss']
    
    def __init__(self, secret_key: str, algorithm: str = DEFAULT_ALGORITHM):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def generate_token(self, payload: Dict[str, Any]) -> str:
        """
        Generate JWT token from payload
        
        Args:
            payload: Token payload dictionary
            
        Returns:
            Encoded JWT token string
        """
        # Add default claims if not present
        token_payload = payload.copy()
        
        current_time = int(time.time())
        if 'iat' not in token_payload:
            token_payload['iat'] = current_time
        
        if 'exp' not in token_payload:
            token_payload['exp'] = current_time + (self.DEFAULT_EXPIRY_HOURS * 3600)
        
        if 'iss' not in token_payload:
            token_payload['iss'] = 'universal-auth'
        
        # Generate token
        return jwt.encode(token_payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and return payload
        
        Args:
            token: JWT token string
            
        Returns:
            Validation result with payload or error
        """
        try:
            # Decode and validate token
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={'verify_exp': True, 'verify_iat': True}
            )
            
            # Validate required claims
            missing_claims = []
            for claim in self.REQUIRED_CLAIMS:
                if claim not in payload:
                    missing_claims.append(claim)
            
            if missing_claims:
                return {
                    'valid': False,
                    'error': f'Missing required claims: {missing_claims}',
                    'payload': None
                }
            
            # Additional validation
            current_time = int(time.time())
            
            # Check expiration
            if payload['exp'] <= current_time:
                return {
                    'valid': False,
                    'error': 'Token has expired',
                    'payload': payload
                }
            
            # Check issued at time (not in future)
            if payload['iat'] > current_time + 300:  # Allow 5 minutes clock skew
                return {
                    'valid': False,
                    'error': 'Token issued in the future',
                    'payload': payload
                }
            
            return {
                'valid': True,
                'error': None,
                'payload': payload
            }
            
        except jwt.ExpiredSignatureError:
            return {
                'valid': False,
                'error': 'Token has expired',
                'payload': None
            }
        except jwt.InvalidTokenError as e:
            return {
                'valid': False,
                'error': f'Invalid token: {str(e)}',
                'payload': None
            }
        except Exception as e:
            return {
                'valid': False,
                'error': f'Token validation error: {str(e)}',
                'payload': None
            }
    
    def refresh_token(self, token: str) -> Dict[str, Any]:
        """
        Refresh JWT token with new expiration
        
        Args:
            token: Current JWT token
            
        Returns:
            New token or error
        """
        validation_result = self.validate_token(token)
        
        if not validation_result['valid']:
            return {
                'success': False,
                'error': validation_result['error'],
                'new_token': None
            }
        
        # Generate new token with same payload but new expiration
        payload = validation_result['payload'].copy()
        current_time = int(time.time())
        payload['iat'] = current_time
        payload['exp'] = current_time + (self.DEFAULT_EXPIRY_HOURS * 3600)
        
        try:
            new_token = self.generate_token(payload)
            return {
                'success': True,
                'error': None,
                'new_token': new_token
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Token refresh error: {str(e)}',
                'new_token': None
            }
    
    def extract_user_info(self, token: str) -> Dict[str, Any]:
        """
        Extract user information from token
        
        Args:
            token: JWT token string
            
        Returns:
            User information or error
        """
        validation_result = self.validate_token(token)
        
        if not validation_result['valid']:
            return {
                'success': False,
                'error': validation_result['error'],
                'user_info': None
            }
        
        payload = validation_result['payload']
        
        # Extract user information
        user_info = {
            'user_id': payload.get('user_id'),
            'email': payload.get('email'),
            'roles': payload.get('roles', []),
            'scopes': payload.get('scopes', []),
            'tenant_id': payload.get('tenant_id'),
            'audience': payload.get('aud'),
            'issued_at': payload.get('iat'),
            'expires_at': payload.get('exp')
        }
        
        return {
            'success': True,
            'error': None,
            'user_info': user_info
        }
    
    def check_token_permissions(self, token: str, required_scopes: List[str]) -> bool:
        """
        Check if token has required permissions
        
        Args:
            token: JWT token string
            required_scopes: List of required scopes
            
        Returns:
            True if token has all required scopes
        """
        user_info_result = self.extract_user_info(token)
        
        if not user_info_result['success']:
            return False
        
        user_scopes = user_info_result['user_info'].get('scopes', [])
        required_scopes_set = set(required_scopes)
        user_scopes_set = set(user_scopes)
        
        return required_scopes_set.issubset(user_scopes_set)

class TestJWTTokenValidation:
    """Property tests for JWT token validation"""
    
    @given(
        secret_key=secret_key_strategy,
        algorithm=algorithm_strategy,
        payload=token_payload_strategy
    )
    @settings(max_examples=100)
    def test_property_16_jwt_token_validation(self, secret_key, algorithm, payload):
        """
        Property 16: JWT Token Validation
        
        For any valid secret key, algorithm, and payload, the JWT system should
        generate a token that can be successfully validated and decoded.
        
        **Validates: Requirements 8.1, 8.2, 8.4**
        """
        # Create JWT manager
        jwt_manager = JWTTokenManager(secret_key, algorithm)
        
        # Generate token
        token = jwt_manager.generate_token(payload)
        assert isinstance(token, str), "Generated token should be a string"
        assert len(token) > 0, "Generated token should not be empty"
        
        # Validate token
        validation_result = jwt_manager.validate_token(token)
        
        # Token should be valid
        assert validation_result['valid'] == True, f"Token should be valid: {validation_result['error']}"
        assert validation_result['error'] is None, "Valid token should have no error"
        assert validation_result['payload'] is not None, "Valid token should have payload"
        
        # Verify payload integrity
        decoded_payload = validation_result['payload']
        for key, value in payload.items():
            assert key in decoded_payload, f"Payload key {key} should be preserved"
            assert decoded_payload[key] == value, f"Payload value for {key} should be preserved"
    
    @given(
        secret_key=secret_key_strategy,
        payload=token_payload_strategy,
        wrong_secret=secret_key_strategy
    )
    @settings(max_examples=50)
    def test_property_jwt_token_security(self, secret_key, payload, wrong_secret):
        """
        Property: JWT Token Security
        
        For any token generated with one secret key, validation with a different
        secret key should fail, ensuring token security.
        
        **Validates: Requirements 8.1, 8.2**
        """
        # Ensure different secret keys
        if secret_key == wrong_secret:
            wrong_secret = secret_key + "_different"
        
        # Create JWT managers with different keys
        jwt_manager_correct = JWTTokenManager(secret_key)
        jwt_manager_wrong = JWTTokenManager(wrong_secret)
        
        # Generate token with correct key
        token = jwt_manager_correct.generate_token(payload)
        
        # Validate with correct key (should succeed)
        correct_validation = jwt_manager_correct.validate_token(token)
        assert correct_validation['valid'] == True, "Token should be valid with correct key"
        
        # Validate with wrong key (should fail)
        wrong_validation = jwt_manager_wrong.validate_token(token)
        assert wrong_validation['valid'] == False, "Token should be invalid with wrong key"
        assert wrong_validation['error'] is not None, "Invalid token should have error message"
    
    @given(
        secret_key=secret_key_strategy,
        payload=token_payload_strategy
    )
    @settings(max_examples=60)
    def test_property_jwt_token_expiration(self, secret_key, payload):
        """
        Property: JWT Token Expiration
        
        For any token with an expiration time in the past, validation should
        fail with an expiration error.
        
        **Validates: Requirements 8.1, 8.4**
        """
        jwt_manager = JWTTokenManager(secret_key)
        
        # Create expired token
        expired_payload = payload.copy()
        expired_payload['exp'] = int(time.time()) - 3600  # Expired 1 hour ago
        expired_payload['iat'] = int(time.time()) - 7200  # Issued 2 hours ago
        
        expired_token = jwt_manager.generate_token(expired_payload)
        
        # Validate expired token
        validation_result = jwt_manager.validate_token(expired_token)
        
        # Should be invalid due to expiration
        assert validation_result['valid'] == False, "Expired token should be invalid"
        assert 'expired' in validation_result['error'].lower(), "Error should mention expiration"
    
    @given(
        secret_key=secret_key_strategy,
        payload=token_payload_strategy
    )
    @settings(max_examples=40)
    def test_property_jwt_token_refresh(self, payload, secret_key):
        """
        Property: JWT Token Refresh
        
        For any valid token, the refresh operation should generate a new token
        with the same payload but updated timestamps.
        
        **Validates: Requirements 8.1, 8.4**
        """
        jwt_manager = JWTTokenManager(secret_key)
        
        # Generate original token
        original_token = jwt_manager.generate_token(payload)
        
        # Refresh token
        refresh_result = jwt_manager.refresh_token(original_token)
        
        # Refresh should succeed
        assert refresh_result['success'] == True, f"Token refresh should succeed: {refresh_result['error']}"
        assert refresh_result['new_token'] is not None, "Refresh should provide new token"
        
        # New token should be different from original
        new_token = refresh_result['new_token']
        assert new_token != original_token, "Refreshed token should be different from original"
        
        # New token should be valid
        new_validation = jwt_manager.validate_token(new_token)
        assert new_validation['valid'] == True, "Refreshed token should be valid"
        
        # Payload should be preserved (except timestamps)
        new_payload = new_validation['payload']
        for key, value in payload.items():
            if key not in ['iat', 'exp']:  # Timestamps will be different
                assert new_payload[key] == value, f"Payload key {key} should be preserved in refresh"
    
    @given(
        secret_key=secret_key_strategy,
        payload=token_payload_strategy,
        required_scopes=st.lists(scope_strategy, min_size=1, max_size=3, unique=True)
    )
    @settings(max_examples=50)
    def test_property_jwt_permission_checking(self, secret_key, payload, required_scopes):
        """
        Property: JWT Permission Checking
        
        For any token and required scopes, permission checking should correctly
        determine if the token has all required scopes.
        
        **Validates: Requirements 8.2, 8.4**
        """
        jwt_manager = JWTTokenManager(secret_key)
        
        # Generate token
        token = jwt_manager.generate_token(payload)
        
        # Check permissions
        has_permissions = jwt_manager.check_token_permissions(token, required_scopes)
        
        # Determine expected result
        token_scopes = set(payload.get('scopes', []))
        required_scopes_set = set(required_scopes)
        expected_result = required_scopes_set.issubset(token_scopes)
        
        assert has_permissions == expected_result, (
            f"Permission check failed: token_scopes={token_scopes}, "
            f"required_scopes={required_scopes_set}, expected={expected_result}, got={has_permissions}"
        )
    
    @given(
        secret_key=secret_key_strategy,
        payload=token_payload_strategy
    )
    @settings(max_examples=40)
    def test_property_jwt_user_info_extraction(self, secret_key, payload):
        """
        Property: JWT User Info Extraction
        
        For any valid token, user information extraction should correctly
        return all user-related claims from the token.
        
        **Validates: Requirements 8.1, 8.2**
        """
        jwt_manager = JWTTokenManager(secret_key)
        
        # Generate token
        token = jwt_manager.generate_token(payload)
        
        # Extract user info
        user_info_result = jwt_manager.extract_user_info(token)
        
        # Extraction should succeed
        assert user_info_result['success'] == True, f"User info extraction should succeed: {user_info_result['error']}"
        assert user_info_result['user_info'] is not None, "Should return user info"
        
        # Verify user info content
        user_info = user_info_result['user_info']
        
        # Check that all expected fields are present
        expected_fields = ['user_id', 'email', 'roles', 'scopes', 'tenant_id', 'audience', 'issued_at', 'expires_at']
        for field in expected_fields:
            assert field in user_info, f"User info should contain {field}"
        
        # Verify field values match payload
        if 'user_id' in payload:
            assert user_info['user_id'] == payload['user_id'], "User ID should match payload"
        if 'email' in payload:
            assert user_info['email'] == payload['email'], "Email should match payload"
        if 'roles' in payload:
            assert user_info['roles'] == payload['roles'], "Roles should match payload"
        if 'scopes' in payload:
            assert user_info['scopes'] == payload['scopes'], "Scopes should match payload"
    
    @given(
        secret_key=secret_key_strategy,
        payloads=st.lists(token_payload_strategy, min_size=2, max_size=5)
    )
    @settings(max_examples=30)
    def test_property_jwt_token_isolation(self, secret_key, payloads):
        """
        Property: JWT Token Isolation
        
        For any set of different payloads, each generated token should be
        unique and validation should return the correct payload for each token.
        
        **Validates: Requirements 8.1, 8.2**
        """
        jwt_manager = JWTTokenManager(secret_key)
        
        # Generate tokens for all payloads
        tokens = []
        for payload in payloads:
            token = jwt_manager.generate_token(payload)
            tokens.append(token)
        
        # All tokens should be unique
        assert len(set(tokens)) == len(tokens), "All generated tokens should be unique"
        
        # Each token should validate to its original payload
        for i, (token, original_payload) in enumerate(zip(tokens, payloads)):
            validation_result = jwt_manager.validate_token(token)
            
            assert validation_result['valid'] == True, f"Token {i} should be valid"
            
            decoded_payload = validation_result['payload']
            for key, value in original_payload.items():
                assert decoded_payload[key] == value, f"Token {i} payload key {key} should match original"
    
    @given(
        secret_key=secret_key_strategy,
        payload=token_payload_strategy,
        multiple_validations=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=25)
    def test_property_jwt_validation_consistency(self, secret_key, payload, multiple_validations):
        """
        Property: JWT Validation Consistency
        
        For any token, validation should be consistent across multiple calls
        with the same input parameters.
        
        **Validates: Requirements 8.1, 8.2**
        """
        jwt_manager = JWTTokenManager(secret_key)
        
        # Generate token
        token = jwt_manager.generate_token(payload)
        
        # Validate multiple times
        results = []
        for _ in range(multiple_validations):
            result = jwt_manager.validate_token(token)
            results.append(result)
        
        # All results should be identical
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            assert result['valid'] == first_result['valid'], f"Validation consistency failed at call {i}"
            assert result['error'] == first_result['error'], f"Error consistency failed at call {i}"
            
            if result['payload'] and first_result['payload']:
                assert result['payload'] == first_result['payload'], f"Payload consistency failed at call {i}"
    
    @given(
        secret_key=secret_key_strategy,
        base_payload=token_payload_strategy
    )
    @settings(max_examples=20)
    def test_property_jwt_required_claims_validation(self, secret_key, base_payload):
        """
        Property: JWT Required Claims Validation
        
        For any token missing required claims, validation should fail
        with appropriate error messages.
        
        **Validates: Requirements 8.1, 8.2**
        """
        jwt_manager = JWTTokenManager(secret_key)
        
        # Test each required claim
        for required_claim in jwt_manager.REQUIRED_CLAIMS:
            # Create payload without the required claim
            incomplete_payload = base_payload.copy()
            if required_claim in incomplete_payload:
                del incomplete_payload[required_claim]
            
            # Generate token with incomplete payload
            token = jwt_manager.generate_token(incomplete_payload)
            
            # Validation should fail if the claim is truly missing from the final payload
            validation_result = jwt_manager.validate_token(token)
            
            # Note: Some claims like 'iat', 'exp', 'iss' are added automatically in generate_token
            # So we only expect failure for claims that aren't auto-added
            if required_claim == 'user_id':  # This is not auto-added
                assert validation_result['valid'] == False, f"Token without {required_claim} should be invalid"
                assert 'Missing required claims' in validation_result['error'], f"Error should mention missing {required_claim}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])