
package authz
default allow = false

allow {
  required := data.features[input.feature].required_capabilities
  all(cap in input.role_capabilities; cap in required)
  all(cap in input.provider_capabilities; cap in required)
  input.resource_scope == null
}

allow {
  required := data.features[input.feature].required_capabilities
  all(cap in input.role_capabilities; cap in required)
  all(cap in input.provider_capabilities; cap in required)
  input.resource_scope == data.resource_scopes[input.feature]
}
