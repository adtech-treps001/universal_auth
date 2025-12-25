#!/usr/bin/env python3
"""
Mock Data Generator for Universal Auth System

This script generates comprehensive mock data for testing different scenarios
including users, tenants, projects, API keys, and audit logs.
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
from faker import Faker
import argparse
import os
from pathlib import Path

fake = Faker()

class MockDataGenerator:
    """Generate mock data for testing scenarios"""
    
    def __init__(self, seed: int = None):
        if seed:
            Faker.seed(seed)
            random.seed(seed)
        
        self.tenants = []
        self.users = []
        self.roles = []
        self.projects = []
        self.api_keys = []
        self.oauth_accounts = []
        self.audit_logs = []
        self.sessions = []
        
        # Predefined data for consistency
        self.oauth_providers = ['google', 'github', 'linkedin', 'apple', 'meta']
        self.api_providers = ['openai', 'gemini', 'anthropic', 'custom']
        self.event_types = [
            'user_login_success', 'user_login_failed', 'user_logout', 'user_registration',
            'password_change', 'oauth_login_success', 'oauth_login_failed', 'otp_sent',
            'otp_verified', 'otp_failed', 'admin_access', 'config_updated', 'api_key_created',
            'unauthorized_access', 'suspicious_activity', 'data_export'
        ]
        
    def generate_tenants(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate mock tenants"""
        print(f"Generating {count} mock tenants...")
        
        # Always include default tenant
        self.tenants = [{
            'id': str(uuid.uuid4()),
            'name': 'Default Tenant',
            'domain': 'localhost',
            'settings': {
                'theme': {
                    'primary_color': '#007bff',
                    'secondary_color': '#6c757d',
                    'font_family': 'Arial'
                },
                'features': {
                    'oauth_enabled': True,
                    'otp_enabled': True,
                    'progressive_profiling': True
                }
            },
            'is_active': True,
            'created_at': fake.date_time_between(start_date='-1y', end_date='now').isoformat(),
            'updated_at': fake.date_time_between(start_date='-1m', end_date='now').isoformat()
        }]
        
        # Generate additional tenants
        for _ in range(count - 1):
            tenant = {
                'id': str(uuid.uuid4()),
                'name': fake.company(),
                'domain': fake.domain_name(),
                'settings': {
                    'theme': {
                        'primary_color': fake.hex_color(),
                        'secondary_color': fake.hex_color(),
                        'font_family': random.choice(['Arial', 'Helvetica', 'Roboto', 'Open Sans'])
                    },
                    'features': {
                        'oauth_enabled': random.choice([True, False]),
                        'otp_enabled': random.choice([True, False]),
                        'progressive_profiling': random.choice([True, False])
                    }
                },
                'is_active': random.choice([True, True, True, False]),  # 75% active
                'created_at': fake.date_time_between(start_date='-2y', end_date='-1m').isoformat(),
                'updated_at': fake.date_time_between(start_date='-1m', end_date='now').isoformat()
            }
            self.tenants.append(tenant)
        
        return self.tenants
    
    def generate_roles(self) -> List[Dict[str, Any]]:
        """Generate system and custom roles"""
        print("Generating mock roles...")
        
        # System roles for each tenant
        system_roles = [
            {
                'name': 'super_admin',
                'description': 'Super Administrator with full system access',
                'capabilities': [
                    'admin.projects.read', 'admin.projects.write', 'admin.projects.delete',
                    'admin.users.read', 'admin.users.write', 'admin.users.delete',
                    'admin.roles.read', 'admin.roles.write', 'admin.roles.delete',
                    'admin.config.read', 'admin.config.write', 'admin.config.delete',
                    'admin.audit.read', 'admin.integrations.read', 'admin.integrations.write'
                ],
                'is_system_role': True
            },
            {
                'name': 'admin',
                'description': 'Administrator with project management access',
                'capabilities': [
                    'admin.projects.read', 'admin.projects.write',
                    'admin.users.read', 'admin.users.write',
                    'admin.config.read', 'admin.config.write'
                ],
                'is_system_role': True
            },
            {
                'name': 'user',
                'description': 'Standard user with basic access',
                'capabilities': ['profile.read', 'profile.write'],
                'is_system_role': True
            },
            {
                'name': 'viewer',
                'description': 'Read-only access user',
                'capabilities': ['profile.read'],
                'is_system_role': True
            }
        ]
        
        self.roles = []
        
        for tenant in self.tenants:
            # Add system roles for each tenant
            for role_template in system_roles:
                role = {
                    'id': str(uuid.uuid4()),
                    'tenant_id': tenant['id'],
                    'created_at': fake.date_time_between(start_date='-1y', end_date='now').isoformat(),
                    'updated_at': fake.date_time_between(start_date='-1m', end_date='now').isoformat(),
                    **role_template
                }
                self.roles.append(role)
            
            # Add some custom roles
            custom_roles = [
                {
                    'name': 'moderator',
                    'description': 'Content moderator with limited admin access',
                    'capabilities': ['admin.users.read', 'admin.content.moderate'],
                    'is_system_role': False
                },
                {
                    'name': 'developer',
                    'description': 'Developer with API access',
                    'capabilities': ['api.read', 'api.write', 'profile.read', 'profile.write'],
                    'is_system_role': False
                }
            ]
            
            for role_template in custom_roles:
                if random.choice([True, False]):  # 50% chance to add custom roles
                    role = {
                        'id': str(uuid.uuid4()),
                        'tenant_id': tenant['id'],
                        'created_at': fake.date_time_between(start_date='-6m', end_date='now').isoformat(),
                        'updated_at': fake.date_time_between(start_date='-1m', end_date='now').isoformat(),
                        **role_template
                    }
                    self.roles.append(role)
        
        return self.roles
    
    def generate_users(self, count: int = 50) -> List[Dict[str, Any]]:
        """Generate mock users"""
        print(f"Generating {count} mock users...")
        
        # Always include default admin user
        default_tenant = next(t for t in self.tenants if t['domain'] == 'localhost')
        
        self.users = [{
            'id': str(uuid.uuid4()),
            'email': 'admin@universal-auth.local',
            'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PmvlDO',  # admin123
            'first_name': 'System',
            'last_name': 'Administrator',
            'phone': '+1234567890',
            'is_active': True,
            'is_verified': True,
            'profile_completion_percentage': 100,
            'session_count': random.randint(50, 200),
            'last_login': fake.date_time_between(start_date='-1d', end_date='now').isoformat(),
            'created_at': fake.date_time_between(start_date='-1y', end_date='-6m').isoformat(),
            'updated_at': fake.date_time_between(start_date='-1d', end_date='now').isoformat(),
            'tenant_id': default_tenant['id'],
            'roles': ['super_admin']
        }]
        
        # Generate regular users
        for _ in range(count - 1):
            tenant = random.choice(self.tenants)
            session_count = random.randint(0, 100)
            
            # Profile completion based on session count (progressive profiling)
            if session_count == 0:
                completion = 30  # New users
            elif session_count < 5:
                completion = random.randint(30, 60)
            elif session_count < 20:
                completion = random.randint(60, 85)
            else:
                completion = random.randint(85, 100)
            
            user = {
                'id': str(uuid.uuid4()),
                'email': fake.email(),
                'password_hash': fake.sha256(),
                'first_name': fake.first_name(),
                'last_name': fake.last_name(),
                'phone': fake.phone_number() if random.choice([True, False]) else None,
                'is_active': random.choice([True, True, True, False]),  # 75% active
                'is_verified': random.choice([True, True, False]),  # 67% verified
                'profile_completion_percentage': completion,
                'session_count': session_count,
                'last_login': fake.date_time_between(start_date='-30d', end_date='now').isoformat() if session_count > 0 else None,
                'created_at': fake.date_time_between(start_date='-2y', end_date='now').isoformat(),
                'updated_at': fake.date_time_between(start_date='-30d', end_date='now').isoformat(),
                'tenant_id': tenant['id'],
                'roles': [random.choice(['user', 'viewer', 'admin']) if random.random() < 0.1 else 'user']
            }
            self.users.append(user)
        
        return self.users
    
    def generate_oauth_accounts(self) -> List[Dict[str, Any]]:
        """Generate OAuth accounts for users"""
        print("Generating OAuth accounts...")
        
        self.oauth_accounts = []
        
        for user in self.users:
            # 60% chance user has OAuth accounts
            if random.random() < 0.6:
                num_accounts = random.choices([1, 2, 3], weights=[70, 25, 5])[0]
                
                providers = random.sample(self.oauth_providers, min(num_accounts, len(self.oauth_providers)))
                
                for provider in providers:
                    account = {
                        'id': str(uuid.uuid4()),
                        'user_id': user['id'],
                        'provider': provider,
                        'provider_user_id': str(random.randint(100000, 999999999)),
                        'provider_email': user['email'] if random.choice([True, False]) else fake.email(),
                        'provider_data': {
                            'name': f"{user['first_name']} {user['last_name']}",
                            'avatar_url': fake.image_url(),
                            'profile_url': fake.url()
                        },
                        'access_token': fake.sha256()[:64],
                        'refresh_token': fake.sha256()[:64] if random.choice([True, False]) else None,
                        'expires_at': fake.date_time_between(start_date='now', end_date='+30d').isoformat(),
                        'created_at': fake.date_time_between(start_date='-1y', end_date='now').isoformat(),
                        'updated_at': fake.date_time_between(start_date='-30d', end_date='now').isoformat()
                    }
                    self.oauth_accounts.append(account)
        
        return self.oauth_accounts
    
    def generate_projects(self, count: int = 20) -> List[Dict[str, Any]]:
        """Generate mock projects"""
        print(f"Generating {count} mock projects...")
        
        self.projects = []
        
        for _ in range(count):
            tenant = random.choice(self.tenants)
            # Find users in this tenant
            tenant_users = [u for u in self.users if u['tenant_id'] == tenant['id']]
            owner = random.choice(tenant_users) if tenant_users else None
            
            project = {
                'id': str(uuid.uuid4()),
                'name': fake.catch_phrase(),
                'description': fake.text(max_nb_chars=200),
                'tenant_id': tenant['id'],
                'owner_id': owner['id'] if owner else None,
                'configuration': {
                    'oauth_providers': random.sample(self.oauth_providers, random.randint(1, 3)),
                    'otp_enabled': random.choice([True, False]),
                    'progressive_profiling': random.choice([True, False]),
                    'session_timeout': random.choice([3600, 7200, 14400, 28800]),  # 1-8 hours
                    'max_login_attempts': random.choice([3, 5, 10])
                },
                'theme_config': {
                    'primary_color': fake.hex_color(),
                    'secondary_color': fake.hex_color(),
                    'font_family': random.choice(['Arial', 'Helvetica', 'Roboto', 'Open Sans']),
                    'border_radius': random.randint(0, 20),
                    'button_style': random.choice(['solid', 'outline', 'ghost'])
                },
                'workflow_type': random.choice(['social_auth', 'email_password', 'otp_only', 'hybrid']),
                'is_active': random.choice([True, True, True, False]),  # 75% active
                'created_at': fake.date_time_between(start_date='-1y', end_date='now').isoformat(),
                'updated_at': fake.date_time_between(start_date='-30d', end_date='now').isoformat()
            }
            self.projects.append(project)
        
        return self.projects
    
    def generate_api_keys(self, count: int = 30) -> List[Dict[str, Any]]:
        """Generate mock API keys"""
        print(f"Generating {count} mock API keys...")
        
        self.api_keys = []
        
        for _ in range(count):
            user = random.choice(self.users)
            provider = random.choice(self.api_providers)
            
            # Generate realistic scopes based on provider
            if provider == 'openai':
                scopes = random.sample(['chat.completions', 'completions', 'embeddings', 'images', 'audio'], random.randint(1, 3))
            elif provider == 'gemini':
                scopes = random.sample(['generate', 'embed', 'chat'], random.randint(1, 2))
            else:
                scopes = random.sample(['read', 'write', 'admin'], random.randint(1, 2))
            
            api_key = {
                'id': str(uuid.uuid4()),
                'name': f"{provider.title()} API Key - {fake.word().title()}",
                'key_hash': fake.sha256(),
                'key_prefix': f"{provider[:2]}-{fake.random_letters(length=4)}",
                'provider': provider,
                'scopes': scopes,
                'allowed_roles': random.sample(['user', 'admin', 'developer'], random.randint(1, 2)),
                'user_id': user['id'],
                'tenant_id': user['tenant_id'],
                'is_active': random.choice([True, True, True, False]),  # 75% active
                'last_used': fake.date_time_between(start_date='-30d', end_date='now').isoformat() if random.choice([True, False]) else None,
                'expires_at': fake.date_time_between(start_date='+30d', end_date='+1y').isoformat() if random.choice([True, False]) else None,
                'created_at': fake.date_time_between(start_date='-6m', end_date='now').isoformat(),
                'updated_at': fake.date_time_between(start_date='-30d', end_date='now').isoformat()
            }
            self.api_keys.append(api_key)
        
        return self.api_keys
    
    def generate_audit_logs(self, count: int = 500) -> List[Dict[str, Any]]:
        """Generate mock audit logs"""
        print(f"Generating {count} mock audit logs...")
        
        self.audit_logs = []
        
        for _ in range(count):
            user = random.choice(self.users) if random.choice([True, False]) else None
            event_type = random.choice(self.event_types)
            
            # Determine success based on event type
            if 'failed' in event_type or 'unauthorized' in event_type or 'suspicious' in event_type:
                success = False
            else:
                success = random.choice([True, True, True, False])  # 75% success rate
            
            # Generate event-specific data
            event_data = {}
            if 'login' in event_type:
                event_data = {
                    'login_method': random.choice(['password', 'oauth', 'otp']),
                    'user_agent': fake.user_agent(),
                    'remember_me': random.choice([True, False])
                }
            elif 'oauth' in event_type:
                event_data = {
                    'provider': random.choice(self.oauth_providers),
                    'redirect_uri': fake.url()
                }
            elif 'otp' in event_type:
                event_data = {
                    'phone_number': fake.phone_number(),
                    'delivery_method': 'sms'
                }
            elif 'api_key' in event_type:
                event_data = {
                    'provider': random.choice(self.api_providers),
                    'scopes': random.sample(['read', 'write', 'admin'], random.randint(1, 2))
                }
            elif 'data_export' in event_type:
                event_data = {
                    'data_type': random.choice(['user_data', 'audit_logs', 'system_config']),
                    'data_volume': random.randint(1000, 10000000),  # bytes
                    'export_format': random.choice(['json', 'csv', 'xml'])
                }
            
            audit_log = {
                'id': str(uuid.uuid4()),
                'event_id': f"evt_{int(fake.unix_time())}_{random.randint(1000, 9999)}",
                'event_type': event_type,
                'event_category': self._get_event_category(event_type),
                'severity': self._get_event_severity(event_type, success),
                'user_id': user['id'] if user else None,
                'session_id': str(uuid.uuid4()) if user else None,
                'ip_address': fake.ipv4(),
                'user_agent': fake.user_agent(),
                'tenant_id': user['tenant_id'] if user else random.choice(self.tenants)['id'],
                'request_id': str(uuid.uuid4()),
                'endpoint': f"/api/{random.choice(['auth', 'users', 'admin', 'projects'])}/{random.choice(['login', 'create', 'update', 'delete'])}",
                'method': random.choice(['GET', 'POST', 'PUT', 'DELETE']),
                'message': self._generate_audit_message(event_type, success, user),
                'success': success,
                'event_data': event_data,
                'timestamp': fake.date_time_between(start_date='-30d', end_date='now').isoformat(),
                'created_at': fake.date_time_between(start_date='-30d', end_date='now').isoformat(),
                'source': 'universal-auth',
                'version': '1.0'
            }
            self.audit_logs.append(audit_log)
        
        # Sort by timestamp
        self.audit_logs.sort(key=lambda x: x['timestamp'])
        
        return self.audit_logs
    
    def generate_sessions(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate mock user sessions"""
        print(f"Generating {count} mock sessions...")
        
        self.sessions = []
        
        for _ in range(count):
            user = random.choice([u for u in self.users if u['is_active']])
            
            session = {
                'id': str(uuid.uuid4()),
                'user_id': user['id'],
                'session_token': fake.sha256()[:64],
                'ip_address': fake.ipv4(),
                'user_agent': fake.user_agent(),
                'tenant_id': user['tenant_id'],
                'expires_at': fake.date_time_between(start_date='now', end_date='+7d').isoformat(),
                'created_at': fake.date_time_between(start_date='-7d', end_date='now').isoformat(),
                'last_activity': fake.date_time_between(start_date='-1d', end_date='now').isoformat()
            }
            self.sessions.append(session)
        
        return self.sessions
    
    def _get_event_category(self, event_type: str) -> str:
        """Get event category based on event type"""
        if 'login' in event_type or 'logout' in event_type or 'registration' in event_type or 'password' in event_type or 'oauth' in event_type or 'otp' in event_type:
            return 'authentication'
        elif 'admin' in event_type:
            return 'admin_action'
        elif 'config' in event_type or 'api_key' in event_type:
            return 'configuration'
        elif 'unauthorized' in event_type or 'suspicious' in event_type:
            return 'security'
        elif 'data_export' in event_type:
            return 'data_access'
        else:
            return 'system'
    
    def _get_event_severity(self, event_type: str, success: bool) -> str:
        """Get event severity based on type and success"""
        if 'suspicious' in event_type or 'unauthorized' in event_type:
            return 'ERROR'
        elif 'admin' in event_type or 'config' in event_type or 'api_key' in event_type:
            return 'WARN'
        elif not success and ('login' in event_type or 'otp' in event_type):
            return 'WARN'
        else:
            return 'INFO'
    
    def _generate_audit_message(self, event_type: str, success: bool, user: Dict[str, Any] = None) -> str:
        """Generate human-readable audit message"""
        user_info = f"user {user['email']}" if user else "anonymous user"
        
        messages = {
            'user_login_success': f"Successful login by {user_info}",
            'user_login_failed': f"Failed login attempt by {user_info}",
            'user_logout': f"User logout by {user_info}",
            'user_registration': f"New user registration: {user_info}",
            'password_change': f"Password changed by {user_info}",
            'oauth_login_success': f"Successful OAuth login by {user_info}",
            'oauth_login_failed': f"Failed OAuth login attempt by {user_info}",
            'otp_sent': f"OTP sent to {user_info}",
            'otp_verified': f"OTP verified for {user_info}",
            'otp_failed': f"OTP verification failed for {user_info}",
            'admin_access': f"Admin panel accessed by {user_info}",
            'config_updated': f"System configuration updated by {user_info}",
            'api_key_created': f"API key created by {user_info}",
            'unauthorized_access': f"Unauthorized access attempt by {user_info}",
            'suspicious_activity': f"Suspicious activity detected for {user_info}",
            'data_export': f"Data export performed by {user_info}"
        }
        
        base_message = messages.get(event_type, f"Event {event_type} by {user_info}")
        
        if not success:
            base_message += " (failed)"
        
        return base_message
    
    def generate_all_data(self, users_count: int = 50, projects_count: int = 20, 
                         api_keys_count: int = 30, audit_logs_count: int = 500,
                         sessions_count: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """Generate all mock data"""
        print("🎭 Generating comprehensive mock data for Universal Auth System...")
        print("=" * 60)
        
        # Generate data in dependency order
        self.generate_tenants(5)
        self.generate_roles()
        self.generate_users(users_count)
        self.generate_oauth_accounts()
        self.generate_projects(projects_count)
        self.generate_api_keys(api_keys_count)
        self.generate_audit_logs(audit_logs_count)
        self.generate_sessions(sessions_count)
        
        return {
            'tenants': self.tenants,
            'roles': self.roles,
            'users': self.users,
            'oauth_accounts': self.oauth_accounts,
            'projects': self.projects,
            'api_keys': self.api_keys,
            'audit_logs': self.audit_logs,
            'sessions': self.sessions
        }
    
    def save_to_files(self, output_dir: str = "mock_data"):
        """Save generated data to JSON files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        data_sets = {
            'tenants': self.tenants,
            'roles': self.roles,
            'users': self.users,
            'oauth_accounts': self.oauth_accounts,
            'projects': self.projects,
            'api_keys': self.api_keys,
            'audit_logs': self.audit_logs,
            'sessions': self.sessions
        }
        
        print(f"\n💾 Saving mock data to {output_path}/")
        
        for name, data in data_sets.items():
            if data:
                file_path = output_path / f"{name}.json"
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                print(f"  ✅ {name}: {len(data)} records -> {file_path}")
        
        # Save summary
        summary = {
            'generated_at': datetime.now().isoformat(),
            'summary': {name: len(data) for name, data in data_sets.items()},
            'total_records': sum(len(data) for data in data_sets.values())
        }
        
        summary_path = output_path / "summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"  📊 Summary: {summary['total_records']} total records -> {summary_path}")
        
        return output_path

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Universal Auth System Mock Data Generator")
    
    parser.add_argument("--users", type=int, default=50, help="Number of users to generate")
    parser.add_argument("--projects", type=int, default=20, help="Number of projects to generate")
    parser.add_argument("--api-keys", type=int, default=30, help="Number of API keys to generate")
    parser.add_argument("--audit-logs", type=int, default=500, help="Number of audit logs to generate")
    parser.add_argument("--sessions", type=int, default=100, help="Number of sessions to generate")
    parser.add_argument("--output-dir", default="mock_data", help="Output directory for generated data")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible data")
    
    args = parser.parse_args()
    
    # Create generator
    generator = MockDataGenerator(seed=args.seed)
    
    try:
        # Generate all data
        all_data = generator.generate_all_data(
            users_count=args.users,
            projects_count=args.projects,
            api_keys_count=args.api_keys,
            audit_logs_count=args.audit_logs,
            sessions_count=args.sessions
        )
        
        # Save to files
        output_path = generator.save_to_files(args.output_dir)
        
        print("\n" + "=" * 60)
        print("✨ Mock data generation completed successfully!")
        print(f"📁 Data saved to: {output_path.absolute()}")
        print("\n🚀 You can now use this data for:")
        print("  • Testing different user scenarios")
        print("  • Load testing with realistic data")
        print("  • Demonstrating system capabilities")
        print("  • BDD test scenarios")
        
    except Exception as e:
        print(f"\n💥 Error generating mock data: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())