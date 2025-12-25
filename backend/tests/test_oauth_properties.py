"""
Property-Based Tests for OAuth Service

This module contains property-based tests that validate universal correctness
properties for the OAuth authentication system using Hypothesis.

Feature: universal-auth, Property 1: OAuth Provider Redirect Consistency
"""

import pytest
import os
import re
import tempfile
import yaml
from urllib.parse import urlparse, parse_qs
from unittest.mock import patch
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from auth.oauth_service import OAuthService, ProviderType


def create_test_oauth_service():
    """Create OAuth service with test providers for property testing"""
    config_data = {
        'providers': {
            'google': {
                'type': 'google',
                'client_id_env': 'TEST_GOOGLE_CLIENT_ID',
                'client_secret_env': 'TEST_GOOGLE_CLIENT_SECRET',
                'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'token_url': 'https://oauth2.googleapis.com/token',
                'userinfo_url': 'https://openidconnect.googleapis.com/v1/userinfo',
                'scopes': ['openid', 'email', 'profile'],
                'redirect_uri': 'http://localhost:8000/auth/callback/google'
            },
            'github': {
                'type': 'github',
                'client_id_env': 'TEST_GITHUB_CLIENT_ID',
                'client_secret_env': 'TEST_GITHUB_CLIENT_SECRET',
                'auth_url': 'https://github.com/login/oauth/authorize',
                'token_url': 'https://github.com/login/oauth/access_token',
                'userinfo_url': 'https://api.github.com/user',
                'scopes': ['user:email'],
                'redirect_uri': 'http://localhost:8000/auth/callback/github'
            },
            'linkedin': {
                'type': 'linkedin',
                'client_id_env': 'TEST_LINKEDIN_CLIENT_ID',
                'client_secret_env': 'TEST_LINKEDIN_CLIENT_SECRET',
                'auth_url': 'https://www.linkedin.com/oauth/v2/authorization',
                'token_url': 'https://www.linkedin.com/oauth/v2/accessToken',
                'userinfo_url': 'https://api.linkedin.com/v2/people/~',
                'scopes': ['r_liteprofile', 'r_emailaddress'],
                'redirect_uri': 'http://localhost:8000/auth/callback/linkedin'
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    with patch.dict(os.environ, {
        'TEST_GOOGLE_CLIENT_ID': 'test_google_client_123',
        'TEST_GOOGLE_CLIENT_SECRET': 'test_google_secret_456',
        'TEST_GITHUB_CLIENT_ID': 'test_github_client_789',
        'TEST_GITHUB_CLIENT_SECRET': 'test_github_secret_012',
        'TEST_LINKEDIN_CLIENT_ID': 'test_linkedin_client_345',
        'TEST_LINKEDIN_CLIENT_SECRET': 'test_linkedin_secret_678'
    }):
        service = OAuthService(config_path=config_path)
    
    # Cleanup
    os.unlink(config_path)
    return service


class TestOAuthProperties:
    """Property-based tests for OAuth Service correctness"""
    
    # Strategy for generating valid provider names
    valid_provider_names = st.sampled_from(['google', 'github', 'linkedin'])
    
    # Strategy for generating valid state parameters
    valid_state_params = st.one_of(
        st.none(),
        st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))
    )
    
    @given(
        provider_name=valid_provider_names,
        state=valid_state_params
    )
    @settings(
        max_examples=20, 
        deadline=3000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_oauth_provider_redirect_consistency(self, provider_name, state):
        """
        Property 1: OAuth Provider Redirect Consistency
        
        For any configured OAuth provider and valid authentication request, 
        the system should generate the correct OAuth authorization URL with 
        proper parameters and redirect the user appropriately.
        
        **Feature: universal-auth, Property 1: OAuth Provider Redirect Consistency**
        **Validates: Requirements 1.1**
        """
        service = create_test_oauth_service()
        
        # Generate OAuth authorization URL
        auth_url = service.generate_auth_url(provider_name, state)
        
        # Parse the generated URL
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        
        # Get provider configuration for validation
        provider_config = service.providers[provider_name]
        
        # Property assertions: URL must have correct structure and parameters
        
        # 1. URL should start with the provider's auth URL
        expected_base_url = urlparse(provider_config.auth_url)
        assert parsed_url.scheme == expected_base_url.scheme
        assert parsed_url.netloc == expected_base_url.netloc
        assert parsed_url.path == expected_base_url.path
        
        # 2. Required OAuth2 parameters must be present
        assert 'client_id' in query_params
        assert 'redirect_uri' in query_params
        assert 'scope' in query_params
        assert 'response_type' in query_params
        assert 'state' in query_params
        
        # 3. Parameter values must match provider configuration
        assert query_params['client_id'][0] == provider_config.client_id
        assert query_params['redirect_uri'][0] == provider_config.redirect_uri
        assert query_params['response_type'][0] == 'code'
        
        # 4. Scopes must match provider configuration
        url_scopes = set(query_params['scope'][0].split(' '))
        config_scopes = set(provider_config.scopes)
        assert url_scopes == config_scopes
        
        # 5. State parameter handling
        url_state = query_params['state'][0]
        if state is not None:
            # If state was provided, it should be used
            assert url_state == state
        else:
            # If no state provided, one should be generated
            assert len(url_state) > 0
        
        # 6. State should be stored in service sessions for validation
        assert url_state in service.sessions
        assert service.sessions[url_state]['provider'] == provider_name
        
        # 7. Provider-specific parameters should be included
        if provider_config.type == ProviderType.GOOGLE:
            assert 'access_type' in query_params
            assert query_params['access_type'][0] == 'offline'
            assert 'prompt' in query_params
            assert query_params['prompt'][0] == 'consent'
        elif provider_config.type == ProviderType.GITHUB:
            assert 'allow_signup' in query_params
            assert query_params['allow_signup'][0] == 'true'
    
    @given(provider_name=valid_provider_names)
    @settings(max_examples=10, deadline=2000)
    def test_oauth_url_generation_idempotency(self, provider_name):
        """
        Property: OAuth URL generation should be consistent for the same provider
        
        For any provider, generating URLs multiple times should produce URLs
        with the same base structure and required parameters (excluding state).
        
        **Feature: universal-auth, Property 1: OAuth Provider Redirect Consistency**
        **Validates: Requirements 1.1**
        """
        service = create_test_oauth_service()
        
        # Generate multiple URLs for the same provider
        url1 = service.generate_auth_url(provider_name, "test_state_1")
        url2 = service.generate_auth_url(provider_name, "test_state_2")
        
        # Parse both URLs
        parsed1 = urlparse(url1)
        parsed2 = urlparse(url2)
        params1 = parse_qs(parsed1.query)
        params2 = parse_qs(parsed2.query)
        
        # Base URL structure should be identical
        assert parsed1.scheme == parsed2.scheme
        assert parsed1.netloc == parsed2.netloc
        assert parsed1.path == parsed2.path
        
        # Core parameters should be identical (except state)
        core_params = ['client_id', 'redirect_uri', 'scope', 'response_type']
        for param in core_params:
            assert params1[param] == params2[param]
        
        # State parameters should be different (as expected)
        assert params1['state'][0] != params2['state'][0]
        assert params1['state'][0] == "test_state_1"
        assert params2['state'][0] == "test_state_2"
    
    def test_oauth_provider_validation_property(self):
        """
        Property: Provider validation should be consistent
        
        For any provider name, validation should return True for configured
        providers and False for unconfigured providers.
        
        **Feature: universal-auth, Property 1: OAuth Provider Redirect Consistency**
        **Validates: Requirements 1.1**
        """
        service = create_test_oauth_service()
        
        # Test with known configured providers
        configured_providers = ['google', 'github', 'linkedin']
        for provider in configured_providers:
            assert service.validate_provider(provider) is True
        
        # Test with known unconfigured providers
        unconfigured_providers = ['facebook', 'twitter', 'apple', 'invalid', '']
        for provider in unconfigured_providers:
            assert service.validate_provider(provider) is False
    
    @given(provider_name=st.text(min_size=1, max_size=50))
    @settings(max_examples=20, deadline=2000)
    def test_oauth_invalid_provider_handling(self, provider_name):
        """
        Property: Invalid provider names should be handled consistently
        
        For any invalid provider name, the system should raise a ValueError
        when attempting to generate an auth URL.
        
        **Feature: universal-auth, Property 1: OAuth Provider Redirect Consistency**
        **Validates: Requirements 1.1**
        """
        service = create_test_oauth_service()
        
        # Skip valid provider names
        assume(provider_name not in ['google', 'github', 'linkedin'])
        
        # Should raise ValueError for invalid providers
        with pytest.raises(ValueError, match=re.escape(f"Provider {provider_name} not configured")):
            service.generate_auth_url(provider_name)
    
    @given(
        provider_name=valid_provider_names,
        state=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))
    )
    @settings(max_examples=10, deadline=2000)
    def test_oauth_state_session_management(self, provider_name, state):
        """
        Property: State parameters should be properly managed in sessions
        
        For any valid provider and state, the generated state should be stored
        in the service sessions with correct provider association.
        
        **Feature: universal-auth, Property 1: OAuth Provider Redirect Consistency**
        **Validates: Requirements 1.1**
        """
        service = create_test_oauth_service()
        
        # Clear existing sessions
        service.sessions.clear()
        
        # Generate auth URL
        auth_url = service.generate_auth_url(provider_name, state)
        
        # Verify state is stored in sessions
        assert state in service.sessions
        assert service.sessions[state]['provider'] == provider_name
        assert 'created_at' in service.sessions[state]
        assert isinstance(service.sessions[state]['created_at'], (int, float))
        
        # Verify URL contains the state
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        assert query_params['state'][0] == state