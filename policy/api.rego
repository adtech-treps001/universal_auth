package api

import rego.v1

# Default deny API access
default allow := false

# API endpoint authorization mapping
endpoint_capabilities := {
    "GET /auth/me": "user:profile",
    "PUT /auth/profile": "user:update_profile",
    "GET /auth/providers": "auth:list_providers",
    "POST /auth/oauth/redirect": "auth:oauth",
    "POST /auth/otp/send": "auth:otp",
    "POST /auth/otp/verify": "auth:otp",
    "GET /tenants": "tenant:list",
    "POST /tenants": "tenant:create",
    "GET /tenants/{id}": "tenant:read",
    "PUT /tenants/{id}": "tenant:update",
    "DELETE /tenants/{id}": "tenant:delete",
    "POST /tenants/{id}/users": "tenant:manage_users",
    "DELETE /tenants/{id}/users/{user_id}": "tenant:manage_users",
    "GET /tenants/{id}/users": "tenant:read_users",
    "POST /tenants/{id}/invite": "tenant:invite_users",
    "GET /rbac/roles": "rbac:list_roles",
    "POST /rbac/assign": "rbac:assign_role",
    "DELETE /rbac/remove": "rbac:remove_role",
    "GET /rbac/capabilities": "rbac:list_capabilities"
}

# Allow if user has required capability for the endpoint
allow if {
    endpoint_key := sprintf("%s %s", [input.method, input.path])
    required_capability := endpoint_capabilities[endpoint_key]
    input.user.capabilities[_] == required_capability
}

allow if {
    input.user.capabilities[_] == "*"
}

# Pattern matching for parameterized endpoints
allow if {
    some pattern, capability in endpoint_capabilities
    regex.match(pattern_to_regex(pattern), sprintf("%s %s", [input.method, input.path]))
    input.user.capabilities[_] == capability
}

# Convert endpoint pattern to regex
pattern_to_regex(pattern) := regex if {
    # Replace {id} with [^/]+ for regex matching
    regex := replace(pattern, "{id}", "[^/]+")
}

pattern_to_regex(pattern) := regex if {
    # Replace {user_id} with [^/]+ for regex matching  
    regex := replace(pattern, "{user_id}", "[^/]+")
}

# Rate limiting check
rate_limit_ok if {
    input.rate_limit
    input.rate_limit.current < input.rate_limit.limit
}

rate_limit_ok if {
    not input.rate_limit
}

# Combined authorization
api_access if {
    allow
    rate_limit_ok
}