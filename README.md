
# Universal Auth System

A comprehensive authentication and authorization platform with multi-provider support, progressive profiling, and enterprise-grade security features.

## Features

- **Multi-Provider Authentication**: Google, GitHub, LinkedIn, Apple, Meta, Enterprise SSO
- **Mobile OTP**: Indian phone number validation and SMS OTP
- **Progressive Profiling**: Gradual user data collection over multiple sessions
- **Dynamic RBAC**: Role-based access control with scope versioning
- **OPA Integration**: Policy-as-code with sidecar pattern
- **Project Configuration**: Per-project workflows, themes, and settings
- **API Key Management**: Secure storage with role-based scoping
- **Admin Panels**: Complete configuration and management interface
- **Multi-Tenant**: Full isolation and customization per tenant

## Architecture

The system uses a microservices architecture with:
- **FastAPI Backend**: Authentication and authorization services
- **Next.js Frontend**: React-based UI with atomic design components
- **PostgreSQL**: Primary database for user data and configurations
- **Redis**: Session storage and caching
- **OPA Sidecars**: Policy evaluation for all services
- **Docker**: Containerized deployment

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Make (optional, for convenience commands)

### Setup

1. **Clone and navigate to the project**:
   ```bash
   cd universal_auth
   ```

2. **Copy environment configuration**:
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` file with your configuration**:
   - Database credentials
   - OAuth provider keys
   - JWT secrets
   - SMS provider settings

4. **Start the development environment**:
   ```bash
   make setup
   # OR manually:
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

5. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - OPA Server: http://localhost:8181

### Development Commands

```bash
make help          # Show all available commands
make up            # Start services
make down          # Stop services
make logs          # View logs
make test          # Run tests
make clean         # Clean up containers
```

## Project Structure

```
universal_auth/
├── backend/           # FastAPI backend services
│   ├── auth/         # Authentication modules
│   ├── db/           # Database models and migrations
│   └── main.py       # Application entry point
├── frontend/         # Next.js frontend application
│   ├── atoms/        # Basic UI components
│   ├── molecules/    # Composite UI components
│   ├── organisms/    # Complex UI components
│   └── templates/    # Page layouts
├── config/           # Configuration files
│   ├── auth/         # Authentication configurations
│   └── app/          # Application settings
├── policy/           # OPA policy files
└── docker-compose.yml # Container orchestration
```

## Configuration

### OAuth Providers

Configure OAuth providers in `config/auth/providers.yaml`:

```yaml
providers:
  google:
    type: oauth2
    client_id_env: GOOGLE_CLIENT_ID
    client_secret_env: GOOGLE_CLIENT_SECRET
    # ... other settings
```

### Workflows

Define authentication workflows in `config/auth/workflows.yaml`:

```yaml
workflows:
  EMAIL_SOCIAL_GOOGLE:
    ui_style: WHITE_SOCIAL
    enabled_auth_methods: [google, email_otp]
    defaults:
      primary_identity: email
      default_role: user
```

### RBAC

Configure roles and capabilities in `config/auth/rbac.yaml`:

```yaml
roles:
  user:
    capabilities: [app:login, app:profile.read, app:profile.write]
  admin:
    capabilities: ["*"]
```

## API Documentation

The API documentation is automatically generated and available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

The project includes comprehensive testing:

```bash
# Run all tests
make test

# Backend tests only
docker-compose exec auth-backend pytest

# Frontend tests only
docker-compose exec frontend npm test

# Property-based tests
docker-compose exec auth-backend pytest -m property
```

## Deployment

### Production Setup

1. **Update environment variables** for production
2. **Build production images**:
   ```bash
   docker-compose -f docker-compose.yml build
   ```
3. **Deploy with production compose file**:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

### Environment Variables

Key environment variables for production:
- `JWT_SECRET_KEY`: Strong secret for JWT tokens
- `DATABASE_URL`: Production database connection
- `REDIS_URL`: Production Redis connection
- OAuth provider credentials
- SMS provider settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For support and questions:
- Check the documentation
- Review existing issues
- Create a new issue with detailed information
