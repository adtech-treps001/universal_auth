"""
Property Tests for API Response Format Consistency

This module contains property-based tests for API response format consistency
using Hypothesis to validate universal correctness properties.

**Feature: universal-auth, Property 17: API Response Format Consistency**
**Validates: Requirements 8.3**
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Dict, Any, List, Optional, Union
import json
from datetime import datetime

# API response strategies
status_code_strategy = st.sampled_from([200, 201, 400, 401, 403, 404, 422, 500])
success_status_strategy = st.sampled_from([200, 201, 202, 204])
error_status_strategy = st.sampled_from([400, 401, 403, 404, 422, 500])

# Data strategies
user_data_strategy = st.fixed_dictionaries({
    'id': st.text(min_size=1, max_size=50),
    'email': st.emails(),
    'name': st.text(min_size=1, max_size=100),
    'roles': st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=3)
})

project_data_strategy = st.fixed_dictionaries({
    'id': st.text(min_size=1, max_size=50),
    'name': st.text(min_size=1, max_size=100),
    'description': st.text(min_size=0, max_size=500),
    'created_at': st.text(min_size=10, max_size=30)  # ISO datetime string
})

error_detail_strategy = st.fixed_dictionaries({
    'field': st.text(min_size=1, max_size=50),
    'message': st.text(min_size=1, max_size=200),
    'code': st.text(min_size=1, max_size=20)
})

# Pagination strategies
pagination_strategy = st.fixed_dictionaries({
    'page': st.integers(min_value=1, max_value=100),
    'per_page': st.integers(min_value=1, max_value=100),
    'total': st.integers(min_value=0, max_value=10000),
    'pages': st.integers(min_value=1, max_value=1000)
})

class APIResponseFormatter:
    """Core API response formatting logic"""
    
    # Standard response structure
    RESPONSE_STRUCTURE = {
        'success': bool,
        'data': Any,
        'message': str,
        'errors': List[Dict[str, Any]],
        'meta': Dict[str, Any]
    }
    
    # Error code mappings
    ERROR_CODES = {
        400: 'BAD_REQUEST',
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        422: 'VALIDATION_ERROR',
        500: 'INTERNAL_ERROR'
    }
    
    # Success messages
    SUCCESS_MESSAGES = {
        200: 'Request successful',
        201: 'Resource created successfully',
        202: 'Request accepted',
        204: 'Request successful, no content'
    }
    
    @staticmethod
    def format_success_response(data: Any, message: str = None, meta: Dict[str, Any] = None, 
                               status_code: int = 200) -> Dict[str, Any]:
        """
        Format successful API response
        
        Args:
            data: Response data
            message: Success message
            meta: Metadata (pagination, etc.)
            status_code: HTTP status code
            
        Returns:
            Formatted response dictionary
        """
        if message is None:
            message = APIResponseFormatter.SUCCESS_MESSAGES.get(status_code, 'Request successful')
        
        response = {
            'success': True,
            'data': data,
            'message': message,
            'errors': [],
            'meta': meta or {}
        }
        
        # Add timestamp
        response['meta']['timestamp'] = datetime.utcnow().isoformat()
        response['meta']['status_code'] = status_code
        
        return response
    
    @staticmethod
    def format_error_response(message: str, errors: List[Dict[str, Any]] = None, 
                             status_code: int = 400, error_code: str = None) -> Dict[str, Any]:
        """
        Format error API response
        
        Args:
            message: Error message
            errors: List of detailed errors
            status_code: HTTP status code
            error_code: Application-specific error code
            
        Returns:
            Formatted error response dictionary
        """
        if error_code is None:
            error_code = APIResponseFormatter.ERROR_CODES.get(status_code, 'UNKNOWN_ERROR')
        
        response = {
            'success': False,
            'data': None,
            'message': message,
            'errors': errors or [],
            'meta': {
                'timestamp': datetime.utcnow().isoformat(),
                'status_code': status_code,
                'error_code': error_code
            }
        }
        
        return response
    
    @staticmethod
    def format_validation_error_response(validation_errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format validation error response
        
        Args:
            validation_errors: List of validation error details
            
        Returns:
            Formatted validation error response
        """
        return APIResponseFormatter.format_error_response(
            message='Validation failed',
            errors=validation_errors,
            status_code=422,
            error_code='VALIDATION_ERROR'
        )
    
    @staticmethod
    def format_paginated_response(items: List[Any], pagination: Dict[str, Any], 
                                 message: str = None) -> Dict[str, Any]:
        """
        Format paginated response
        
        Args:
            items: List of items for current page
            pagination: Pagination metadata
            message: Success message
            
        Returns:
            Formatted paginated response
        """
        meta = pagination.copy()
        meta['timestamp'] = datetime.utcnow().isoformat()
        meta['status_code'] = 200
        
        return {
            'success': True,
            'data': items,
            'message': message or 'Request successful',
            'errors': [],
            'meta': meta
        }
    
    @staticmethod
    def validate_response_structure(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate response structure against standard format
        
        Args:
            response: Response dictionary to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ['success', 'data', 'message', 'errors', 'meta']
        for field in required_fields:
            if field not in response:
                errors.append(f"Missing required field: {field}")
        
        # Validate field types
        if 'success' in response and not isinstance(response['success'], bool):
            errors.append("Field 'success' must be boolean")
        
        if 'message' in response and not isinstance(response['message'], str):
            errors.append("Field 'message' must be string")
        
        if 'errors' in response and not isinstance(response['errors'], list):
            errors.append("Field 'errors' must be list")
        
        if 'meta' in response and not isinstance(response['meta'], dict):
            errors.append("Field 'meta' must be dictionary")
        
        # Validate meta fields
        if 'meta' in response and isinstance(response['meta'], dict):
            meta = response['meta']
            
            if 'timestamp' not in meta:
                warnings.append("Meta should include timestamp")
            
            if 'status_code' not in meta:
                warnings.append("Meta should include status_code")
        
        # Validate error structure
        if 'errors' in response and isinstance(response['errors'], list):
            for i, error in enumerate(response['errors']):
                if not isinstance(error, dict):
                    errors.append(f"Error {i} must be dictionary")
                else:
                    if 'message' not in error:
                        errors.append(f"Error {i} missing message field")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    @staticmethod
    def normalize_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize response to standard format
        
        Args:
            response: Response to normalize
            
        Returns:
            Normalized response
        """
        normalized = {
            'success': response.get('success', True),
            'data': response.get('data'),
            'message': response.get('message', ''),
            'errors': response.get('errors', []),
            'meta': response.get('meta', {})
        }
        
        # Ensure meta has required fields
        if 'timestamp' not in normalized['meta']:
            normalized['meta']['timestamp'] = datetime.utcnow().isoformat()
        
        if 'status_code' not in normalized['meta']:
            # Infer status code from success flag
            normalized['meta']['status_code'] = 200 if normalized['success'] else 400
        
        return normalized

class TestAPIResponseFormatConsistency:
    """Property tests for API response format consistency"""
    
    @given(
        data=st.one_of(user_data_strategy, project_data_strategy, st.lists(user_data_strategy, min_size=0, max_size=5)),
        message=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
        status_code=success_status_strategy
    )
    @settings(max_examples=100)
    def test_property_17_api_response_format_consistency(self, data, message, status_code):
        """
        Property 17: API Response Format Consistency
        
        For any successful API response, the format should be consistent
        and include all required fields in the correct structure.
        
        **Validates: Requirements 8.3**
        """
        # Format success response
        response = APIResponseFormatter.format_success_response(data, message, status_code=status_code)
        
        # Validate response structure
        validation_result = APIResponseFormatter.validate_response_structure(response)
        
        # Response should be valid
        assert validation_result['valid'] == True, f"Response should be valid: {validation_result['errors']}"
        
        # Verify required fields
        assert 'success' in response, "Response should have 'success' field"
        assert 'data' in response, "Response should have 'data' field"
        assert 'message' in response, "Response should have 'message' field"
        assert 'errors' in response, "Response should have 'errors' field"
        assert 'meta' in response, "Response should have 'meta' field"
        
        # Verify field types and values
        assert response['success'] == True, "Success response should have success=True"
        assert response['data'] == data, "Response data should match input data"
        assert isinstance(response['message'], str), "Message should be string"
        assert isinstance(response['errors'], list), "Errors should be list"
        assert len(response['errors']) == 0, "Success response should have empty errors list"
        assert isinstance(response['meta'], dict), "Meta should be dictionary"
        
        # Verify meta fields
        meta = response['meta']
        assert 'timestamp' in meta, "Meta should include timestamp"
        assert 'status_code' in meta, "Meta should include status_code"
        assert meta['status_code'] == status_code, "Meta status_code should match input"
    
    @given(
        message=st.text(min_size=1, max_size=200),
        errors=st.lists(error_detail_strategy, min_size=0, max_size=5),
        status_code=error_status_strategy
    )
    @settings(max_examples=80)
    def test_property_error_response_format_consistency(self, message, errors, status_code):
        """
        Property: Error Response Format Consistency
        
        For any error API response, the format should be consistent
        and properly indicate failure with appropriate error details.
        
        **Validates: Requirements 8.3**
        """
        # Format error response
        response = APIResponseFormatter.format_error_response(message, errors, status_code)
        
        # Validate response structure
        validation_result = APIResponseFormatter.validate_response_structure(response)
        
        # Response should be valid
        assert validation_result['valid'] == True, f"Error response should be valid: {validation_result['errors']}"
        
        # Verify error response characteristics
        assert response['success'] == False, "Error response should have success=False"
        assert response['data'] is None, "Error response should have data=None"
        assert response['message'] == message, "Error message should match input"
        assert response['errors'] == errors, "Error details should match input"
        
        # Verify meta fields for error response
        meta = response['meta']
        assert meta['status_code'] == status_code, "Meta status_code should match input"
        assert 'error_code' in meta, "Error response meta should include error_code"
        assert 'timestamp' in meta, "Error response meta should include timestamp"
    
    @given(
        items=st.lists(user_data_strategy, min_size=0, max_size=10),
        pagination=pagination_strategy
    )
    @settings(max_examples=60)
    def test_property_paginated_response_format_consistency(self, items, pagination):
        """
        Property: Paginated Response Format Consistency
        
        For any paginated API response, the format should include
        pagination metadata and maintain consistent structure.
        
        **Validates: Requirements 8.3**
        """
        # Format paginated response
        response = APIResponseFormatter.format_paginated_response(items, pagination)
        
        # Validate response structure
        validation_result = APIResponseFormatter.validate_response_structure(response)
        
        # Response should be valid
        assert validation_result['valid'] == True, f"Paginated response should be valid: {validation_result['errors']}"
        
        # Verify paginated response characteristics
        assert response['success'] == True, "Paginated response should be successful"
        assert response['data'] == items, "Response data should match items"
        assert isinstance(response['data'], list), "Paginated data should be list"
        
        # Verify pagination metadata
        meta = response['meta']
        for key in ['page', 'per_page', 'total', 'pages']:
            assert key in meta, f"Pagination meta should include {key}"
            assert meta[key] == pagination[key], f"Pagination {key} should match input"
        
        # Verify standard meta fields
        assert 'timestamp' in meta, "Meta should include timestamp"
        assert 'status_code' in meta, "Meta should include status_code"
        assert meta['status_code'] == 200, "Paginated response should have status 200"
    
    @given(
        validation_errors=st.lists(error_detail_strategy, min_size=1, max_size=5)
    )
    @settings(max_examples=40)
    def test_property_validation_error_response_format(self, validation_errors):
        """
        Property: Validation Error Response Format
        
        For any validation error response, the format should clearly
        indicate validation failure with detailed error information.
        
        **Validates: Requirements 8.3**
        """
        # Format validation error response
        response = APIResponseFormatter.format_validation_error_response(validation_errors)
        
        # Validate response structure
        validation_result = APIResponseFormatter.validate_response_structure(response)
        
        # Response should be valid
        assert validation_result['valid'] == True, f"Validation error response should be valid: {validation_result['errors']}"
        
        # Verify validation error characteristics
        assert response['success'] == False, "Validation error should have success=False"
        assert response['message'] == 'Validation failed', "Should have validation failure message"
        assert response['errors'] == validation_errors, "Should include validation error details"
        
        # Verify validation-specific meta
        meta = response['meta']
        assert meta['status_code'] == 422, "Validation error should have status 422"
        assert meta['error_code'] == 'VALIDATION_ERROR', "Should have validation error code"
        
        # Verify error detail structure
        for error in response['errors']:
            assert 'field' in error, "Validation error should specify field"
            assert 'message' in error, "Validation error should have message"
            assert 'code' in error, "Validation error should have code"
    
    @given(
        responses=st.lists(
            st.one_of(
                st.builds(lambda d, m: APIResponseFormatter.format_success_response(d, m), 
                         user_data_strategy, st.text(min_size=1, max_size=100)),
                st.builds(lambda m, e: APIResponseFormatter.format_error_response(m, e),
                         st.text(min_size=1, max_size=100), st.lists(error_detail_strategy, max_size=3))
            ),
            min_size=2,
            max_size=5
        )
    )
    @settings(max_examples=30)
    def test_property_response_format_uniformity(self, responses):
        """
        Property: Response Format Uniformity
        
        For any set of API responses (success or error), all should
        follow the same structural format and validation rules.
        
        **Validates: Requirements 8.3**
        """
        # Validate all responses
        for i, response in enumerate(responses):
            validation_result = APIResponseFormatter.validate_response_structure(response)
            
            assert validation_result['valid'] == True, (
                f"Response {i} should be valid: {validation_result['errors']}"
            )
            
            # Verify all responses have the same structure
            required_fields = ['success', 'data', 'message', 'errors', 'meta']
            for field in required_fields:
                assert field in response, f"Response {i} should have field {field}"
            
            # Verify field types are consistent
            assert isinstance(response['success'], bool), f"Response {i} success should be bool"
            assert isinstance(response['message'], str), f"Response {i} message should be string"
            assert isinstance(response['errors'], list), f"Response {i} errors should be list"
            assert isinstance(response['meta'], dict), f"Response {i} meta should be dict"
    
    @given(
        raw_response=st.dictionaries(
            keys=st.sampled_from(['success', 'data', 'message', 'errors', 'meta', 'status', 'result']),
            values=st.one_of(
                st.booleans(),
                st.text(min_size=0, max_size=100),
                st.lists(st.text(min_size=1, max_size=50), max_size=3),
                st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=50), max_size=3)
            ),
            min_size=1,
            max_size=7
        )
    )
    @settings(max_examples=40)
    def test_property_response_normalization(self, raw_response):
        """
        Property: Response Normalization
        
        For any raw response dictionary, normalization should convert
        it to the standard format while preserving data integrity.
        
        **Validates: Requirements 8.3**
        """
        # Normalize response
        normalized = APIResponseFormatter.normalize_response(raw_response)
        
        # Validate normalized response
        validation_result = APIResponseFormatter.validate_response_structure(normalized)
        
        # Normalized response should be valid
        assert validation_result['valid'] == True, (
            f"Normalized response should be valid: {validation_result['errors']}"
        )
        
        # Verify all required fields are present
        required_fields = ['success', 'data', 'message', 'errors', 'meta']
        for field in required_fields:
            assert field in normalized, f"Normalized response should have {field}"
        
        # Verify data preservation where possible
        if 'success' in raw_response:
            assert normalized['success'] == raw_response['success'], "Success flag should be preserved"
        
        if 'data' in raw_response:
            assert normalized['data'] == raw_response['data'], "Data should be preserved"
        
        if 'message' in raw_response:
            assert normalized['message'] == raw_response['message'], "Message should be preserved"
        
        # Verify meta includes required fields
        assert 'timestamp' in normalized['meta'], "Normalized meta should include timestamp"
        assert 'status_code' in normalized['meta'], "Normalized meta should include status_code"
    
    @given(
        response_data=st.one_of(user_data_strategy, project_data_strategy),
        multiple_formats=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=25)
    def test_property_response_formatting_consistency(self, response_data, multiple_formats):
        """
        Property: Response Formatting Consistency
        
        For any data, multiple formatting operations should produce
        identical results, ensuring consistency across API endpoints.
        
        **Validates: Requirements 8.3**
        """
        # Format the same data multiple times
        responses = []
        for _ in range(multiple_formats):
            response = APIResponseFormatter.format_success_response(response_data)
            responses.append(response)
        
        # All responses should be identical (except timestamps)
        first_response = responses[0]
        for i, response in enumerate(responses[1:], 1):
            assert response['success'] == first_response['success'], f"Success consistency failed at {i}"
            assert response['data'] == first_response['data'], f"Data consistency failed at {i}"
            assert response['message'] == first_response['message'], f"Message consistency failed at {i}"
            assert response['errors'] == first_response['errors'], f"Errors consistency failed at {i}"
            
            # Meta should be consistent except for timestamp
            for key, value in first_response['meta'].items():
                if key != 'timestamp':  # Timestamps may differ slightly
                    assert response['meta'][key] == value, f"Meta {key} consistency failed at {i}"
    
    @given(
        success_data=user_data_strategy,
        error_message=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=30)
    def test_property_success_error_response_distinction(self, success_data, error_message):
        """
        Property: Success/Error Response Distinction
        
        Success and error responses should be clearly distinguishable
        while maintaining the same structural format.
        
        **Validates: Requirements 8.3**
        """
        # Create success and error responses
        success_response = APIResponseFormatter.format_success_response(success_data)
        error_response = APIResponseFormatter.format_error_response(error_message)
        
        # Both should be valid
        success_validation = APIResponseFormatter.validate_response_structure(success_response)
        error_validation = APIResponseFormatter.validate_response_structure(error_response)
        
        assert success_validation['valid'] == True, "Success response should be valid"
        assert error_validation['valid'] == True, "Error response should be valid"
        
        # Should have same structure but different values
        assert success_response['success'] == True, "Success response should have success=True"
        assert error_response['success'] == False, "Error response should have success=False"
        
        assert success_response['data'] == success_data, "Success response should have data"
        assert error_response['data'] is None, "Error response should have data=None"
        
        assert len(success_response['errors']) == 0, "Success response should have no errors"
        assert error_response['message'] == error_message, "Error response should have error message"
        
        # Both should have meta with different status codes
        assert success_response['meta']['status_code'] == 200, "Success should have status 200"
        assert error_response['meta']['status_code'] == 400, "Error should have status 400"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])