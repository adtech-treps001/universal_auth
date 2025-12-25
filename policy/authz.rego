package authz

import rego.v1

# Default deny
default allow := false

# Allow if user has required capability
allow if {
    input.user.capabilities[_] == "*"  # Admin wildcard
}

allow if {
    input.user.capabilities[_] == input.required_capability
}

allow if {
    # Pattern matching for wildcard capabilities
    some capability in input.user.capabilities
    endswith(capability, "*")
    prefix := substring(capability, 0, count(capability) - 1)
    startswith(input.required_capability, prefix)
}

# Tenant-specific authorization
allow if {
    input.tenant_id
    input.user.tenant_memberships[input.tenant_id]
    input.user.tenant_memberships[input.tenant_id].is_active == true
    input.user.tenant_memberships[input.tenant_id].capabilities[_] == input.required_capability
}

allow if {
    input.tenant_id
    input.user.tenant_memberships[input.tenant_id]
    input.user.tenant_memberships[input.tenant_id].is_active == true
    input.user.tenant_memberships[input.tenant_id].capabilities[_] == "*"
}

# Resource-specific authorization
resource_access if {
    input.resource
    input.action
    required_cap := sprintf("%s:%s", [input.resource, input.action])
    input.user.capabilities[_] == required_cap
}

resource_access if {
    input.resource
    input.action
    input.user.capabilities[_] == "*"
}

# UI visibility rules
ui_visible if {
    input.ui_component
    required_cap := sprintf("ui:%s", [input.ui_component])
    input.user.capabilities[_] == required_cap
}

ui_visible if {
    input.ui_component
    input.user.capabilities[_] == "*"
}

ui_visible if {
    input.ui_component
    input.user.capabilities[_] == "ui:*"
}