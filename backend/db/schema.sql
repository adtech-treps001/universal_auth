
CREATE TABLE users (
  id UUID PRIMARY KEY,
  name TEXT,
  email TEXT UNIQUE,
  phone TEXT UNIQUE,
  role TEXT,
  created_at TIMESTAMP DEFAULT now()
);
