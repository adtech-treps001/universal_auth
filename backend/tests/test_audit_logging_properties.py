"""
Property Tests for Audit Logging Completeness

This module contains property-based tests for audit logging completeness
using Hypothesis to validate universal correctness properties.

**Feature: universal-auth, Property 15: Audit Logging Completeness**
**Validates: Requirements 7.1**
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timedelta
import uuid

# Audit event strategies
event_type_strategy = st.sampled_from([
    'user_login', 'user_logout', 'user_registration', 'password_change',
    'role_assignment', 'permission_grant', 'api_key_created', 'api_key_deleted',
    'config_change', 'admin_access', 'unauthorized_access', 'data_export'
])

user_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
ip_address_strategy = st.one_of(
    st.text(min_size=7, max_size=15).filter(lambda x: all(part.isdigit() and 0 <= int(part) <= 255 for part in x.split('.')) if x.count('.') == 3 else False),
    st.just('127.0.0.1'),
    st.just('192.168.1.1'),
    st.just('10.0.0.1')
)
user_agent_strategy = st.sampled_from([
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
])

# Audit context strategies
audit_context_strategy = st.fixed_dictionaries({
    'user_id': st.one_of(st.none(), user_id_strategy),
    'session_id': st.one_of(st.none(), st.text(min_size=10, max_size=50)),
    'ip_address': ip_address_strategy,
    'user_agent': user_agent_strategy,
    'tenant_id': st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    'request_id': st.text(min_size=10, max_size=50)
})

# Event data strategies
event_data_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_')),
    values=st.one_of(
        st.text(min_size=0, max_size=200),
        st.integers(min_value=0, max_value=10000),
        st.booleans(),
        st.lists(st.text(min_size=1, max_size=50), max_size=5)
    ),
    min_size=0,
    max_size=10
)

class AuditLogger:
    """Core audit logging system"""
    
    # Required audit fields
    REQUIRED_FIELDS = [
        'event_id', 'event_type', 'timestamp', 'user_id', 'ip_address',
        'user_agent', 'success', 'event_data'
    ]
    
    # Event severity levels
    SEVERITY_LEVELS = {
        'user_login': 'INFO',
        'user_logout': 'INFO',
        'user_registration': 'INFO',
        'password_change': 'WARN',
        'role_assignment': 'WARN',
        'permission_grant': 'WARN',
        'api_key_created': 'WARN',
        'api_key_deleted': 'WARN',
        'config_change': 'WARN',
        'admin_access': 'WARN',
        'unauthorized_access': 'ERROR',
        'data_export': 'WARN'
    }
    
    # Sensitive fields that should be masked
    SENSITIVE_FIELDS = ['password', 'api_key', 'secret', 'token', 'private_key']
    
    def __init__(self):
        self.audit_logs = []
    
    def log_event(self, event_type: str, context: Dict[str, Any], 
                  event_data: Dict[str, Any] = None, success: bool = True) -> str:
        """
        Log an audit event
        
        Args:
            event_type: Type of event being logged
            context: Audit context (user, IP, etc.)
            event_data: Additional event-specific data
            success: Whether the event was successful
            
        Returns:
            Event ID of the logged event
        """
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Mask sensitive data
        masked_event_data = self._mask_sensitive_data(event_data or {})
        
        # Create audit log entry
        audit_entry = {
            'event_id': event_id,
            'event_type': event_type,
            'timestamp': timestamp,
            'user_id': context.get('user_id'),
            'session_id': context.get('session_id'),
            'ip_address': context.get('ip_address'),
            'user_agent': context.get('user_agent'),
            'tenant_id': context.get('tenant_id'),
            'request_id': context.get('request_id'),
            'success': success,
            'severity': self.SEVERITY_LEVELS.get(event_type, 'INFO'),
            'event_data': masked_event_data
        }
        
        # Store audit log
        self.audit_logs.append(audit_entry)
        
        return event_id
    
    def get_audit_logs(self, filters: Dict[str, Any] = None, 
                      start_time: datetime = None, end_time: datetime = None) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with optional filtering
        
        Args:
            filters: Filter criteria
            start_time: Start time for filtering
            end_time: End time for filtering
            
        Returns:
            List of matching audit log entries
        """
        logs = self.audit_logs.copy()
        
        # Apply time filtering
        if start_time or end_time:
            filtered_logs = []
            for log in logs:
                log_time = datetime.fromisoformat(log['timestamp'])
                if start_time and log_time < start_time:
                    continue
                if end_time and log_time > end_time:
                    continue
                filtered_logs.append(log)
            logs = filtered_logs
        
        # Apply other filters
        if filters:
            filtered_logs = []
            for log in logs:
                match = True
                for key, value in filters.items():
                    if key in log and log[key] != value:
                        match = False
                        break
                if match:
                    filtered_logs.append(log)
            logs = filtered_logs
        
        return logs
    
    def validate_audit_entry(self, audit_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate audit log entry completeness and structure
        
        Args:
            audit_entry: Audit log entry to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in audit_entry:
                errors.append(f"Missing required field: {field}")
            elif audit_entry[field] is None and field in ['event_id', 'event_type', 'timestamp']:
                errors.append(f"Required field {field} cannot be None")
        
        # Validate field types and formats
        if 'event_id' in audit_entry:
            event_id = audit_entry['event_id']
            if not isinstance(event_id, str) or len(event_id) == 0:
                errors.append("event_id must be non-empty string")
        
        if 'event_type' in audit_entry:
            event_type = audit_entry['event_type']
            if not isinstance(event_type, str) or len(event_type) == 0:
                errors.append("event_type must be non-empty string")
        
        if 'timestamp' in audit_entry:
            timestamp = audit_entry['timestamp']
            if not isinstance(timestamp, str):
                errors.append("timestamp must be string")
            else:
                try:
                    datetime.fromisoformat(timestamp)
                except ValueError:
                    errors.append("timestamp must be valid ISO format")
        
        if 'success' in audit_entry:
            if not isinstance(audit_entry['success'], bool):
                errors.append("success must be boolean")
        
        if 'event_data' in audit_entry:
            if not isinstance(audit_entry['event_data'], dict):
                errors.append("event_data must be dictionary")
        
        # Check for sensitive data exposure
        if 'event_data' in audit_entry and isinstance(audit_entry['event_data'], dict):
            for key, value in audit_entry['event_data'].items():
                if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                    if not self._is_masked_value(value):
                        warnings.append(f"Potentially sensitive field {key} may not be properly masked")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in event data"""
        masked_data = {}
        
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                # Mask sensitive values
                if isinstance(value, str) and len(value) > 4:
                    masked_data[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
                else:
                    masked_data[key] = '***'
            else:
                masked_data[key] = value
        
        return masked_data
    
    def _is_masked_value(self, value: Any) -> bool:
        """Check if a value appears to be masked"""
        if isinstance(value, str):
            return '*' in value or value == '***'
        return False
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit log statistics"""
        total_events = len(self.audit_logs)
        
        if total_events == 0:
            return {
                'total_events': 0,
                'events_by_type': {},
                'events_by_severity': {},
                'success_rate': 0.0,
                'time_range': None
            }
        
        # Count events by type
        events_by_type = {}
        events_by_severity = {}
        successful_events = 0
        
        timestamps = []
        
        for log in self.audit_logs:
            event_type = log.get('event_type', 'unknown')
            severity = log.get('severity', 'INFO')
            success = log.get('success', False)
            timestamp = log.get('timestamp')
            
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
            events_by_severity[severity] = events_by_severity.get(severity, 0) + 1
            
            if success:
                successful_events += 1
            
            if timestamp:
                timestamps.append(timestamp)
        
        # Calculate time range
        time_range = None
        if timestamps:
            timestamps.sort()
            time_range = {
                'start': timestamps[0],
                'end': timestamps[-1]
            }
        
        return {
            'total_events': total_events,
            'events_by_type': events_by_type,
            'events_by_severity': events_by_severity,
            'success_rate': successful_events / total_events if total_events > 0 else 0.0,
            'time_range': time_range
        }

class TestAuditLoggingCompleteness:
    """Property tests for audit logging completeness"""
    
    @given(
        event_type=event_type_strategy,
        context=audit_context_strategy,
        event_data=event_data_strategy,
        success=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_15_audit_logging_completeness(self, event_type, context, event_data, success):
        """
        Property 15: Audit Logging Completeness
        
        For any audit event, the logging system should capture all required
        information and store it in a complete, structured format.
        
        **Validates: Requirements 7.1**
        """
        # Create audit logger
        audit_logger = AuditLogger()
        
        # Log the event
        event_id = audit_logger.log_event(event_type, context, event_data, success)
        
        # Verify event was logged
        assert isinstance(event_id, str), "Event ID should be returned as string"
        assert len(event_id) > 0, "Event ID should not be empty"
        
        # Retrieve the logged event
        logs = audit_logger.get_audit_logs()
        assert len(logs) == 1, "Exactly one event should be logged"
        
        logged_event = logs[0]
        
        # Validate the logged event
        validation_result = audit_logger.validate_audit_entry(logged_event)
        assert validation_result['valid'] == True, f"Logged event should be valid: {validation_result['errors']}"
        
        # Verify all required fields are present
        for field in audit_logger.REQUIRED_FIELDS:
            assert field in logged_event, f"Required field {field} should be present"
        
        # Verify field values
        assert logged_event['event_id'] == event_id, "Event ID should match returned ID"
        assert logged_event['event_type'] == event_type, "Event type should be preserved"
        assert logged_event['success'] == success, "Success flag should be preserved"
        
        # Verify context information is captured
        for key, value in context.items():
            if value is not None:
                assert logged_event[key] == value, f"Context {key} should be preserved"
        
        # Verify timestamp is valid
        timestamp = logged_event['timestamp']
        assert isinstance(timestamp, str), "Timestamp should be string"
        datetime.fromisoformat(timestamp)  # Should not raise exception
        
        # Verify severity is assigned
        assert 'severity' in logged_event, "Severity should be assigned"
        expected_severity = audit_logger.SEVERITY_LEVELS.get(event_type, 'INFO')
        assert logged_event['severity'] == expected_severity, "Severity should match event type"
    
    @given(
        events=st.lists(
            st.tuples(event_type_strategy, audit_context_strategy, event_data_strategy, st.booleans()),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50)
    def test_property_audit_log_retrieval_completeness(self, events):
        """
        Property: Audit Log Retrieval Completeness
        
        For any set of logged events, retrieval should return all events
        with complete information and proper filtering capabilities.
        
        **Validates: Requirements 7.1**
        """
        audit_logger = AuditLogger()
        
        # Log all events
        event_ids = []
        for event_type, context, event_data, success in events:
            event_id = audit_logger.log_event(event_type, context, event_data, success)
            event_ids.append(event_id)
        
        # Retrieve all logs
        all_logs = audit_logger.get_audit_logs()
        
        # Verify all events are retrieved
        assert len(all_logs) == len(events), "All logged events should be retrievable"
        
        # Verify each event is complete
        retrieved_event_ids = [log['event_id'] for log in all_logs]
        for event_id in event_ids:
            assert event_id in retrieved_event_ids, f"Event {event_id} should be retrievable"
        
        # Verify each retrieved event is valid
        for log in all_logs:
            validation_result = audit_logger.validate_audit_entry(log)
            assert validation_result['valid'] == True, f"Retrieved event should be valid: {validation_result['errors']}"
    
    @given(
        events_with_sensitive_data=st.lists(
            st.tuples(
                event_type_strategy,
                audit_context_strategy,
                st.dictionaries(
                    keys=st.sampled_from(['password', 'api_key', 'secret_token', 'username', 'email']),
                    values=st.text(min_size=5, max_size=50),
                    min_size=1,
                    max_size=3
                ),
                st.booleans()
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=40)
    def test_property_sensitive_data_masking(self, events_with_sensitive_data):
        """
        Property: Sensitive Data Masking
        
        For any events containing sensitive data, the audit system should
        properly mask sensitive information while preserving audit completeness.
        
        **Validates: Requirements 7.1**
        """
        audit_logger = AuditLogger()
        
        # Log events with sensitive data
        for event_type, context, event_data, success in events_with_sensitive_data:
            audit_logger.log_event(event_type, context, event_data, success)
        
        # Retrieve logs
        logs = audit_logger.get_audit_logs()
        
        # Verify sensitive data is masked
        for log in logs:
            event_data = log.get('event_data', {})
            
            for key, value in event_data.items():
                if any(sensitive in key.lower() for sensitive in audit_logger.SENSITIVE_FIELDS):
                    # Sensitive fields should be masked
                    assert audit_logger._is_masked_value(value), f"Sensitive field {key} should be masked"
                    
            # Validate the log entry
            validation_result = audit_logger.validate_audit_entry(log)
            assert validation_result['valid'] == True, "Log with masked data should be valid"
    
    @given(
        base_events=st.lists(
            st.tuples(event_type_strategy, audit_context_strategy, event_data_strategy, st.booleans()),
            min_size=5,
            max_size=15
        ),
        filter_criteria=st.dictionaries(
            keys=st.sampled_from(['event_type', 'user_id', 'success', 'tenant_id']),
            values=st.one_of(
                event_type_strategy,
                user_id_strategy,
                st.booleans(),
                st.text(min_size=1, max_size=50)
            ),
            min_size=1,
            max_size=2
        )
    )
    @settings(max_examples=30)
    def test_property_audit_log_filtering_accuracy(self, base_events, filter_criteria):
        """
        Property: Audit Log Filtering Accuracy
        
        For any set of audit events and filter criteria, filtering should
        return exactly the events that match the criteria.
        
        **Validates: Requirements 7.1**
        """
        audit_logger = AuditLogger()
        
        # Log all events
        for event_type, context, event_data, success in base_events:
            audit_logger.log_event(event_type, context, event_data, success)
        
        # Apply filters
        filtered_logs = audit_logger.get_audit_logs(filters=filter_criteria)
        
        # Verify filtering accuracy
        all_logs = audit_logger.get_audit_logs()
        
        # Manually filter to verify accuracy
        expected_logs = []
        for log in all_logs:
            match = True
            for key, value in filter_criteria.items():
                if key in log and log[key] != value:
                    match = False
                    break
            if match:
                expected_logs.append(log)
        
        # Compare results
        assert len(filtered_logs) == len(expected_logs), "Filter should return correct number of events"
        
        filtered_event_ids = [log['event_id'] for log in filtered_logs]
        expected_event_ids = [log['event_id'] for log in expected_logs]
        
        assert set(filtered_event_ids) == set(expected_event_ids), "Filter should return correct events"
    
    @given(
        events=st.lists(
            st.tuples(event_type_strategy, audit_context_strategy, event_data_strategy, st.booleans()),
            min_size=3,
            max_size=10
        ),
        time_window_hours=st.integers(min_value=1, max_value=24)
    )
    @settings(max_examples=25)
    def test_property_audit_log_time_filtering(self, events, time_window_hours):
        """
        Property: Audit Log Time Filtering
        
        For any set of audit events, time-based filtering should correctly
        identify events within the specified time range.
        
        **Validates: Requirements 7.1**
        """
        audit_logger = AuditLogger()
        
        # Log events
        for event_type, context, event_data, success in events:
            audit_logger.log_event(event_type, context, event_data, success)
        
        # Define time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)
        
        # Filter by time range
        time_filtered_logs = audit_logger.get_audit_logs(start_time=start_time, end_time=end_time)
        
        # Verify time filtering
        for log in time_filtered_logs:
            log_time = datetime.fromisoformat(log['timestamp'])
            assert start_time <= log_time <= end_time, "Filtered log should be within time range"
        
        # Verify completeness - all logs should be within range since they were just created
        all_logs = audit_logger.get_audit_logs()
        assert len(time_filtered_logs) == len(all_logs), "All recent logs should be within time range"
    
    @given(
        events=st.lists(
            st.tuples(event_type_strategy, audit_context_strategy, event_data_strategy, st.booleans()),
            min_size=5,
            max_size=20
        )
    )
    @settings(max_examples=30)
    def test_property_audit_statistics_accuracy(self, events):
        """
        Property: Audit Statistics Accuracy
        
        For any set of audit events, statistics should accurately reflect
        the logged events and their characteristics.
        
        **Validates: Requirements 7.1**
        """
        audit_logger = AuditLogger()
        
        # Log events
        expected_by_type = {}
        expected_by_severity = {}
        expected_success_count = 0
        
        for event_type, context, event_data, success in events:
            audit_logger.log_event(event_type, context, event_data, success)
            
            # Track expected statistics
            expected_by_type[event_type] = expected_by_type.get(event_type, 0) + 1
            
            severity = audit_logger.SEVERITY_LEVELS.get(event_type, 'INFO')
            expected_by_severity[severity] = expected_by_severity.get(severity, 0) + 1
            
            if success:
                expected_success_count += 1
        
        # Get statistics
        stats = audit_logger.get_audit_statistics()
        
        # Verify statistics accuracy
        assert stats['total_events'] == len(events), "Total events should match logged events"
        assert stats['events_by_type'] == expected_by_type, "Events by type should match"
        assert stats['events_by_severity'] == expected_by_severity, "Events by severity should match"
        
        expected_success_rate = expected_success_count / len(events) if events else 0.0
        assert abs(stats['success_rate'] - expected_success_rate) < 0.001, "Success rate should be accurate"
        
        # Verify time range
        if events:
            assert stats['time_range'] is not None, "Time range should be provided for non-empty logs"
            assert 'start' in stats['time_range'], "Time range should have start"
            assert 'end' in stats['time_range'], "Time range should have end"
    
    @given(
        event_type=event_type_strategy,
        context=audit_context_strategy,
        event_data=event_data_strategy,
        multiple_logs=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=20)
    def test_property_audit_logging_consistency(self, event_type, context, event_data, multiple_logs):
        """
        Property: Audit Logging Consistency
        
        For any event logged multiple times, each log entry should be
        consistent and complete while maintaining unique identifiers.
        
        **Validates: Requirements 7.1**
        """
        audit_logger = AuditLogger()
        
        # Log the same event multiple times
        event_ids = []
        for _ in range(multiple_logs):
            event_id = audit_logger.log_event(event_type, context, event_data, True)
            event_ids.append(event_id)
        
        # Verify all event IDs are unique
        assert len(set(event_ids)) == len(event_ids), "All event IDs should be unique"
        
        # Retrieve all logs
        logs = audit_logger.get_audit_logs()
        assert len(logs) == multiple_logs, "All events should be logged"
        
        # Verify consistency across logs (except unique fields)
        first_log = logs[0]
        for log in logs[1:]:
            # These fields should be consistent
            assert log['event_type'] == first_log['event_type'], "Event type should be consistent"
            assert log['success'] == first_log['success'], "Success flag should be consistent"
            assert log['severity'] == first_log['severity'], "Severity should be consistent"
            
            # Context should be consistent
            for key in ['user_id', 'ip_address', 'user_agent', 'tenant_id']:
                assert log[key] == first_log[key], f"Context {key} should be consistent"
            
            # Event data should be consistent
            assert log['event_data'] == first_log['event_data'], "Event data should be consistent"
            
            # These fields should be unique or different
            assert log['event_id'] != first_log['event_id'], "Event IDs should be unique"
            # Timestamps may be different due to timing

if __name__ == "__main__":
    pytest.main([__file__, "-v"])