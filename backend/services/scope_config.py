"""
Scope Configuration Service

This module loads and manages configuration for the dynamic scope management system.
"""

import yaml
import os
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import timedelta

@dataclass
class PollingConfig:
    """Configuration for scope change polling"""
    enabled: bool = True
    interval_seconds: int = 30
    batch_size: int = 100

@dataclass
class SessionInvalidationConfig:
    """Configuration for session invalidation"""
    enabled: bool = True
    grace_period_minutes: int = 5
    notify_before_invalidation: bool = True

@dataclass
class VersionCheckingConfig:
    """Configuration for scope version checking"""
    enabled: bool = True
    max_age_minutes: int = 30
    check_on_api_request: bool = True

@dataclass
class WebSocketConfig:
    """Configuration for WebSocket notifications"""
    enabled: bool = True
    keepalive_interval_seconds: int = 30
    connection_timeout_seconds: int = 300
    max_connections_per_user: int = 5

@dataclass
class CachingConfig:
    """Configuration for caching"""
    enabled: bool = True
    scope_version_ttl_seconds: int = 300
    capability_cache_ttl_seconds: int = 600

@dataclass
class LoggingConfig:
    """Configuration for logging"""
    log_scope_changes: bool = True
    log_session_invalidations: bool = True
    log_websocket_events: bool = False

@dataclass
class SecurityConfig:
    """Configuration for security settings"""
    require_secure_websocket: bool = False
    validate_token_on_websocket: bool = True
    max_failed_scope_checks: int = 3

@dataclass
class NotificationTemplate:
    """Template for notifications"""
    title: str
    message: str
    action_required: bool = False

@dataclass
class RateLimitingConfig:
    """Configuration for rate limiting"""
    scope_updates_per_minute: int = 60
    websocket_messages_per_minute: int = 120
    scope_checks_per_minute: int = 300

class ScopeConfig:
    """Main configuration class for scope management"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                '../../config/auth/scope_config.yaml'
            )
        
        self.config_path = config_path
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            scope_mgmt = config_data.get('scope_management', {})
            
            # Load sub-configurations
            self.polling = PollingConfig(**scope_mgmt.get('polling', {}))
            self.session_invalidation = SessionInvalidationConfig(
                **scope_mgmt.get('session_invalidation', {})
            )
            self.version_checking = VersionCheckingConfig(
                **scope_mgmt.get('version_checking', {})
            )
            self.websocket = WebSocketConfig(**scope_mgmt.get('websocket', {}))
            self.caching = CachingConfig(**scope_mgmt.get('caching', {}))
            self.logging = LoggingConfig(**scope_mgmt.get('logging', {}))
            self.security = SecurityConfig(**scope_mgmt.get('security', {}))
            self.rate_limiting = RateLimitingConfig(
                **config_data.get('rate_limiting', {})
            )
            
            # Load scope change triggers
            self.scope_change_triggers = config_data.get('scope_change_triggers', [])
            
            # Load notification templates
            notifications = config_data.get('notifications', {})
            self.notifications = {}
            for key, template_data in notifications.items():
                self.notifications[key] = NotificationTemplate(**template_data)
            
        except FileNotFoundError:
            # Use default configuration if file not found
            self._load_defaults()
        except Exception as e:
            raise ValueError(f"Error loading scope configuration: {e}")
    
    def _load_defaults(self):
        """Load default configuration values"""
        self.polling = PollingConfig()
        self.session_invalidation = SessionInvalidationConfig()
        self.version_checking = VersionCheckingConfig()
        self.websocket = WebSocketConfig()
        self.caching = CachingConfig()
        self.logging = LoggingConfig()
        self.security = SecurityConfig()
        self.rate_limiting = RateLimitingConfig()
        
        self.scope_change_triggers = [
            'role_assignment',
            'role_removal',
            'capability_grant',
            'capability_revoke',
            'tenant_membership_change',
            'admin_override'
        ]
        
        self.notifications = {
            'scope_change': NotificationTemplate(
                title="Permissions Updated",
                message="Your permissions have been updated. Please refresh your session to continue.",
                action_required=True
            ),
            'session_invalidated': NotificationTemplate(
                title="Session Expired",
                message="Your session has been invalidated due to permission changes. Please log in again.",
                action_required=True
            ),
            'role_change': NotificationTemplate(
                title="Role Changed",
                message="Your role has been changed. New permissions are now active.",
                action_required=False
            )
        }
    
    def get_polling_interval(self) -> timedelta:
        """Get polling interval as timedelta"""
        return timedelta(seconds=self.polling.interval_seconds)
    
    def get_grace_period(self) -> timedelta:
        """Get session invalidation grace period as timedelta"""
        return timedelta(minutes=self.session_invalidation.grace_period_minutes)
    
    def get_max_scope_check_age(self) -> timedelta:
        """Get maximum scope check age as timedelta"""
        return timedelta(minutes=self.version_checking.max_age_minutes)
    
    def get_websocket_keepalive_interval(self) -> timedelta:
        """Get WebSocket keepalive interval as timedelta"""
        return timedelta(seconds=self.websocket.keepalive_interval_seconds)
    
    def get_websocket_timeout(self) -> timedelta:
        """Get WebSocket connection timeout as timedelta"""
        return timedelta(seconds=self.websocket.connection_timeout_seconds)
    
    def get_scope_version_ttl(self) -> timedelta:
        """Get scope version cache TTL as timedelta"""
        return timedelta(seconds=self.caching.scope_version_ttl_seconds)
    
    def get_capability_cache_ttl(self) -> timedelta:
        """Get capability cache TTL as timedelta"""
        return timedelta(seconds=self.caching.capability_cache_ttl_seconds)
    
    def is_scope_change_trigger(self, event_type: str) -> bool:
        """Check if event type triggers scope changes"""
        return event_type in self.scope_change_triggers
    
    def get_notification_template(self, notification_type: str) -> NotificationTemplate:
        """Get notification template by type"""
        return self.notifications.get(
            notification_type,
            NotificationTemplate(
                title="Notification",
                message="You have a new notification.",
                action_required=False
            )
        )
    
    def reload(self):
        """Reload configuration from file"""
        self._load_config()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'polling': {
                'enabled': self.polling.enabled,
                'interval_seconds': self.polling.interval_seconds,
                'batch_size': self.polling.batch_size
            },
            'session_invalidation': {
                'enabled': self.session_invalidation.enabled,
                'grace_period_minutes': self.session_invalidation.grace_period_minutes,
                'notify_before_invalidation': self.session_invalidation.notify_before_invalidation
            },
            'version_checking': {
                'enabled': self.version_checking.enabled,
                'max_age_minutes': self.version_checking.max_age_minutes,
                'check_on_api_request': self.version_checking.check_on_api_request
            },
            'websocket': {
                'enabled': self.websocket.enabled,
                'keepalive_interval_seconds': self.websocket.keepalive_interval_seconds,
                'connection_timeout_seconds': self.websocket.connection_timeout_seconds,
                'max_connections_per_user': self.websocket.max_connections_per_user
            },
            'caching': {
                'enabled': self.caching.enabled,
                'scope_version_ttl_seconds': self.caching.scope_version_ttl_seconds,
                'capability_cache_ttl_seconds': self.caching.capability_cache_ttl_seconds
            },
            'logging': {
                'log_scope_changes': self.logging.log_scope_changes,
                'log_session_invalidations': self.logging.log_session_invalidations,
                'log_websocket_events': self.logging.log_websocket_events
            },
            'security': {
                'require_secure_websocket': self.security.require_secure_websocket,
                'validate_token_on_websocket': self.security.validate_token_on_websocket,
                'max_failed_scope_checks': self.security.max_failed_scope_checks
            },
            'rate_limiting': {
                'scope_updates_per_minute': self.rate_limiting.scope_updates_per_minute,
                'websocket_messages_per_minute': self.rate_limiting.websocket_messages_per_minute,
                'scope_checks_per_minute': self.rate_limiting.scope_checks_per_minute
            },
            'scope_change_triggers': self.scope_change_triggers,
            'notifications': {
                key: {
                    'title': template.title,
                    'message': template.message,
                    'action_required': template.action_required
                }
                for key, template in self.notifications.items()
            }
        }

# Global configuration instance
_scope_config = None

def get_scope_config(config_path: str = None) -> ScopeConfig:
    """Get or create scope configuration instance"""
    global _scope_config
    if _scope_config is None:
        _scope_config = ScopeConfig(config_path)
    return _scope_config

def reload_scope_config():
    """Reload scope configuration from file"""
    global _scope_config
    if _scope_config:
        _scope_config.reload()