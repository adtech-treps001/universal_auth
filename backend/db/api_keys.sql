
CREATE TABLE api_keys (
  id UUID PRIMARY KEY,
  tenant_id UUID,
  user_id UUID,
  key_hash TEXT,
  scopes TEXT[],
  created_at TIMESTAMP DEFAULT now()
);
