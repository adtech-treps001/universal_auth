"""
Tests for OAuth Service

This module contains unit tests for the OAuth authentication service,
testing provider configuration, URL generation, and token exchange.
"""

import pytest
import os
import tempfile
import yaml
from unittest.mock import patch, AsyncMock
from auth.oauth_service import OAuthService, ProviderType, ProviderConfig, OAuthTokens, UserInfo


class TestOAuthService:
    """Test cases for OAuth Service"""
    
    @pytest.fixture
    def mock_config_file(self):
        """Create a temporary config file for testing"""
        config_data = {
            'providers': {
                'google': {
                    'type': 'google',
                    'client_id_env': 'GOOGLE_CLIENT_ID',
                    'client_secret_env': 'GOOGLE_CLIENT_SECRET',
                    'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                    'token_url': 'https://oauth2.googleapis.com/token',
                    'userinfo_url': 'https://openidconnect.googleapis.com/v1/userinfo',
                    'scopes': ['openid', 'email', 'profile'],
                    'redirect_uri': 'http://localhost:8000/auth/callback/google'
                },
                'github': {
                    'type': 'github',
                    'client_id_env': 'GITHUB_CLIENT_ID',
                    'client_secret_env': 'GITHUB_CLIENT_SECRET',
                    'auth_url': 'https://github.com/login/oauth/authorize',
                    'token_url': 'https://github.com/login/oauth/access_token',
                    'userinfo_url': 'https://api.github.com/user',
                    'scopes': ['user:email'],
                    'redirect_uri': 'http://localhost:8000/auth/callback/github'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            return f.name
    
    @pytest.fixture
    def oauth_service(self, mock_config_file):
        """Create OAuth service with mock configuration"""
        with patch.dict(os.environ, {
            'GOOGLE_CLIENT_ID': 'test_google_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_google_client_secret',
            'GITHUB_CLIENT_ID': 'test_github_client_id',
            'GITHUB_CLIENT_SECRET': 'test_github_client_secret'
        }):
            service = OAuthService(config_path=mock_config_file)
            yield service
        
        # Cleanup
        os.unlink(mock_config_file)
    
    def test_load_providers(self, oauth_service):
        """Test that providers are loaded correctly from config"""
        providers = oauth_service.get_available_providers()
        assert 'google' in providers
        assert 'github' in providers
        assert len(providers) == 2
    
    def test_validate_provider(self, oauth_service):
        """Test provider validation"""
        assert oauth_service.validate_provider('google') is True
        assert oauth_service.validate_provider('github') is True
        assert oauth_service.validate_provider('invalid') is False
    
    def test_generate_auth_url(self, oauth_service):
        """Test OAuth authorization URL generation"""
        auth_url = oauth_service.generate_auth_url('google')
        
        assert 'https://accounts.google.com/o/oauth2/v2/auth' in auth_url
        assert 'client_id=test_google_client_id' in auth_url
        assert 'scope=openid+email+profile' in auth_url
        assert 'response_type=code' in auth_url
        assert 'state=' in auth_url
        assert 'access_type=offline' in auth_url  # Google-specific parameter
    
    def test_generate_auth_url_with_state(self, oauth_service):
        """Test OAuth URL generation with custom state"""
        custom_state = 'custom_state_123'
        auth_url = oauth_service.generate_auth_url('google', state=custom_state)
        
        assert f'state={custom_state}' in auth_url
        assert custom_state in oauth_service.sessions
    
    def test_generate_auth_url_invalid_provider(self, oauth_service):
        """Test OAuth URL generation with invalid provider"""
        with pytest.raises(ValueError, match="Provider invalid not configured"):
            oauth_service.generate_auth_url('invalid')
    
    def test_parse_user_info_google(self, oauth_service):
        """Test parsing Google user info"""
        google_data = {
            'sub': '123456789',
            'email': 'test@example.com',
            'name': 'Test User',
            'given_name': 'Test',
            'family_name': 'User',
            'picture': 'https://example.com/avatar.jpg'
        }
        
        user_info = oauth_service._parse_user_info(ProviderType.GOOGLE, google_data)
        
        assert user_info.provider_user_id == '123456789'
        assert user_info.email == 'test@example.com'
        assert user_info.name == 'Test User'
        assert user_info.first_name == 'Test'
        assert user_info.last_name == 'User'
        assert user_info.avatar_url == 'https://example.com/avatar.jpg'
    
    def test_parse_user_info_github(self, oauth_service):
        """Test parsing GitHub user info"""
        github_data = {
            'id': 12345,
            'email': 'test@example.com',
            'name': 'Test User',
            'avatar_url': 'https://github.com/avatar.jpg'
        }
        
        user_info = oauth_service._parse_user_info(ProviderType.GITHUB, github_data)
        
        assert user_info.provider_user_id == '12345'
        assert user_info.email == 'test@example.com'
        assert user_info.name == 'Test User'
        assert user_info.avatar_url == 'https://github.com/avatar.jpg'
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self, oauth_service):
        """Test exchanging authorization code for tokens"""
        provider = oauth_service.providers['google']
        
        mock_response_data = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'expires_in': 3600,
            'token_type': 'Bearer'
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            mock_client.return_value.__aenter__.return_value.post.return_value.json.return_value = mock_response_data
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status = AsyncMock()
            
            tokens = await oauth_service._exchange_code_for_tokens(provider, 'test_code')
            
            assert tokens.access_token == 'test_access_token'
            assert tokens.refresh_token == 'test_refresh_token'
            assert tokens.expires_in == 3600
            assert tokens.token_type == 'Bearer'
    
    @pytest.mark.asyncio
    async def test_get_user_info(self, oauth_service):
        """Test getting user info from provider"""
        provider = oauth_service.providers['google']
        
        mock_user_data = {
            'sub': '123456789',
            'email': 'test@example.com',
            'name': 'Test User',
            'given_name': 'Test',
            'family_name': 'User',
            'picture': 'https://example.com/avatar.jpg'
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock()
            mock_client.return_value.__aenter__.return_value.get.return_value.json.return_value = mock_user_data
            mock_client.return_value.__aenter__.return_value.get.return_value.raise_for_status = AsyncMock()
            
            user_info = await oauth_service._get_user_info(provider, 'test_access_token')
            
            assert user_info.provider_user_id == '123456789'
            assert user_info.email == 'test@example.com'
            assert user_info.name == 'Test User'