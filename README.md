# Universal Auth System

A comprehensive, production-ready authentication and authorization system with multi-tenant support, OAuth integration, OTP authentication, RBAC, API key management, and comprehensive security monitoring.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for development)
- Node.js 18+ (for frontend development)

### One-Command Deployment

```bash
# Clone and deploy
git clone <repository-url>
cd universal_auth
python scripts/deploy.py
```

This will:
- ✅ Check prerequisites
- 🔧 Set up environment
- 🏗️ Build Docker images
- 🚀 Start all services
- 🏥 Run health checks
- 🧪 Execute tests
- 🎭 Generate mock data

### Manual Deployment

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 2. Build and start services
docker-compose up -d

# 3. Wait for services to be ready
docker-compose logs -f

# 4. Generate test data (optional)
python scripts/generate_mock_data.py

# 5. Run tests
python scripts/run_tests.py
```

## 📍 Service URLs

After deployment, access these services:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:3000/admin
- **OPA Console**: http://localhost:8181

## 🔐 Default Credentials

- **Email**: admin@universal-auth.local
- **Password**: admin123

## 🏗️ Architecture

### Core Components

- **Frontend**: React application with atomic design components
- **Backend**: FastAPI with comprehensive authentication services
- **Database**: PostgreSQL with audit logging
- **Cache**: Redis for sessions and rate limiting
- **Policy Engine**: Open Policy Agent (OPA) for authorization
- **Reverse Proxy**: Nginx with rate limiting and SSL

### Key Features

#### Authentication Methods
- 🔑 OAuth (Google, GitHub, LinkedIn, Apple, Meta)
- 📱 Mobile OTP (Indian numbers)
- 📧 Email/Password
- 🔄 Progressive profiling

#### Authorization & Security
- 👥 Role-Based Access Control (RBAC)
- 🏢 Multi-tenant isolation
- 🔍 Dynamic scope management
- 🛡️ Security monitoring and alerts
- 📊 Comprehensive audit logging

#### API & Integration
- 🔐 JWT token management
- 🗝️ API key management (OpenAI, Gemini, etc.)
- 📋 Consistent API responses
- 🔄 Rate limiting and quotas

#### Admin & Configuration
- ⚙️ Project configuration management
- 🎨 Theme and UI customization
- 👨‍💼 Admin panels
- 📈 Analytics and reporting

## 🧪 Testing

### Run All Tests

```bash
# Run comprehensive test suite
python scripts/run_tests.py --types all

# Run specific test types
python scripts/run_tests.py --types unit property security

# Run BDD tests with browser automation
python scripts/run_tests.py --types bdd --headed
```

### Test Types

- **Unit Tests**: Individual component testing
- **Property Tests**: Hypothesis-based property validation
- **Integration Tests**: Service integration testing
- **BDD Tests**: Playwright browser automation
- **Security Tests**: Security-focused test scenarios
- **Performance Tests**: Load and performance testing

### Test Coverage

The system includes comprehensive test coverage:
- ✅ 25+ Property-based tests validating universal correctness
- ✅ BDD scenarios for authentication, admin, and integration flows
- ✅ Security monitoring and threat detection tests
- ✅ API response format consistency tests
- ✅ JWT token management and validation tests

## 🎭 Mock Data

Generate realistic test data for different scenarios:

```bash
# Generate comprehensive mock data
python scripts/generate_mock_data.py

# Custom data generation
python scripts/generate_mock_data.py \
  --users 100 \
  --projects 50 \
  --api-keys 75 \
  --audit-logs 1000 \
  --sessions 200
```

Generated data includes:
- 👥 Users with various roles and completion levels
- 🏢 Tenants with different configurations
- 📱 OAuth accounts and social logins
- 🔑 API keys with different scopes
- 📊 Audit logs with realistic events
- 🎯 Projects with theme configurations

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=postgresql://auth_user:auth_password@postgres:5432/universal_auth

# JWT Configuration
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRY_HOURS=24

# OAuth Providers
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Security
SECURITY_MONITORING_ENABLED=true
AUDIT_LOGGING_ENABLED=true
RATE_LIMITING_ENABLED=true
```

### OAuth Provider Setup

1. **Google OAuth**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create OAuth 2.0 credentials
   - Add redirect URI: `http://localhost:8000/auth/callback/google`

2. **GitHub OAuth**:
   - Go to GitHub Settings > Developer settings > OAuth Apps
   - Create new OAuth App
   - Add callback URL: `http://localhost:8000/auth/callback/github`

3. **Other Providers**: Similar setup for LinkedIn, Apple, Meta

## 🛠️ Development

### Project Structure

```
universal_auth/
├── backend/                 # FastAPI backend
│   ├── auth/               # Authentication routes
│   ├── services/           # Business logic services
│   ├── models/             # Database models
│   └── tests/              # Backend tests
├── frontend/               # React frontend
│   ├── src/components/     # UI components
│   └── public/             # Static assets
├── tests/bdd/              # BDD tests with Playwright
├── scripts/                # Deployment and utility scripts
├── config/                 # Configuration files
├── policy/                 # OPA policies
├── nginx/                  # Nginx configuration
└── database/               # Database initialization
```

### Local Development

```bash
# Backend development
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend development
cd frontend
npm install
npm start

# Run tests during development
python scripts/run_tests.py --types unit property
```

### Adding New Features

1. **Authentication Provider**:
   - Add provider configuration in `config/auth/providers.yaml`
   - Implement OAuth service in `backend/auth/oauth_service.py`
   - Add frontend integration in `frontend/src/components/`

2. **API Endpoint**:
   - Create route in `backend/auth/`
   - Add service logic in `backend/services/`
   - Use `ResponseFormatter` for consistent responses
   - Add property tests for validation

3. **Admin Feature**:
   - Add admin route in `backend/auth/admin_routes.py`
   - Implement service in `backend/services/admin_service.py`
   - Create frontend component in `frontend/src/components/organisms/`
   - Add RBAC permissions

## 🔒 Security Features

### Built-in Security

- 🛡️ **Brute Force Protection**: Automatic IP blocking
- 🔍 **Suspicious Activity Detection**: Impossible travel, unusual patterns
- 📊 **Real-time Monitoring**: Security dashboard and alerts
- 🔐 **Data Encryption**: Sensitive data masking in logs
- 🚫 **Rate Limiting**: API and authentication endpoint protection

### Security Monitoring

Access the security dashboard at `/admin/security` to view:
- 🚨 Real-time security alerts
- 📈 Threat level statistics
- 🌍 Geographic login patterns
- 📊 Failed authentication attempts
- 🔒 Blocked IP addresses

### Audit Logging

Comprehensive audit trail includes:
- 👤 All authentication events
- ⚙️ Configuration changes
- 👨‍💼 Admin actions
- 🔑 API key operations
- 🚫 Security violations

## 📊 Monitoring & Analytics

### Health Checks

Monitor system health:
```bash
# Check all services
curl http://localhost:80/health

# Check specific services
curl http://localhost:8000/api/health/database
curl http://localhost:8000/api/health/redis
curl http://localhost:8181/health
```

### Metrics & Logging

- **Application Logs**: Structured JSON logging
- **Audit Logs**: Searchable security events
- **Performance Metrics**: Response times and throughput
- **Security Metrics**: Threat detection and blocking

## 🚀 Production Deployment

### Docker Production Setup

1. **Update Environment**:
   ```bash
   cp .env.example .env.production
   # Configure production values
   ```

2. **SSL Certificates**:
   ```bash
   # Add your SSL certificates to nginx/ssl/
   cp your-cert.pem nginx/ssl/cert.pem
   cp your-key.pem nginx/ssl/key.pem
   ```

3. **Deploy**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

### Production Checklist

- [ ] Update all default passwords
- [ ] Configure OAuth provider credentials
- [ ] Set up SSL certificates
- [ ] Configure email SMTP settings
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategy
- [ ] Review security settings
- [ ] Set up log aggregation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Code Quality

- **Property Tests**: Add Hypothesis tests for new logic
- **BDD Tests**: Add Playwright tests for user flows
- **Security Tests**: Include security considerations
- **Documentation**: Update relevant documentation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Common Issues

1. **Services not starting**: Check Docker daemon and port availability
2. **OAuth not working**: Verify provider credentials and redirect URIs
3. **Tests failing**: Ensure all services are running and healthy
4. **Performance issues**: Check resource allocation and database connections

### Getting Help

- 📖 Check the documentation in `/docs`
- 🐛 Report issues on GitHub
- 💬 Join our community discussions
- 📧 Contact support team

## 🎯 Roadmap

### Upcoming Features

- 🔐 WebAuthn/FIDO2 support
- 📱 Mobile SDK
- 🌐 Additional OAuth providers
- 📊 Advanced analytics
- 🔄 Backup and disaster recovery
- 🎨 More UI themes and customization

---

**Universal Auth System** - Production-ready authentication for modern applications 🚀