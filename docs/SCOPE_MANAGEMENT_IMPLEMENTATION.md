# Dynamic Scope Management Implementation

## Overview

The dynamic scope management system provides real-time tracking and invalidation of user permissions and sessions when roles or capabilities change. This ensures that users always have the correct permissions and that outdated sessions are automatically invalidated.

## Components Implemented

### 1. Core Scope Manager (`services/scope_manager.py`)
- **ScopeVersionManager**: Main class for managing scope versions
- **Database Models**: 
  - `ScopeVersion`: Tracks user scope versions per tenant
  - `ScopeChangeEvent`: Records all scope change events
  - `SessionScopeTracking`: Links sessions to scope versions
- **Key Features**:
  - Monotonic version increments
  - Change detection and event logging
  - Session invalidation based on scope versions
  - Background polling for scope changes

### 2. Session Service Integration (`services/session_service.py`)
- Enhanced session management with scope version tracking
- Automatic session invalidation when scopes are outdated
- JWT tokens include scope version information
- Session refresh updates scope versions

### 3. RBAC Service Integration (`services/rbac_service.py`)
- Updated to work with scope manager
- Automatic scope version updates when roles change
- Capability inheritance and role hierarchy support

### 4. Middleware (`auth/scope_middleware.py`)
- **ScopeVersionMiddleware**: Automatically checks scope versions on API requests
- **CapabilityRequiredMiddleware**: Enforces capability requirements per endpoint
- Automatic session invalidation for outdated tokens
- Request context enrichment with user capabilities

### 5. WebSocket Notifications (`services/websocket_service.py`, `auth/websocket_routes.py`)
- **ConnectionManager**: Manages WebSocket connections per user/tenant
- **WebSocketNotificationService**: Sends real-time notifications
- **Notification Types**:
  - Scope changes
  - Session invalidations
  - Role changes
  - Tenant access changes
- Keep-alive mechanism and connection management

### 6. Configuration System (`services/scope_config.py`, `config/auth/scope_config.yaml`)
- Comprehensive configuration for all scope management features
- Polling intervals and batch sizes
- Session invalidation settings
- WebSocket configuration
- Caching and security settings
- Rate limiting configuration

### 7. Property Tests (`tests/test_scope_properties_simple.py`)
- **Property 18**: Dynamic Scope Version Management
- **Property 20**: Scope Polling and Invalidation
- Validates monotonic version increases
- Tests scope change detection accuracy
- Verifies user and tenant isolation
- Confirms event creation and tracking

## Key Features

### Scope Version Management
- Each user has a scope version per tenant context
- Versions increment monotonically when capabilities or roles change
- Checksums prevent unnecessary version increments for identical scopes
- Change events track what specifically changed

### Session Invalidation
- Sessions store their scope version at creation time
- Middleware automatically checks if session scope version is current
- Outdated sessions are invalidated automatically
- Grace periods and notification options configurable

### Real-time Notifications
- WebSocket connections provide real-time updates
- Users notified immediately when permissions change
- Session invalidation notifications with clear action items
- Connection management with automatic cleanup

### Background Processing
- Polling mechanism checks for scope changes periodically
- Batch processing of change events
- Automatic session cleanup for expired or outdated sessions
- Configurable intervals and batch sizes

## Configuration Options

### Polling Configuration
```yaml
polling:
  enabled: true
  interval_seconds: 30
  batch_size: 100
```

### Session Invalidation
```yaml
session_invalidation:
  enabled: true
  grace_period_minutes: 5
  notify_before_invalidation: true
```

### WebSocket Settings
```yaml
websocket:
  enabled: true
  keepalive_interval_seconds: 30
  connection_timeout_seconds: 300
  max_connections_per_user: 5
```

## API Integration

### Middleware Setup
```python
from auth.scope_middleware import create_scope_middleware

app.add_middleware(
    create_scope_middleware,
    db_session_factory=get_db_session,
    secret_key=SECRET_KEY,
    excluded_paths=["/auth/login", "/health"]
)
```

### WebSocket Connection
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/notifications?token=${jwt_token}`);

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'scope_change') {
        // Handle scope change notification
        window.location.reload(); // Or refresh session
    }
};
```

### Capability Checking
```python
# In route handlers
if not hasattr(request.state, 'capabilities'):
    raise HTTPException(401, "Authentication required")

if 'admin:users' not in request.state.capabilities:
    raise HTTPException(403, "Insufficient permissions")
```

## Database Schema

### Scope Versions Table
```sql
CREATE TABLE scope_versions (
    user_id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR PRIMARY KEY,
    version INTEGER NOT NULL DEFAULT 1,
    capabilities JSON NOT NULL DEFAULT '[]',
    roles JSON NOT NULL DEFAULT '[]',
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    checksum VARCHAR NOT NULL
);
```

### Scope Change Events Table
```sql
CREATE TABLE scope_change_events (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    tenant_id VARCHAR,
    old_version INTEGER NOT NULL,
    new_version INTEGER NOT NULL,
    changed_capabilities JSON NOT NULL DEFAULT '[]',
    changed_roles JSON NOT NULL DEFAULT '[]',
    change_type VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    processed BOOLEAN NOT NULL DEFAULT FALSE
);
```

## Testing

### Property Tests Validate
- **Monotonic Version Increases**: Scope versions never decrease
- **Change Detection**: Only actual changes trigger version increments
- **User Isolation**: Changes to one user don't affect others
- **Tenant Isolation**: Changes in one tenant don't affect others
- **Event Creation**: All scope changes create proper events
- **Session Invalidation**: Outdated sessions are correctly identified and invalidated

### Test Coverage
- 6 property-based tests using Hypothesis
- Tests run with 50+ examples each for comprehensive validation
- Mock implementations for testing without database dependencies
- Validates both positive and negative cases

## Performance Considerations

### Caching
- Scope versions cached for configurable TTL (default 5 minutes)
- Capability lookups cached separately (default 10 minutes)
- Cache invalidation on scope changes

### Batch Processing
- Change events processed in configurable batches
- Polling intervals adjustable based on load
- Rate limiting prevents abuse

### Database Optimization
- Composite primary keys for efficient lookups
- Indexes on frequently queried columns
- Cleanup of old change events

## Security Features

### Token Validation
- JWT tokens include scope version for validation
- Automatic token invalidation on scope changes
- Secure WebSocket connections with token validation

### Rate Limiting
- Configurable limits on scope updates
- WebSocket message rate limiting
- API request rate limiting per user

### Audit Trail
- Complete audit trail of all scope changes
- Change events include old and new values
- Timestamps and change types tracked

## Deployment Notes

### Environment Variables
```bash
SCOPE_POLLING_ENABLED=true
SCOPE_POLLING_INTERVAL=30
WEBSOCKET_ENABLED=true
SCOPE_CACHE_TTL=300
```

### Production Considerations
- Enable secure WebSocket connections (WSS)
- Configure appropriate polling intervals for load
- Set up monitoring for scope change events
- Regular cleanup of old change events
- Database connection pooling for high concurrency

## Future Enhancements

### Planned Features
- Scope change approval workflows
- Temporary scope grants with expiration
- Scope change rollback capabilities
- Advanced notification filtering
- Metrics and monitoring dashboard

### Integration Points
- External identity providers
- Audit log systems
- Monitoring and alerting platforms
- Admin dashboard for scope management

## Conclusion

The dynamic scope management system provides a robust, real-time solution for managing user permissions and session validity. With comprehensive testing, configurable behavior, and real-time notifications, it ensures users always have the correct permissions while maintaining security and performance.