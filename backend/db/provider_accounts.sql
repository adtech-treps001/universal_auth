
CREATE TABLE provider_accounts (
  id UUID PRIMARY KEY,
  user_id UUID,
  provider TEXT,
  label TEXT,
  granted_capabilities TEXT[],
  created_at TIMESTAMP DEFAULT now()
);
