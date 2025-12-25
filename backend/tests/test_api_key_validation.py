"""
Tests for API Key Validation Service

Comprehensive tests for API key validation, scope checking, rate limiting,
and access control functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from services.api_key_validation import APIKeyValidationService, ScopeValidator, RateLimitManager
from services.api_key_service import APIKeyService
from services.rbac_service import RBACService
from models.api_key import APIKey, APIKeyUsageLog, APIKeyStatus, APIKeyProvider
from models.user import User
from models.project import Project

class TestAPIKeyValidationService:
    """Test API key validation service"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def validation_service(self, mock_db):
        """Create validation service instance"""
        return APIKeyValidationService(mock_db)
    
    @pytest.fixture
    def sample_api_key(self):
        """Create sample API key"""
        return APIKey(
            id="test-key-id",
            key_name="Test Key",
            provider=APIKeyProvider.OPENAI.value,
            encrypted_key=b"encrypted_key_data",
            key_hash="test_hash",
            project_id="test-project",
            tenant_id="test-tenant",
            owner_id="test-owner",
            status=APIKeyStatus.ACTIVE.value,
            scopes=["chat.completions", "embeddings"],
            allowed_roles=["developer", "admin"],
            model_access=["gpt-4", "gpt-3.5-turbo"],
            ip_whitelist=["192.168.1.0/24", "10.0.0.1"],
            rate_limits={
                "requests_per_minute": 60,
                "tokens_per_minute": 10000,
                "requests_per_day": 1000
            },
            expires_at=datetime.utcnow() + timedelta(days=30),
            usage_count=0,
            version=1
        )
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user"""
        return User(
            id="test-user",
            email="test@example.com",
            tenant_id="test-tenant"
        )
    
    def test_validate_api_key_success(self, validation_service, mock_db, sample_api_key, sample_user):
        """Test successful API key validation"""
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        # Mock RBAC service
        with patch.object(validation_service, 'rbac_service') as mock_rbac:
            mock_rbac.get_user_roles.return_value = [Mock(name="developer")]
            
            request_context = {
                'client_ip': '192.168.1.100',
                'scopes': ['chat.completions'],
                'model': 'gpt-4',
                'endpoint': '/api/chat/completions',
                'method': 'POST'
            }
            
            result = validation_service.validate_api_key(
                key_id="test-key-id",
                user_id="test-user",
                request_context=request_context
            )
            
            assert result['valid'] is True
            assert result['message'] == "API key validated successfully"
            assert result['key_id'] == "test-key-id"
            assert result['provider'] == APIKeyProvider.OPENAI.value
            assert 'chat.completions' in result['allowed_scopes']
    
    def test_validate_api_key_not_found(self, validation_service, mock_db):
        """Test validation with non-existent API key"""
        
        # Mock database query returning None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        request_context = {'client_ip': '192.168.1.100'}
        
        result = validation_service.validate_api_key(
            key_id="nonexistent-key",
            user_id="test-user",
            request_context=request_context
        )
        
        assert result['valid'] is False
        assert result['message'] == "API key not found"
    
    def test_validate_api_key_inactive(self, validation_service, mock_db, sample_api_key):
        """Test validation with inactive API key"""
        
        sample_api_key.status = APIKeyStatus.INACTIVE.value
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        request_context = {'client_ip': '192.168.1.100'}
        
        result = validation_service.validate_api_key(
            key_id="test-key-id",
            user_id="test-user",
            request_context=request_context
        )
        
        assert result['valid'] is False
        assert result['message'] == "API key is inactive"
    
    def test_validate_api_key_expired(self, validation_service, mock_db, sample_api_key):
        """Test validation with expired API key"""
        
        sample_api_key.expires_at = datetime.utcnow() - timedelta(days=1)
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        request_context = {'client_ip': '192.168.1.100'}
        
        result = validation_service.validate_api_key(
            key_id="test-key-id",
            user_id="test-user",
            request_context=request_context
        )
        
        assert result['valid'] is False
        assert result['message'] == "API key has expired"
    
    def test_validate_api_key_insufficient_permissions(self, validation_service, mock_db, sample_api_key):
        """Test validation with insufficient user permissions"""
        
        sample_api_key.owner_id = "different-owner"
        sample_api_key.allowed_roles = ["admin"]
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        # Mock RBAC service returning user without admin role
        with patch.object(validation_service, 'rbac_service') as mock_rbac:
            mock_rbac.get_user_roles.return_value = [Mock(name="developer")]
            
            request_context = {'client_ip': '192.168.1.100'}
            
            result = validation_service.validate_api_key(
                key_id="test-key-id",
                user_id="test-user",
                request_context=request_context
            )
            
            assert result['valid'] is False
            assert result['message'] == "Insufficient permissions to use this API key"
    
    def test_validate_api_key_ip_restriction(self, validation_service, mock_db, sample_api_key):
        """Test validation with IP address restrictions"""
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        # Mock RBAC service
        with patch.object(validation_service, 'rbac_service') as mock_rbac:
            mock_rbac.get_user_roles.return_value = [Mock(name="developer")]
            
            # Test with disallowed IP
            request_context = {'client_ip': '203.0.113.1'}  # Outside whitelist
            
            result = validation_service.validate_api_key(
                key_id="test-key-id",
                user_id="test-user",
                request_context=request_context
            )
            
            assert result['valid'] is False
            assert result['message'] == "IP address not allowed"
    
    def test_validate_api_key_insufficient_scopes(self, validation_service, mock_db, sample_api_key):
        """Test validation with insufficient scopes"""
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        # Mock RBAC service
        with patch.object(validation_service, 'rbac_service') as mock_rbac:
            mock_rbac.get_user_roles.return_value = [Mock(name="developer")]
            
            request_context = {
                'client_ip': '192.168.1.100',
                'scopes': ['images', 'fine_tuning']  # Not in allowed scopes
            }
            
            result = validation_service.validate_api_key(
                key_id="test-key-id",
                user_id="test-user",
                request_context=request_context
            )
            
            assert result['valid'] is False
            assert result['message'] == "Insufficient scopes"
    
    def test_validate_api_key_model_restriction(self, validation_service, mock_db, sample_api_key):
        """Test validation with model access restrictions"""
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        # Mock RBAC service
        with patch.object(validation_service, 'rbac_service') as mock_rbac:
            mock_rbac.get_user_roles.return_value = [Mock(name="developer")]
            
            request_context = {
                'client_ip': '192.168.1.100',
                'scopes': ['chat.completions'],
                'model': 'claude-3'  # Not in allowed models
            }
            
            result = validation_service.validate_api_key(
                key_id="test-key-id",
                user_id="test-user",
                request_context=request_context
            )
            
            assert result['valid'] is False
            assert result['message'] == "Model 'claude-3' not allowed"
    
    def test_check_scope_access_success(self, validation_service, mock_db, sample_api_key):
        """Test successful scope access check"""
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        result = validation_service.check_scope_access(
            key_id="test-key-id",
            required_scopes=["chat.completions"]
        )
        
        assert result is True
    
    def test_check_scope_access_insufficient(self, validation_service, mock_db, sample_api_key):
        """Test scope access check with insufficient scopes"""
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        result = validation_service.check_scope_access(
            key_id="test-key-id",
            required_scopes=["images", "fine_tuning"]
        )
        
        assert result is False
    
    def test_rate_limit_check_success(self, validation_service, mock_db, sample_api_key):
        """Test successful rate limit check"""
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        request_context = {
            'endpoint': '/api/chat/completions',
            'method': 'POST'
        }
        
        result = validation_service.check_rate_limit(
            key_id="test-key-id",
            request_context=request_context
        )
        
        assert result['allowed'] is True
        assert 'remaining_requests' in result
    
    def test_rate_limit_exceeded(self, validation_service, mock_db, sample_api_key):
        """Test rate limit exceeded scenario"""
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        # Simulate rate limit cache with many recent requests
        cache_key = f"{sample_api_key.id}"
        current_time = 1000000000.0
        
        # Fill cache with requests at rate limit
        validation_service._rate_limit_cache[cache_key] = [
            current_time - i for i in range(60)  # 60 requests in last minute
        ]
        
        request_context = {
            'endpoint': '/api/chat/completions',
            'method': 'POST'
        }
        
        with patch('time.time', return_value=current_time):
            result = validation_service.check_rate_limit(
                key_id="test-key-id",
                request_context=request_context
            )
        
        assert result['allowed'] is False
        assert result['reason'] == 'Requests per minute limit exceeded'
    
    def test_get_key_permissions(self, validation_service, mock_db, sample_api_key):
        """Test getting key permissions"""
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        # Mock RBAC service
        with patch.object(validation_service, 'rbac_service') as mock_rbac:
            mock_rbac.get_user_roles.return_value = [Mock(name="developer")]
            
            permissions = validation_service.get_key_permissions(
                key_id="test-key-id",
                user_id="test-user"
            )
            
            assert permissions['key_id'] == "test-key-id"
            assert permissions['has_access'] is True
            assert permissions['provider'] == APIKeyProvider.OPENAI.value
            assert permissions['scopes'] == ["chat.completions", "embeddings"]

class TestScopeValidator:
    """Test scope validation utilities"""
    
    def test_validate_scopes_all_valid(self):
        """Test validation with all valid scopes"""
        
        scopes = ["chat.completions", "embeddings", "models"]
        result = ScopeValidator.validate_scopes(scopes)
        
        assert result['all_valid'] is True
        assert result['valid_scopes'] == scopes
        assert result['invalid_scopes'] == []
    
    def test_validate_scopes_some_invalid(self):
        """Test validation with some invalid scopes"""
        
        scopes = ["chat.completions", "invalid@scope", "embeddings", ""]
        result = ScopeValidator.validate_scopes(scopes)
        
        assert result['all_valid'] is False
        assert "chat.completions" in result['valid_scopes']
        assert "embeddings" in result['valid_scopes']
        assert "invalid@scope" in result['invalid_scopes']
        assert "" in result['invalid_scopes']
    
    def test_get_scope_hierarchy(self):
        """Test scope hierarchy generation"""
        
        scope = "api.chat.completions.stream"
        hierarchy = ScopeValidator.get_scope_hierarchy(scope)
        
        expected = ["api", "api.chat", "api.chat.completions", "api.chat.completions.stream"]
        assert hierarchy == expected
    
    def test_check_scope_permission_direct_match(self):
        """Test scope permission with direct match"""
        
        allowed_scopes = ["chat.completions", "embeddings"]
        required_scope = "chat.completions"
        
        result = ScopeValidator.check_scope_permission(allowed_scopes, required_scope)
        assert result is True
    
    def test_check_scope_permission_wildcard(self):
        """Test scope permission with wildcard"""
        
        allowed_scopes = ["chat.*", "embeddings"]
        required_scope = "chat.completions"
        
        result = ScopeValidator.check_scope_permission(allowed_scopes, required_scope)
        assert result is True
    
    def test_check_scope_permission_global_wildcard(self):
        """Test scope permission with global wildcard"""
        
        allowed_scopes = ["*"]
        required_scope = "any.scope.here"
        
        result = ScopeValidator.check_scope_permission(allowed_scopes, required_scope)
        assert result is True
    
    def test_check_scope_permission_no_match(self):
        """Test scope permission with no match"""
        
        allowed_scopes = ["chat.completions", "embeddings"]
        required_scope = "images.generate"
        
        result = ScopeValidator.check_scope_permission(allowed_scopes, required_scope)
        assert result is False

class TestRateLimitManager:
    """Test rate limit management utilities"""
    
    def test_calculate_rate_limit_reset_minute(self):
        """Test rate limit reset calculation for minute"""
        
        current_time = datetime(2023, 1, 1, 12, 30, 45)
        reset_time = RateLimitManager.calculate_rate_limit_reset("minute", current_time)
        
        expected = datetime(2023, 1, 1, 12, 31, 0)
        assert reset_time == expected
    
    def test_calculate_rate_limit_reset_hour(self):
        """Test rate limit reset calculation for hour"""
        
        current_time = datetime(2023, 1, 1, 12, 30, 45)
        reset_time = RateLimitManager.calculate_rate_limit_reset("hour", current_time)
        
        expected = datetime(2023, 1, 1, 13, 0, 0)
        assert reset_time == expected
    
    def test_calculate_rate_limit_reset_day(self):
        """Test rate limit reset calculation for day"""
        
        current_time = datetime(2023, 1, 1, 12, 30, 45)
        reset_time = RateLimitManager.calculate_rate_limit_reset("day", current_time)
        
        expected = datetime(2023, 1, 2, 0, 0, 0)
        assert reset_time == expected
    
    def test_get_rate_limit_window(self):
        """Test rate limit window calculation"""
        
        minute_window = RateLimitManager.get_rate_limit_window("minute")
        assert minute_window == timedelta(minutes=1)
        
        hour_window = RateLimitManager.get_rate_limit_window("hour")
        assert hour_window == timedelta(hours=1)
        
        day_window = RateLimitManager.get_rate_limit_window("day")
        assert day_window == timedelta(days=1)

class TestAPIKeyValidationIntegration:
    """Integration tests for API key validation"""
    
    @pytest.fixture
    def validation_service(self, mock_db):
        """Create validation service with mocked dependencies"""
        service = APIKeyValidationService(mock_db)
        service.api_key_service = Mock(spec=APIKeyService)
        service.rbac_service = Mock(spec=RBACService)
        return service
    
    def test_full_validation_workflow(self, validation_service, mock_db, sample_api_key):
        """Test complete validation workflow"""
        
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        validation_service.rbac_service.get_user_roles.return_value = [Mock(name="developer")]
        
        # Mock usage log creation
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        request_context = {
            'client_ip': '192.168.1.100',
            'user_agent': 'TestAgent/1.0',
            'scopes': ['chat.completions'],
            'model': 'gpt-4',
            'endpoint': '/api/chat/completions',
            'method': 'POST',
            'estimated_tokens': 100
        }
        
        # Perform validation
        result = validation_service.validate_api_key(
            key_id="test-key-id",
            user_id="test-user",
            request_context=request_context
        )
        
        # Verify result
        assert result['valid'] is True
        assert result['key_id'] == "test-key-id"
        assert result['provider'] == APIKeyProvider.OPENAI.value
        
        # Verify usage tracking was called
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    def test_validation_with_error_handling(self, validation_service, mock_db):
        """Test validation with database errors"""
        
        # Mock database error
        mock_db.query.side_effect = Exception("Database error")
        
        request_context = {'client_ip': '192.168.1.100'}
        
        result = validation_service.validate_api_key(
            key_id="test-key-id",
            user_id="test-user",
            request_context=request_context
        )
        
        assert result['valid'] is False
        assert result['message'] == "Validation error occurred"
    
    def test_concurrent_rate_limiting(self, validation_service, mock_db, sample_api_key):
        """Test rate limiting under concurrent access"""
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_api_key
        
        request_context = {
            'endpoint': '/api/chat/completions',
            'method': 'POST'
        }
        
        # Simulate multiple concurrent requests
        results = []
        for i in range(65):  # Exceed rate limit of 60
            result = validation_service.check_rate_limit(
                key_id="test-key-id",
                request_context=request_context
            )
            results.append(result)
        
        # First 60 should be allowed, rest should be denied
        allowed_count = sum(1 for r in results if r['allowed'])
        denied_count = sum(1 for r in results if not r['allowed'])
        
        assert allowed_count <= 60  # Should not exceed rate limit
        assert denied_count > 0     # Some should be denied