
CREATE TABLE auth_audit_logs (
  id UUID PRIMARY KEY,
  user_id UUID,
  tenant_id UUID,
  action TEXT,
  decision TEXT,
  context JSONB,
  created_at TIMESTAMP DEFAULT now()
);
