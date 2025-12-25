"""
Comprehensive Audit Logging Service

This module provides comprehensive audit logging for all authentication events,
admin actions, and security-related activities with searchable and filterable interface.

**Implements: Requirements 7.1, 7.3**
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import hashlib
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Text, Integer, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB
import os

logger = logging.getLogger(__name__)

Base = declarative_base()

class EventSeverity(Enum):
    """Audit event severity levels"""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class EventCategory(Enum):
    """Audit event categories"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    USER_MANAGEMENT = "user_management"
    ADMIN_ACTION = "admin_action"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    DATA_ACCESS = "data_access"
    SYSTEM = "system"

@dataclass
class AuditContext:
    """Audit event context information"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

class AuditLog(Base):
    """Audit log database model"""
    __tablename__ = 'audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(50), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_category = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    
    # Context information
    user_id = Column(String(50), index=True)
    session_id = Column(String(100), index=True)
    ip_address = Column(String(45), index=True)  # IPv6 compatible
    user_agent = Column(Text)
    tenant_id = Column(String(50), index=True)
    request_id = Column(String(100), index=True)
    endpoint = Column(String(200))
    method = Column(String(10))
    
    # Event details
    message = Column(Text, nullable=False)
    success = Column(Boolean, nullable=False, index=True)
    event_data = Column(JSONB)  # PostgreSQL JSONB for efficient querying
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Additional metadata
    source = Column(String(50), default='universal-auth')
    version = Column(String(20), default='1.0')
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_tenant_timestamp', 'tenant_id', 'timestamp'),
        Index('idx_audit_category_severity', 'event_category', 'severity'),
        Index('idx_audit_success_timestamp', 'success', 'timestamp'),
    )

class AuditService:
    """Comprehensive audit logging service"""
    
    # Event type mappings to categories and severities
    EVENT_MAPPINGS = {
        # Authentication events
        'user_login_success': (EventCategory.AUTHENTICATION, EventSeverity.INFO),
        'user_login_failed': (EventCategory.AUTHENTICATION, EventSeverity.WARN),
        'user_logout': (EventCategory.AUTHENTICATION, EventSeverity.INFO),
        'user_registration': (EventCategory.AUTHENTICATION, EventSeverity.INFO),
        'password_change': (EventCategory.AUTHENTICATION, EventSeverity.WARN),
        'password_reset_request': (EventCategory.AUTHENTICATION, EventSeverity.WARN),
        'password_reset_complete': (EventCategory.AUTHENTICATION, EventSeverity.WARN),
        'oauth_login_success': (EventCategory.AUTHENTICATION, EventSeverity.INFO),
        'oauth_login_failed': (EventCategory.AUTHENTICATION, EventSeverity.WARN),
        'otp_sent': (EventCategory.AUTHENTICATION, EventSeverity.INFO),
        'otp_verified': (EventCategory.AUTHENTICATION, EventSeverity.INFO),
        'otp_failed': (EventCategory.AUTHENTICATION, EventSeverity.WARN),
        
        # Authorization events
        'access_granted': (EventCategory.AUTHORIZATION, EventSeverity.INFO),
        'access_denied': (EventCategory.AUTHORIZATION, EventSeverity.WARN),
        'permission_check': (EventCategory.AUTHORIZATION, EventSeverity.INFO),
        'role_assignment': (EventCategory.AUTHORIZATION, EventSeverity.WARN),
        'role_removal': (EventCategory.AUTHORIZATION, EventSeverity.WARN),
        'scope_granted': (EventCategory.AUTHORIZATION, EventSeverity.WARN),
        'scope_revoked': (EventCategory.AUTHORIZATION, EventSeverity.WARN),
        
        # User management events
        'user_created': (EventCategory.USER_MANAGEMENT, EventSeverity.WARN),
        'user_updated': (EventCategory.USER_MANAGEMENT, EventSeverity.WARN),
        'user_deleted': (EventCategory.USER_MANAGEMENT, EventSeverity.ERROR),
        'user_suspended': (EventCategory.USER_MANAGEMENT, EventSeverity.ERROR),
        'user_activated': (EventCategory.USER_MANAGEMENT, EventSeverity.WARN),
        'profile_updated': (EventCategory.USER_MANAGEMENT, EventSeverity.INFO),
        
        # Admin actions
        'admin_login': (EventCategory.ADMIN_ACTION, EventSeverity.WARN),
        'admin_access': (EventCategory.ADMIN_ACTION, EventSeverity.WARN),
        'admin_config_change': (EventCategory.ADMIN_ACTION, EventSeverity.ERROR),
        'admin_user_impersonation': (EventCategory.ADMIN_ACTION, EventSeverity.CRITICAL),
        'admin_bulk_operation': (EventCategory.ADMIN_ACTION, EventSeverity.ERROR),
        
        # Configuration events
        'config_updated': (EventCategory.CONFIGURATION, EventSeverity.WARN),
        'provider_configured': (EventCategory.CONFIGURATION, EventSeverity.WARN),
        'theme_updated': (EventCategory.CONFIGURATION, EventSeverity.INFO),
        'api_key_created': (EventCategory.CONFIGURATION, EventSeverity.WARN),
        'api_key_deleted': (EventCategory.CONFIGURATION, EventSeverity.WARN),
        'api_key_rotated': (EventCategory.CONFIGURATION, EventSeverity.WARN),
        
        # Security events
        'suspicious_activity': (EventCategory.SECURITY, EventSeverity.ERROR),
        'brute_force_attempt': (EventCategory.SECURITY, EventSeverity.ERROR),
        'unauthorized_access': (EventCategory.SECURITY, EventSeverity.ERROR),
        'token_revoked': (EventCategory.SECURITY, EventSeverity.WARN),
        'session_hijack_attempt': (EventCategory.SECURITY, EventSeverity.CRITICAL),
        'data_breach_attempt': (EventCategory.SECURITY, EventSeverity.CRITICAL),
        
        # Data access events
        'data_export': (EventCategory.DATA_ACCESS, EventSeverity.WARN),
        'data_import': (EventCategory.DATA_ACCESS, EventSeverity.WARN),
        'sensitive_data_access': (EventCategory.DATA_ACCESS, EventSeverity.WARN),
        'bulk_data_access': (EventCategory.DATA_ACCESS, EventSeverity.WARN),
        
        # System events
        'system_startup': (EventCategory.SYSTEM, EventSeverity.INFO),
        'system_shutdown': (EventCategory.SYSTEM, EventSeverity.WARN),
        'database_migration': (EventCategory.SYSTEM, EventSeverity.WARN),
        'backup_created': (EventCategory.SYSTEM, EventSeverity.INFO),
        'backup_restored': (EventCategory.SYSTEM, EventSeverity.ERROR),
    }
    
    # Sensitive fields that should be masked in audit logs
    SENSITIVE_FIELDS = {
        'password', 'api_key', 'secret', 'token', 'private_key', 'client_secret',
        'refresh_token', 'access_token', 'otp', 'pin', 'ssn', 'credit_card'
    }
    
    def __init__(self, database_url: str = None):
        """Initialize audit service"""
        if database_url is None:
            database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/universal_auth')
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
    
    def log_event(self, event_type: str, message: str, context: AuditContext,
                  success: bool = True, event_data: Dict[str, Any] = None) -> str:
        """
        Log an audit event
        
        Args:
            event_type: Type of event (must be in EVENT_MAPPINGS)
            message: Human-readable event message
            context: Audit context information
            success: Whether the event was successful
            event_data: Additional event-specific data
            
        Returns:
            Event ID of the logged event
        """
        try:
            # Generate unique event ID
            event_id = str(uuid.uuid4())
            
            # Get event category and severity
            category, severity = self.EVENT_MAPPINGS.get(
                event_type, 
                (EventCategory.SYSTEM, EventSeverity.INFO)
            )
            
            # Mask sensitive data
            masked_event_data = self._mask_sensitive_data(event_data or {})
            
            # Create audit log entry
            audit_entry = AuditLog(
                event_id=event_id,
                event_type=event_type,
                event_category=category.value,
                severity=severity.value,
                user_id=context.user_id,
                session_id=context.session_id,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                tenant_id=context.tenant_id,
                request_id=context.request_id,
                endpoint=context.endpoint,
                method=context.method,
                message=message,
                success=success,
                event_data=masked_event_data,
                timestamp=datetime.utcnow()
            )
            
            # Save to database
            with self.SessionLocal() as session:
                session.add(audit_entry)
                session.commit()
            
            logger.debug(f"Audit event logged: {event_id} - {event_type}")
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")
            # Don't raise exception to avoid breaking the main application
            return ""
    
    def get_audit_logs(self, filters: Dict[str, Any] = None, 
                      start_time: datetime = None, end_time: datetime = None,
                      page: int = 1, per_page: int = 50,
                      sort_by: str = 'timestamp', sort_order: str = 'desc') -> Dict[str, Any]:
        """
        Retrieve audit logs with filtering and pagination
        
        Args:
            filters: Filter criteria
            start_time: Start time for filtering
            end_time: End time for filtering
            page: Page number (1-based)
            per_page: Items per page
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Paginated audit logs with metadata
        """
        try:
            with self.SessionLocal() as session:
                query = session.query(AuditLog)
                
                # Apply filters
                if filters:
                    for key, value in filters.items():
                        if hasattr(AuditLog, key) and value is not None:
                            if isinstance(value, list):
                                query = query.filter(getattr(AuditLog, key).in_(value))
                            else:
                                query = query.filter(getattr(AuditLog, key) == value)
                
                # Apply time filtering
                if start_time:
                    query = query.filter(AuditLog.timestamp >= start_time)
                if end_time:
                    query = query.filter(AuditLog.timestamp <= end_time)
                
                # Apply sorting
                if hasattr(AuditLog, sort_by):
                    sort_column = getattr(AuditLog, sort_by)
                    if sort_order.lower() == 'desc':
                        query = query.order_by(sort_column.desc())
                    else:
                        query = query.order_by(sort_column.asc())
                
                # Get total count
                total = query.count()
                
                # Apply pagination
                offset = (page - 1) * per_page
                logs = query.offset(offset).limit(per_page).all()
                
                # Convert to dictionaries
                log_dicts = []
                for log in logs:
                    log_dict = {
                        'id': str(log.id),
                        'event_id': log.event_id,
                        'event_type': log.event_type,
                        'event_category': log.event_category,
                        'severity': log.severity,
                        'user_id': log.user_id,
                        'session_id': log.session_id,
                        'ip_address': log.ip_address,
                        'user_agent': log.user_agent,
                        'tenant_id': log.tenant_id,
                        'request_id': log.request_id,
                        'endpoint': log.endpoint,
                        'method': log.method,
                        'message': log.message,
                        'success': log.success,
                        'event_data': log.event_data,
                        'timestamp': log.timestamp.isoformat() + 'Z',
                        'created_at': log.created_at.isoformat() + 'Z'
                    }
                    log_dicts.append(log_dict)
                
                # Calculate pagination metadata
                pages = (total + per_page - 1) // per_page
                
                return {
                    'logs': log_dicts,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': pages,
                        'has_next': page < pages,
                        'has_prev': page > 1
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {str(e)}")
            return {
                'logs': [],
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'pages': 0,
                    'has_next': False,
                    'has_prev': False
                }
            }
    
    def get_audit_statistics(self, start_time: datetime = None, 
                           end_time: datetime = None,
                           tenant_id: str = None) -> Dict[str, Any]:
        """
        Get audit log statistics
        
        Args:
            start_time: Start time for statistics
            end_time: End time for statistics
            tenant_id: Filter by tenant ID
            
        Returns:
            Audit statistics
        """
        try:
            with self.SessionLocal() as session:
                query = session.query(AuditLog)
                
                # Apply filters
                if start_time:
                    query = query.filter(AuditLog.timestamp >= start_time)
                if end_time:
                    query = query.filter(AuditLog.timestamp <= end_time)
                if tenant_id:
                    query = query.filter(AuditLog.tenant_id == tenant_id)
                
                logs = query.all()
                
                if not logs:
                    return self._empty_statistics()
                
                # Calculate statistics
                total_events = len(logs)
                successful_events = sum(1 for log in logs if log.success)
                
                # Events by type
                events_by_type = {}
                for log in logs:
                    events_by_type[log.event_type] = events_by_type.get(log.event_type, 0) + 1
                
                # Events by category
                events_by_category = {}
                for log in logs:
                    events_by_category[log.event_category] = events_by_category.get(log.event_category, 0) + 1
                
                # Events by severity
                events_by_severity = {}
                for log in logs:
                    events_by_severity[log.severity] = events_by_severity.get(log.severity, 0) + 1
                
                # Top users by activity
                user_activity = {}
                for log in logs:
                    if log.user_id:
                        user_activity[log.user_id] = user_activity.get(log.user_id, 0) + 1
                
                top_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
                
                # Time range
                timestamps = [log.timestamp for log in logs]
                time_range = {
                    'start': min(timestamps).isoformat() + 'Z',
                    'end': max(timestamps).isoformat() + 'Z'
                }
                
                return {
                    'total_events': total_events,
                    'successful_events': successful_events,
                    'failed_events': total_events - successful_events,
                    'success_rate': successful_events / total_events if total_events > 0 else 0.0,
                    'events_by_type': events_by_type,
                    'events_by_category': events_by_category,
                    'events_by_severity': events_by_severity,
                    'top_users': dict(top_users),
                    'time_range': time_range
                }
                
        except Exception as e:
            logger.error(f"Failed to get audit statistics: {str(e)}")
            return self._empty_statistics()
    
    def search_audit_logs(self, search_term: str, search_fields: List[str] = None,
                         page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """
        Search audit logs by text
        
        Args:
            search_term: Text to search for
            search_fields: Fields to search in
            page: Page number
            per_page: Items per page
            
        Returns:
            Search results with pagination
        """
        if search_fields is None:
            search_fields = ['message', 'event_type', 'user_id', 'ip_address']
        
        try:
            with self.SessionLocal() as session:
                query = session.query(AuditLog)
                
                # Build search conditions
                search_conditions = []
                for field in search_fields:
                    if hasattr(AuditLog, field):
                        column = getattr(AuditLog, field)
                        search_conditions.append(column.ilike(f'%{search_term}%'))
                
                if search_conditions:
                    from sqlalchemy import or_
                    query = query.filter(or_(*search_conditions))
                
                # Order by relevance (timestamp desc for now)
                query = query.order_by(AuditLog.timestamp.desc())
                
                # Get total count
                total = query.count()
                
                # Apply pagination
                offset = (page - 1) * per_page
                logs = query.offset(offset).limit(per_page).all()
                
                # Convert to dictionaries (same as get_audit_logs)
                log_dicts = []
                for log in logs:
                    log_dict = {
                        'id': str(log.id),
                        'event_id': log.event_id,
                        'event_type': log.event_type,
                        'event_category': log.event_category,
                        'severity': log.severity,
                        'user_id': log.user_id,
                        'message': log.message,
                        'success': log.success,
                        'timestamp': log.timestamp.isoformat() + 'Z',
                        # Highlight matching terms (simplified)
                        'highlighted_message': self._highlight_search_term(log.message, search_term)
                    }
                    log_dicts.append(log_dict)
                
                pages = (total + per_page - 1) // per_page
                
                return {
                    'logs': log_dicts,
                    'search_term': search_term,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': pages,
                        'has_next': page < pages,
                        'has_prev': page > 1
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to search audit logs: {str(e)}")
            return {
                'logs': [],
                'search_term': search_term,
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'pages': 0,
                    'has_next': False,
                    'has_prev': False
                }
            }
    
    def export_audit_logs(self, filters: Dict[str, Any] = None,
                         start_time: datetime = None, end_time: datetime = None,
                         format: str = 'json') -> str:
        """
        Export audit logs to file
        
        Args:
            filters: Filter criteria
            start_time: Start time for export
            end_time: End time for export
            format: Export format ('json' or 'csv')
            
        Returns:
            File path of exported data
        """
        try:
            # Get all matching logs (no pagination for export)
            result = self.get_audit_logs(
                filters=filters,
                start_time=start_time,
                end_time=end_time,
                per_page=10000  # Large number to get all results
            )
            
            logs = result['logs']
            
            # Generate filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"audit_logs_export_{timestamp}.{format}"
            filepath = os.path.join('/tmp', filename)  # Use appropriate directory
            
            if format.lower() == 'json':
                with open(filepath, 'w') as f:
                    json.dump({
                        'export_timestamp': datetime.utcnow().isoformat() + 'Z',
                        'total_records': len(logs),
                        'filters': filters or {},
                        'logs': logs
                    }, f, indent=2)
            
            elif format.lower() == 'csv':
                import csv
                with open(filepath, 'w', newline='') as f:
                    if logs:
                        writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                        writer.writeheader()
                        for log in logs:
                            # Flatten event_data for CSV
                            row = log.copy()
                            if row.get('event_data'):
                                row['event_data'] = json.dumps(row['event_data'])
                            writer.writerow(row)
            
            logger.info(f"Exported {len(logs)} audit logs to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to export audit logs: {str(e)}")
            return ""
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in event data"""
        if not isinstance(data, dict):
            return data
        
        masked_data = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key contains sensitive information
            is_sensitive = any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS)
            
            if is_sensitive and isinstance(value, str) and len(value) > 0:
                # Mask sensitive values
                if len(value) <= 4:
                    masked_data[key] = '***'
                else:
                    masked_data[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
            elif isinstance(value, dict):
                # Recursively mask nested dictionaries
                masked_data[key] = self._mask_sensitive_data(value)
            else:
                masked_data[key] = value
        
        return masked_data
    
    def _highlight_search_term(self, text: str, search_term: str) -> str:
        """Highlight search term in text (simplified implementation)"""
        if not text or not search_term:
            return text
        
        # Simple case-insensitive highlighting
        import re
        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
        return pattern.sub(f'<mark>{search_term}</mark>', text)
    
    def _empty_statistics(self) -> Dict[str, Any]:
        """Return empty statistics structure"""
        return {
            'total_events': 0,
            'successful_events': 0,
            'failed_events': 0,
            'success_rate': 0.0,
            'events_by_type': {},
            'events_by_category': {},
            'events_by_severity': {},
            'top_users': {},
            'time_range': None
        }

# Factory function for creating audit service
def create_audit_service(database_url: str = None) -> AuditService:
    """
    Create audit service instance
    
    Args:
        database_url: Database connection URL
        
    Returns:
        Configured audit service instance
    """
    return AuditService(database_url)

# Convenience functions for common audit events
def log_authentication_event(audit_service: AuditService, event_type: str, 
                           user_id: str, success: bool, context: AuditContext,
                           additional_data: Dict[str, Any] = None) -> str:
    """Log authentication-related event"""
    message = f"Authentication event: {event_type} for user {user_id}"
    if not success:
        message += " (failed)"
    
    return audit_service.log_event(
        event_type=event_type,
        message=message,
        context=context,
        success=success,
        event_data=additional_data
    )

def log_admin_action(audit_service: AuditService, action: str, admin_user_id: str,
                    context: AuditContext, target_data: Dict[str, Any] = None) -> str:
    """Log admin action event"""
    message = f"Admin action: {action} by {admin_user_id}"
    
    return audit_service.log_event(
        event_type='admin_action',
        message=message,
        context=context,
        success=True,
        event_data={'action': action, 'target': target_data}
    )

def log_security_event(audit_service: AuditService, event_type: str, 
                      context: AuditContext, threat_data: Dict[str, Any] = None) -> str:
    """Log security-related event"""
    message = f"Security event: {event_type}"
    if context.ip_address:
        message += f" from {context.ip_address}"
    
    return audit_service.log_event(
        event_type=event_type,
        message=message,
        context=context,
        success=False,  # Security events are typically failures
        event_data=threat_data
    )