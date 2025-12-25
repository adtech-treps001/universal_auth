package tenant

import rego.v1

# Default deny tenant access
default allow := false

# Allow if user is member of the tenant
allow if {
    input.user_id
    input.tenant_id
    input.user.tenant_memberships[input.tenant_id]
    input.user.tenant_memberships[input.tenant_id].is_active == true
}

# Allow if user has global admin access
allow if {
    input.user.capabilities[_] == "*"
}

allow if {
    input.user.capabilities[_] == "tenant:*"
}

# Tenant creation authorization
create_tenant if {
    input.user.capabilities[_] == "tenant:create"
}

create_tenant if {
    input.user.capabilities[_] == "*"
}

# Tenant management authorization
manage_tenant if {
    input.tenant_id
    input.user.tenant_memberships[input.tenant_id]
    input.user.tenant_memberships[input.tenant_id].role == "admin"
}

manage_tenant if {
    input.user.capabilities[_] == "tenant:manage"
}

manage_tenant if {
    input.user.capabilities[_] == "*"
}

# User invitation authorization
invite_users if {
    input.tenant_id
    input.user.tenant_memberships[input.tenant_id]
    input.user.tenant_memberships[input.tenant_id].role in ["admin", "power_user"]
}

invite_users if {
    input.user.capabilities[_] == "tenant:invite_users"
}

invite_users if {
    input.user.capabilities[_] == "*"
}

# Data isolation check
data_access if {
    input.tenant_id
    input.requested_tenant_id
    input.tenant_id == input.requested_tenant_id
    input.user.tenant_memberships[input.tenant_id].is_active == true
}

data_access if {
    input.user.capabilities[_] == "*"
}