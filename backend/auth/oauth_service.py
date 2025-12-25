from enum import Enum
from typing import Dict, List

class ProviderType(Enum):
    GOOGLE = 'google'
    GITHUB = 'github'
    LINKEDIN = 'linkedin'
    APPLE = 'apple'
    META = 'meta'

class ProviderConfig:
    def __init__(self, name, type_val, client_id, client_secret, auth_url, token_url, userinfo_url, scopes, redirect_uri):
        self.name = name
        self.type = type_val
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = auth_url
        self.token_url = token_url
        self.userinfo_url = userinfo_url
        self.scopes = scopes
        self.redirect_uri = redirect_uri

class OAuthService:
    def __init__(self, config_path='/app/config/auth/providers.yaml'):
        self.providers = {}
        self.sessions = {}
        self._load_providers(config_path)
    
    def _load_providers(self, config_path):
        # Mock implementation for testing
        import os
        try:
            # Try to load from environment variables for testing
            if os.getenv('TEST_GOOGLE_CLIENT_ID'):
                self.providers['google'] = ProviderConfig(
                    name='google',
                    type_val=ProviderType.GOOGLE,
                    client_id=os.getenv('TEST_GOOGLE_CLIENT_ID'),
                    client_secret=os.getenv('TEST_GOOGLE_CLIENT_SECRET'),
                    auth_url='https://accounts.google.com/o/oauth2/v2/auth',
                    token_url='https://oauth2.googleapis.com/token',
                    userinfo_url='https://openidconnect.googleapis.com/v1/userinfo',
                    scopes=['openid', 'email', 'profile'],
                    redirect_uri='http://localhost:8000/auth/callback/google'
                )
            if os.getenv('TEST_GITHUB_CLIENT_ID'):
                self.providers['github'] = ProviderConfig(
                    name='github',
                    type_val=ProviderType.GITHUB,
                    client_id=os.getenv('TEST_GITHUB_CLIENT_ID'),
                    client_secret=os.getenv('TEST_GITHUB_CLIENT_SECRET'),
                    auth_url='https://github.com/login/oauth/authorize',
                    token_url='https://github.com/login/oauth/access_token',
                    userinfo_url='https://api.github.com/user',
                    scopes=['user:email'],
                    redirect_uri='http://localhost:8000/auth/callback/github'
                )
            if os.getenv('TEST_LINKEDIN_CLIENT_ID'):
                self.providers['linkedin'] = ProviderConfig(
                    name='linkedin',
                    type_val=ProviderType.LINKEDIN,
                    client_id=os.getenv('TEST_LINKEDIN_CLIENT_ID'),
                    client_secret=os.getenv('TEST_LINKEDIN_CLIENT_SECRET'),
                    auth_url='https://www.linkedin.com/oauth/v2/authorization',
                    token_url='https://www.linkedin.com/oauth/v2/accessToken',
                    userinfo_url='https://api.linkedin.com/v2/people/~',
                    scopes=['r_liteprofile', 'r_emailaddress'],
                    redirect_uri='http://localhost:8000/auth/callback/linkedin'
                )
        except Exception as e:
            print(f'Error loading providers: {e}')
    
    def get_available_providers(self):
        return list(self.providers.keys())
    
    def validate_provider(self, provider_name):
        return provider_name in self.providers
    
    def generate_auth_url(self, provider_name, state=None):
        if provider_name not in self.providers:
            raise ValueError(f'Provider {provider_name} not configured')
        
        provider = self.providers[provider_name]
        
        if state is None:
            import secrets
            state = secrets.token_urlsafe(32)
        
        # Store state in sessions
        import time
        self.sessions[state] = {
            'provider': provider_name,
            'created_at': time.time()
        }
        
        # Build URL parameters
        from urllib.parse import urlencode
        params = {
            'client_id': provider.client_id,
            'redirect_uri': provider.redirect_uri,
            'scope': ' '.join(provider.scopes),
            'response_type': 'code',
            'state': state
        }
        
        # Add provider-specific parameters
        if provider.type == ProviderType.GOOGLE:
            params['access_type'] = 'offline'
            params['prompt'] = 'consent'
        elif provider.type == ProviderType.GITHUB:
            params['allow_signup'] = 'true'
        
        return f'{provider.auth_url}?{urlencode(params)}'
