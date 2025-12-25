"""
Security Monitoring and Alerts Service

This module provides comprehensive security monitoring, suspicious activity detection,
and automated alert system for the Universal Auth System.

**Implements: Requirements 7.2, 7.4, 7.5**
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import requests
import threading
import time
from collections import defaultdict, deque
import hashlib
import os

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """Security threat levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertChannel(Enum):
    """Alert delivery channels"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"
    SLACK = "slack"
    LOG = "log"

@dataclass
class SecurityAlert:
    """Security alert data structure"""
    alert_id: str
    threat_level: ThreatLevel
    alert_type: str
    title: str
    description: str
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['threat_level'] = self.threat_level.value
        data['timestamp'] = self.timestamp.isoformat() + 'Z'
        return data

@dataclass
class MonitoringRule:
    """Security monitoring rule configuration"""
    rule_id: str
    name: str
    description: str
    event_types: List[str]
    conditions: Dict[str, Any]
    threshold: int
    time_window_minutes: int
    threat_level: ThreatLevel
    enabled: bool = True
    
    def matches_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Check if event matches this rule"""
        if not self.enabled:
            return False
        
        if event_type not in self.event_types:
            return False
        
        # Check conditions
        for key, expected_value in self.conditions.items():
            if key not in event_data:
                return False
            
            actual_value = event_data[key]
            
            # Handle different condition types
            if isinstance(expected_value, dict):
                if 'equals' in expected_value:
                    if actual_value != expected_value['equals']:
                        return False
                elif 'contains' in expected_value:
                    if expected_value['contains'] not in str(actual_value):
                        return False
                elif 'regex' in expected_value:
                    import re
                    if not re.search(expected_value['regex'], str(actual_value)):
                        return False
            else:
                if actual_value != expected_value:
                    return False
        
        return True

class SecurityMonitoringService:
    """Comprehensive security monitoring service"""
    
    def __init__(self, redis_client: redis.Redis = None, config: Dict[str, Any] = None):
        """Initialize security monitoring service"""
        self.redis_client = redis_client or redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        self.config = config or self._load_default_config()
        
        # In-memory tracking for performance
        self.event_counters = defaultdict(lambda: defaultdict(int))
        self.ip_tracking = defaultdict(lambda: deque(maxlen=1000))
        self.user_tracking = defaultdict(lambda: deque(maxlen=1000))
        
        # Alert handlers
        self.alert_handlers: Dict[AlertChannel, Callable] = {
            AlertChannel.EMAIL: self._send_email_alert,
            AlertChannel.WEBHOOK: self._send_webhook_alert,
            AlertChannel.SLACK: self._send_slack_alert,
            AlertChannel.LOG: self._log_alert
        }
        
        # Load monitoring rules
        self.monitoring_rules = self._load_monitoring_rules()
        
        # Start background monitoring thread
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._background_monitoring, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Security monitoring service initialized")
    
    def process_security_event(self, event_type: str, event_data: Dict[str, Any],
                             context: Dict[str, Any] = None) -> List[SecurityAlert]:
        """
        Process security event and generate alerts if needed
        
        Args:
            event_type: Type of security event
            event_data: Event data
            context: Additional context (IP, user, etc.)
            
        Returns:
            List of generated security alerts
        """
        alerts = []
        
        try:
            # Normalize context
            if context is None:
                context = {}
            
            ip_address = context.get('ip_address')
            user_id = context.get('user_id')
            tenant_id = context.get('tenant_id')
            
            # Track event for pattern analysis
            self._track_event(event_type, event_data, context)
            
            # Check against monitoring rules
            for rule in self.monitoring_rules:
                if rule.matches_event(event_type, event_data):
                    alert = self._check_rule_threshold(rule, event_type, context)
                    if alert:
                        alerts.append(alert)
            
            # Built-in security checks
            built_in_alerts = self._run_built_in_checks(event_type, event_data, context)
            alerts.extend(built_in_alerts)
            
            # Send alerts
            for alert in alerts:
                self._send_alert(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error processing security event: {str(e)}")
            return []
    
    def detect_brute_force_attack(self, ip_address: str, user_id: str = None) -> Optional[SecurityAlert]:
        """
        Detect brute force attacks
        
        Args:
            ip_address: Source IP address
            user_id: Target user ID (optional)
            
        Returns:
            Security alert if brute force detected
        """
        try:
            # Check failed login attempts from IP
            ip_key = f"failed_logins:ip:{ip_address}"
            ip_failures = self.redis_client.get(ip_key)
            ip_count = int(ip_failures) if ip_failures else 0
            
            # Check failed login attempts for user
            user_count = 0
            if user_id:
                user_key = f"failed_logins:user:{user_id}"
                user_failures = self.redis_client.get(user_key)
                user_count = int(user_failures) if user_failures else 0
            
            # Thresholds
            ip_threshold = self.config.get('brute_force_ip_threshold', 10)
            user_threshold = self.config.get('brute_force_user_threshold', 5)
            
            if ip_count >= ip_threshold or user_count >= user_threshold:
                alert = SecurityAlert(
                    alert_id=self._generate_alert_id(),
                    threat_level=ThreatLevel.HIGH,
                    alert_type='brute_force_attack',
                    title='Brute Force Attack Detected',
                    description=f'Multiple failed login attempts detected from IP {ip_address}',
                    source_ip=ip_address,
                    user_id=user_id,
                    metadata={
                        'ip_failures': ip_count,
                        'user_failures': user_count,
                        'detection_method': 'threshold_based'
                    }
                )
                
                # Block IP temporarily
                self._block_ip_temporarily(ip_address)
                
                return alert
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting brute force attack: {str(e)}")
            return None
    
    def detect_suspicious_login_patterns(self, user_id: str, ip_address: str,
                                       user_agent: str = None) -> List[SecurityAlert]:
        """
        Detect suspicious login patterns
        
        Args:
            user_id: User ID
            ip_address: Source IP address
            user_agent: User agent string
            
        Returns:
            List of security alerts for suspicious patterns
        """
        alerts = []
        
        try:
            # Check for impossible travel (login from different geographic locations)
            travel_alert = self._check_impossible_travel(user_id, ip_address)
            if travel_alert:
                alerts.append(travel_alert)
            
            # Check for unusual login times
            time_alert = self._check_unusual_login_time(user_id)
            if time_alert:
                alerts.append(time_alert)
            
            # Check for new device/browser
            device_alert = self._check_new_device(user_id, user_agent)
            if device_alert:
                alerts.append(device_alert)
            
            # Check for rapid successive logins
            rapid_alert = self._check_rapid_logins(user_id)
            if rapid_alert:
                alerts.append(rapid_alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error detecting suspicious login patterns: {str(e)}")
            return []
    
    def detect_data_exfiltration(self, user_id: str, data_volume: int,
                               data_type: str, context: Dict[str, Any] = None) -> Optional[SecurityAlert]:
        """
        Detect potential data exfiltration
        
        Args:
            user_id: User performing data access
            data_volume: Volume of data accessed
            data_type: Type of data accessed
            context: Additional context
            
        Returns:
            Security alert if exfiltration detected
        """
        try:
            # Track data access patterns
            access_key = f"data_access:{user_id}:{data_type}"
            
            # Get recent access history
            access_history = self.redis_client.lrange(access_key, 0, -1)
            
            # Calculate recent access volume
            recent_volume = sum(int(volume) for volume in access_history[-10:])  # Last 10 accesses
            
            # Add current access
            self.redis_client.lpush(access_key, data_volume)
            self.redis_client.expire(access_key, 3600)  # 1 hour TTL
            
            # Check thresholds
            volume_threshold = self.config.get('data_exfiltration_threshold', {}).get(data_type, 1000000)  # 1MB default
            
            if recent_volume + data_volume > volume_threshold:
                alert = SecurityAlert(
                    alert_id=self._generate_alert_id(),
                    threat_level=ThreatLevel.HIGH,
                    alert_type='data_exfiltration',
                    title='Potential Data Exfiltration Detected',
                    description=f'Unusual data access volume detected for user {user_id}',
                    user_id=user_id,
                    metadata={
                        'data_type': data_type,
                        'current_volume': data_volume,
                        'recent_total_volume': recent_volume + data_volume,
                        'threshold': volume_threshold,
                        'context': context or {}
                    }
                )
                
                return alert
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting data exfiltration: {str(e)}")
            return None
    
    def get_security_dashboard_data(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """
        Get security dashboard data
        
        Args:
            time_range_hours: Time range for dashboard data
            
        Returns:
            Security dashboard data
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=time_range_hours)
            
            # Get recent alerts
            alerts_key = "security_alerts"
            recent_alerts = []
            
            alert_ids = self.redis_client.lrange(alerts_key, 0, 99)  # Last 100 alerts
            for alert_id in alert_ids:
                alert_data = self.redis_client.get(f"alert:{alert_id}")
                if alert_data:
                    alert = json.loads(alert_data)
                    alert_time = datetime.fromisoformat(alert['timestamp'].replace('Z', ''))
                    if alert_time >= start_time:
                        recent_alerts.append(alert)
            
            # Count alerts by threat level
            alerts_by_level = defaultdict(int)
            for alert in recent_alerts:
                alerts_by_level[alert['threat_level']] += 1
            
            # Count alerts by type
            alerts_by_type = defaultdict(int)
            for alert in recent_alerts:
                alerts_by_type[alert['alert_type']] += 1
            
            # Get blocked IPs
            blocked_ips = []
            blocked_ip_keys = self.redis_client.keys("blocked_ip:*")
            for key in blocked_ip_keys:
                ip = key.decode().split(':')[1]
                ttl = self.redis_client.ttl(key)
                if ttl > 0:
                    blocked_ips.append({
                        'ip': ip,
                        'expires_in_seconds': ttl
                    })
            
            # Get top threat sources
            threat_sources = defaultdict(int)
            for alert in recent_alerts:
                if alert.get('source_ip'):
                    threat_sources[alert['source_ip']] += 1
            
            top_threat_sources = sorted(threat_sources.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                'time_range': {
                    'start': start_time.isoformat() + 'Z',
                    'end': end_time.isoformat() + 'Z',
                    'hours': time_range_hours
                },
                'summary': {
                    'total_alerts': len(recent_alerts),
                    'critical_alerts': alerts_by_level.get('CRITICAL', 0),
                    'high_alerts': alerts_by_level.get('HIGH', 0),
                    'blocked_ips': len(blocked_ips),
                    'active_threats': len(threat_sources)
                },
                'alerts_by_level': dict(alerts_by_level),
                'alerts_by_type': dict(alerts_by_type),
                'recent_alerts': recent_alerts[:20],  # Last 20 alerts
                'blocked_ips': blocked_ips,
                'top_threat_sources': dict(top_threat_sources)
            }
            
        except Exception as e:
            logger.error(f"Error getting security dashboard data: {str(e)}")
            return {}
    
    def _track_event(self, event_type: str, event_data: Dict[str, Any], context: Dict[str, Any]):
        """Track security event for pattern analysis"""
        try:
            timestamp = datetime.utcnow()
            ip_address = context.get('ip_address')
            user_id = context.get('user_id')
            
            # Track by IP
            if ip_address:
                self.ip_tracking[ip_address].append({
                    'event_type': event_type,
                    'timestamp': timestamp,
                    'data': event_data
                })
            
            # Track by user
            if user_id:
                self.user_tracking[user_id].append({
                    'event_type': event_type,
                    'timestamp': timestamp,
                    'data': event_data
                })
            
            # Track failed login attempts
            if event_type in ['user_login_failed', 'oauth_login_failed']:
                if ip_address:
                    ip_key = f"failed_logins:ip:{ip_address}"
                    self.redis_client.incr(ip_key)
                    self.redis_client.expire(ip_key, 3600)  # 1 hour
                
                if user_id:
                    user_key = f"failed_logins:user:{user_id}"
                    self.redis_client.incr(user_key)
                    self.redis_client.expire(user_key, 3600)  # 1 hour
            
            # Reset counters on successful login
            elif event_type in ['user_login_success', 'oauth_login_success']:
                if ip_address:
                    self.redis_client.delete(f"failed_logins:ip:{ip_address}")
                if user_id:
                    self.redis_client.delete(f"failed_logins:user:{user_id}")
            
        except Exception as e:
            logger.error(f"Error tracking security event: {str(e)}")
    
    def _check_rule_threshold(self, rule: MonitoringRule, event_type: str,
                            context: Dict[str, Any]) -> Optional[SecurityAlert]:
        """Check if monitoring rule threshold is exceeded"""
        try:
            # Create tracking key
            key_parts = [rule.rule_id, event_type]
            
            # Add context-specific parts
            if 'ip_address' in context:
                key_parts.append(context['ip_address'])
            if 'user_id' in context:
                key_parts.append(context['user_id'])
            
            tracking_key = f"rule_tracking:{':'.join(key_parts)}"
            
            # Increment counter
            count = self.redis_client.incr(tracking_key)
            
            # Set expiry on first increment
            if count == 1:
                self.redis_client.expire(tracking_key, rule.time_window_minutes * 60)
            
            # Check threshold
            if count >= rule.threshold:
                alert = SecurityAlert(
                    alert_id=self._generate_alert_id(),
                    threat_level=rule.threat_level,
                    alert_type=f'rule_violation_{rule.rule_id}',
                    title=f'Security Rule Violation: {rule.name}',
                    description=rule.description,
                    source_ip=context.get('ip_address'),
                    user_id=context.get('user_id'),
                    tenant_id=context.get('tenant_id'),
                    metadata={
                        'rule_id': rule.rule_id,
                        'rule_name': rule.name,
                        'threshold': rule.threshold,
                        'actual_count': count,
                        'time_window_minutes': rule.time_window_minutes
                    }
                )
                
                # Reset counter to avoid spam
                self.redis_client.delete(tracking_key)
                
                return alert
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking rule threshold: {str(e)}")
            return None
    
    def _run_built_in_checks(self, event_type: str, event_data: Dict[str, Any],
                           context: Dict[str, Any]) -> List[SecurityAlert]:
        """Run built-in security checks"""
        alerts = []
        
        try:
            ip_address = context.get('ip_address')
            user_id = context.get('user_id')
            
            # Brute force detection
            if event_type in ['user_login_failed', 'oauth_login_failed']:
                brute_force_alert = self.detect_brute_force_attack(ip_address, user_id)
                if brute_force_alert:
                    alerts.append(brute_force_alert)
            
            # Suspicious login patterns
            if event_type in ['user_login_success', 'oauth_login_success']:
                pattern_alerts = self.detect_suspicious_login_patterns(
                    user_id, ip_address, context.get('user_agent')
                )
                alerts.extend(pattern_alerts)
            
            # Data access monitoring
            if event_type == 'data_export':
                data_volume = event_data.get('data_volume', 0)
                data_type = event_data.get('data_type', 'unknown')
                exfiltration_alert = self.detect_data_exfiltration(user_id, data_volume, data_type, context)
                if exfiltration_alert:
                    alerts.append(exfiltration_alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error running built-in security checks: {str(e)}")
            return []
    
    def _send_alert(self, alert: SecurityAlert):
        """Send security alert through configured channels"""
        try:
            # Store alert
            alert_key = f"alert:{alert.alert_id}"
            self.redis_client.setex(alert_key, 86400 * 7, json.dumps(alert.to_dict()))  # 7 days TTL
            
            # Add to alerts list
            self.redis_client.lpush("security_alerts", alert.alert_id)
            self.redis_client.ltrim("security_alerts", 0, 999)  # Keep last 1000 alerts
            
            # Send through configured channels
            channels = self.config.get('alert_channels', [AlertChannel.LOG.value])
            
            for channel_name in channels:
                try:
                    channel = AlertChannel(channel_name)
                    handler = self.alert_handlers.get(channel)
                    if handler:
                        handler(alert)
                except Exception as e:
                    logger.error(f"Error sending alert through {channel_name}: {str(e)}")
            
            logger.info(f"Security alert sent: {alert.alert_id} - {alert.title}")
            
        except Exception as e:
            logger.error(f"Error sending security alert: {str(e)}")
    
    def _send_email_alert(self, alert: SecurityAlert):
        """Send alert via email"""
        try:
            email_config = self.config.get('email', {})
            if not email_config.get('enabled', False):
                return
            
            smtp_server = email_config.get('smtp_server')
            smtp_port = email_config.get('smtp_port', 587)
            username = email_config.get('username')
            password = email_config.get('password')
            recipients = email_config.get('recipients', [])
            
            if not all([smtp_server, username, password, recipients]):
                logger.warning("Email configuration incomplete, skipping email alert")
                return
            
            # Create email
            msg = MimeMultipart()
            msg['From'] = username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[SECURITY ALERT] {alert.title}"
            
            # Email body
            body = f"""
Security Alert Details:

Alert ID: {alert.alert_id}
Threat Level: {alert.threat_level.value}
Alert Type: {alert.alert_type}
Title: {alert.title}
Description: {alert.description}
Timestamp: {alert.timestamp.isoformat()}

Source IP: {alert.source_ip or 'N/A'}
User ID: {alert.user_id or 'N/A'}
Tenant ID: {alert.tenant_id or 'N/A'}

Additional Metadata:
{json.dumps(alert.metadata, indent=2)}

This is an automated security alert from Universal Auth System.
"""
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent for {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Error sending email alert: {str(e)}")
    
    def _send_webhook_alert(self, alert: SecurityAlert):
        """Send alert via webhook"""
        try:
            webhook_config = self.config.get('webhook', {})
            if not webhook_config.get('enabled', False):
                return
            
            webhook_url = webhook_config.get('url')
            if not webhook_url:
                return
            
            payload = {
                'alert': alert.to_dict(),
                'source': 'universal-auth-security-monitoring'
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'UniversalAuth-SecurityMonitoring/1.0'
            }
            
            # Add authentication if configured
            auth_token = webhook_config.get('auth_token')
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            logger.info(f"Webhook alert sent for {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Error sending webhook alert: {str(e)}")
    
    def _send_slack_alert(self, alert: SecurityAlert):
        """Send alert to Slack"""
        try:
            slack_config = self.config.get('slack', {})
            if not slack_config.get('enabled', False):
                return
            
            webhook_url = slack_config.get('webhook_url')
            if not webhook_url:
                return
            
            # Determine color based on threat level
            color_map = {
                ThreatLevel.LOW: '#36a64f',      # Green
                ThreatLevel.MEDIUM: '#ff9500',   # Orange
                ThreatLevel.HIGH: '#ff0000',     # Red
                ThreatLevel.CRITICAL: '#8b0000'  # Dark Red
            }
            
            color = color_map.get(alert.threat_level, '#ff0000')
            
            payload = {
                'attachments': [{
                    'color': color,
                    'title': f'🚨 Security Alert: {alert.title}',
                    'text': alert.description,
                    'fields': [
                        {
                            'title': 'Threat Level',
                            'value': alert.threat_level.value,
                            'short': True
                        },
                        {
                            'title': 'Alert Type',
                            'value': alert.alert_type,
                            'short': True
                        },
                        {
                            'title': 'Source IP',
                            'value': alert.source_ip or 'N/A',
                            'short': True
                        },
                        {
                            'title': 'User ID',
                            'value': alert.user_id or 'N/A',
                            'short': True
                        }
                    ],
                    'footer': 'Universal Auth Security Monitoring',
                    'ts': int(alert.timestamp.timestamp())
                }]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Slack alert sent for {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Error sending Slack alert: {str(e)}")
    
    def _log_alert(self, alert: SecurityAlert):
        """Log alert to application logs"""
        log_level = {
            ThreatLevel.LOW: logging.INFO,
            ThreatLevel.MEDIUM: logging.WARNING,
            ThreatLevel.HIGH: logging.ERROR,
            ThreatLevel.CRITICAL: logging.CRITICAL
        }.get(alert.threat_level, logging.ERROR)
        
        logger.log(log_level, f"SECURITY ALERT [{alert.threat_level.value}] {alert.title}: {alert.description}")
    
    def _check_impossible_travel(self, user_id: str, ip_address: str) -> Optional[SecurityAlert]:
        """Check for impossible travel between login locations"""
        # Simplified implementation - in production, use geolocation service
        try:
            last_login_key = f"last_login_location:{user_id}"
            last_location = self.redis_client.get(last_login_key)
            
            if last_location:
                last_data = json.loads(last_location)
                last_ip = last_data['ip']
                last_time = datetime.fromisoformat(last_data['timestamp'])
                
                # If different IP and recent login (within 1 hour)
                if last_ip != ip_address and (datetime.utcnow() - last_time).seconds < 3600:
                    # In production, calculate actual distance and travel time
                    return SecurityAlert(
                        alert_id=self._generate_alert_id(),
                        threat_level=ThreatLevel.MEDIUM,
                        alert_type='impossible_travel',
                        title='Impossible Travel Detected',
                        description=f'User {user_id} logged in from different location too quickly',
                        source_ip=ip_address,
                        user_id=user_id,
                        metadata={
                            'previous_ip': last_ip,
                            'previous_login': last_data['timestamp'],
                            'time_difference_seconds': (datetime.utcnow() - last_time).seconds
                        }
                    )
            
            # Update last login location
            self.redis_client.setex(
                last_login_key,
                86400,  # 24 hours
                json.dumps({
                    'ip': ip_address,
                    'timestamp': datetime.utcnow().isoformat()
                })
            )
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking impossible travel: {str(e)}")
            return None
    
    def _check_unusual_login_time(self, user_id: str) -> Optional[SecurityAlert]:
        """Check for unusual login times"""
        try:
            current_hour = datetime.utcnow().hour
            
            # Track login hours
            login_hours_key = f"login_hours:{user_id}"
            self.redis_client.sadd(login_hours_key, current_hour)
            self.redis_client.expire(login_hours_key, 86400 * 30)  # 30 days
            
            # Get historical login hours
            historical_hours = self.redis_client.smembers(login_hours_key)
            historical_hours = {int(h) for h in historical_hours}
            
            # If we have enough history and current hour is unusual
            if len(historical_hours) > 5 and current_hour not in historical_hours:
                # Check if it's really unusual (outside normal business hours)
                if current_hour < 6 or current_hour > 22:  # Before 6 AM or after 10 PM
                    return SecurityAlert(
                        alert_id=self._generate_alert_id(),
                        threat_level=ThreatLevel.LOW,
                        alert_type='unusual_login_time',
                        title='Unusual Login Time',
                        description=f'User {user_id} logged in at unusual hour: {current_hour}:00',
                        user_id=user_id,
                        metadata={
                            'login_hour': current_hour,
                            'historical_hours': list(historical_hours)
                        }
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking unusual login time: {str(e)}")
            return None
    
    def _check_new_device(self, user_id: str, user_agent: str) -> Optional[SecurityAlert]:
        """Check for login from new device"""
        if not user_agent:
            return None
        
        try:
            # Create device fingerprint
            device_hash = hashlib.md5(user_agent.encode()).hexdigest()
            
            devices_key = f"user_devices:{user_id}"
            is_new_device = not self.redis_client.sismember(devices_key, device_hash)
            
            if is_new_device:
                # Add device to known devices
                self.redis_client.sadd(devices_key, device_hash)
                self.redis_client.expire(devices_key, 86400 * 90)  # 90 days
                
                return SecurityAlert(
                    alert_id=self._generate_alert_id(),
                    threat_level=ThreatLevel.LOW,
                    alert_type='new_device_login',
                    title='New Device Login',
                    description=f'User {user_id} logged in from new device',
                    user_id=user_id,
                    metadata={
                        'user_agent': user_agent,
                        'device_hash': device_hash
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking new device: {str(e)}")
            return None
    
    def _check_rapid_logins(self, user_id: str) -> Optional[SecurityAlert]:
        """Check for rapid successive logins"""
        try:
            login_times_key = f"login_times:{user_id}"
            current_time = time.time()
            
            # Add current login time
            self.redis_client.lpush(login_times_key, current_time)
            self.redis_client.expire(login_times_key, 3600)  # 1 hour
            
            # Get recent login times
            recent_logins = self.redis_client.lrange(login_times_key, 0, 4)  # Last 5 logins
            recent_logins = [float(t) for t in recent_logins]
            
            # Check if 5 logins within 5 minutes
            if len(recent_logins) >= 5:
                time_span = recent_logins[0] - recent_logins[-1]
                if time_span < 300:  # 5 minutes
                    return SecurityAlert(
                        alert_id=self._generate_alert_id(),
                        threat_level=ThreatLevel.MEDIUM,
                        alert_type='rapid_logins',
                        title='Rapid Login Attempts',
                        description=f'User {user_id} had multiple rapid login attempts',
                        user_id=user_id,
                        metadata={
                            'login_count': len(recent_logins),
                            'time_span_seconds': time_span
                        }
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking rapid logins: {str(e)}")
            return None
    
    def _block_ip_temporarily(self, ip_address: str, duration_minutes: int = 60):
        """Temporarily block an IP address"""
        try:
            block_key = f"blocked_ip:{ip_address}"
            self.redis_client.setex(block_key, duration_minutes * 60, "1")
            logger.warning(f"Temporarily blocked IP {ip_address} for {duration_minutes} minutes")
        except Exception as e:
            logger.error(f"Error blocking IP {ip_address}: {str(e)}")
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        return f"alert_{int(time.time())}_{hash(time.time()) % 10000:04d}"
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default security monitoring configuration"""
        return {
            'brute_force_ip_threshold': 10,
            'brute_force_user_threshold': 5,
            'data_exfiltration_threshold': {
                'user_data': 1000000,  # 1MB
                'admin_data': 10000000,  # 10MB
                'system_data': 100000000  # 100MB
            },
            'alert_channels': ['log'],
            'email': {
                'enabled': False
            },
            'webhook': {
                'enabled': False
            },
            'slack': {
                'enabled': False
            }
        }
    
    def _load_monitoring_rules(self) -> List[MonitoringRule]:
        """Load security monitoring rules"""
        # Default monitoring rules
        return [
            MonitoringRule(
                rule_id='failed_login_threshold',
                name='Failed Login Threshold',
                description='Multiple failed login attempts detected',
                event_types=['user_login_failed', 'oauth_login_failed'],
                conditions={'success': False},
                threshold=5,
                time_window_minutes=15,
                threat_level=ThreatLevel.MEDIUM
            ),
            MonitoringRule(
                rule_id='admin_access_monitoring',
                name='Admin Access Monitoring',
                description='Administrative access detected',
                event_types=['admin_login', 'admin_access'],
                conditions={},
                threshold=1,
                time_window_minutes=1,
                threat_level=ThreatLevel.WARN
            ),
            MonitoringRule(
                rule_id='config_change_monitoring',
                name='Configuration Change Monitoring',
                description='System configuration changes detected',
                event_types=['config_updated', 'provider_configured'],
                conditions={},
                threshold=1,
                time_window_minutes=1,
                threat_level=ThreatLevel.WARN
            )
        ]
    
    def _background_monitoring(self):
        """Background monitoring thread"""
        while self.monitoring_active:
            try:
                # Perform periodic security checks
                self._cleanup_old_tracking_data()
                time.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Error in background monitoring: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _cleanup_old_tracking_data(self):
        """Clean up old tracking data"""
        try:
            # Clean up in-memory tracking data older than 1 hour
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            for ip, events in self.ip_tracking.items():
                while events and events[0]['timestamp'] < cutoff_time:
                    events.popleft()
            
            for user, events in self.user_tracking.items():
                while events and events[0]['timestamp'] < cutoff_time:
                    events.popleft()
            
        except Exception as e:
            logger.error(f"Error cleaning up tracking data: {str(e)}")

# Factory function
def create_security_monitoring_service(redis_url: str = None, 
                                     config: Dict[str, Any] = None) -> SecurityMonitoringService:
    """Create security monitoring service instance"""
    redis_client = None
    if redis_url:
        redis_client = redis.from_url(redis_url)
    
    return SecurityMonitoringService(redis_client, config)