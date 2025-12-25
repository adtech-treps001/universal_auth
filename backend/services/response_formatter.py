"""
API Response Format Standardization Service

This module provides consistent API response formatting across all endpoints,
including success responses, error responses, pagination, and validation errors.

**Implements: Requirements 8.3, 8.5**
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)

class ResponseStatus(Enum):
    """Standard response status codes"""
    SUCCESS = "success"
    ERROR = "error"
    VALIDATION_ERROR = "validation_error"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"

@dataclass
class ErrorDetail:
    """Structured error detail"""
    field: Optional[str] = None
    message: str = ""
    code: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class PaginationMeta:
    """Pagination metadata"""
    page: int
    per_page: int
    total: int
    pages: int
    has_next: bool = False
    has_prev: bool = False
    next_page: Optional[int] = None
    prev_page: Optional[int] = None
    
    def __post_init__(self):
        self.pages = max(1, (self.total + self.per_page - 1) // self.per_page)
        self.has_next = self.page < self.pages
        self.has_prev = self.page > 1
        self.next_page = self.page + 1 if self.has_next else None
        self.prev_page = self.page - 1 if self.has_prev else None

class ResponseFormatter:
    """Centralized API response formatter"""
    
    # Standard HTTP status code mappings
    STATUS_CODE_MAP = {
        ResponseStatus.SUCCESS: 200,
        ResponseStatus.ERROR: 400,
        ResponseStatus.VALIDATION_ERROR: 422,
        ResponseStatus.UNAUTHORIZED: 401,
        ResponseStatus.FORBIDDEN: 403,
        ResponseStatus.NOT_FOUND: 404,
        ResponseStatus.RATE_LIMITED: 429
    }
    
    # Standard error codes
    ERROR_CODES = {
        400: 'BAD_REQUEST',
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        422: 'VALIDATION_ERROR',
        429: 'RATE_LIMITED',
        500: 'INTERNAL_ERROR'
    }
    
    # Standard success messages
    SUCCESS_MESSAGES = {
        200: 'Request successful',
        201: 'Resource created successfully',
        202: 'Request accepted for processing',
        204: 'Request successful, no content'
    }
    
    @staticmethod
    def success(data: Any = None, message: str = None, status_code: int = 200,
               meta: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Format successful response
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            meta: Additional metadata
            
        Returns:
            Formatted success response
        """
        if message is None:
            message = ResponseFormatter.SUCCESS_MESSAGES.get(status_code, 'Request successful')
        
        response = {
            'success': True,
            'status': ResponseStatus.SUCCESS.value,
            'data': data,
            'message': message,
            'errors': [],
            'meta': ResponseFormatter._build_meta(status_code, meta)
        }
        
        logger.debug(f"Success response: {status_code} - {message}")
        return response
    
    @staticmethod
    def error(message: str, status_code: int = 400, error_code: str = None,
             errors: List[ErrorDetail] = None, meta: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Format error response
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Application-specific error code
            errors: List of detailed errors
            meta: Additional metadata
            
        Returns:
            Formatted error response
        """
        if error_code is None:
            error_code = ResponseFormatter.ERROR_CODES.get(status_code, 'UNKNOWN_ERROR')
        
        # Convert error details to dictionaries
        error_list = []
        if errors:
            error_list = [error.to_dict() if isinstance(error, ErrorDetail) else error for error in errors]
        
        response = {
            'success': False,
            'status': ResponseFormatter._get_status_from_code(status_code).value,
            'data': None,
            'message': message,
            'errors': error_list,
            'meta': ResponseFormatter._build_meta(status_code, meta, error_code)
        }
        
        logger.warning(f"Error response: {status_code} - {message}")
        return response
    
    @staticmethod
    def validation_error(message: str = "Validation failed", 
                        validation_errors: List[ErrorDetail] = None) -> Dict[str, Any]:
        """
        Format validation error response
        
        Args:
            message: Validation error message
            validation_errors: List of field validation errors
            
        Returns:
            Formatted validation error response
        """
        return ResponseFormatter.error(
            message=message,
            status_code=422,
            error_code='VALIDATION_ERROR',
            errors=validation_errors or []
        )
    
    @staticmethod
    def unauthorized(message: str = "Authentication required") -> Dict[str, Any]:
        """
        Format unauthorized response
        
        Args:
            message: Unauthorized message
            
        Returns:
            Formatted unauthorized response
        """
        return ResponseFormatter.error(
            message=message,
            status_code=401,
            error_code='UNAUTHORIZED'
        )
    
    @staticmethod
    def forbidden(message: str = "Access denied") -> Dict[str, Any]:
        """
        Format forbidden response
        
        Args:
            message: Forbidden message
            
        Returns:
            Formatted forbidden response
        """
        return ResponseFormatter.error(
            message=message,
            status_code=403,
            error_code='FORBIDDEN'
        )
    
    @staticmethod
    def not_found(message: str = "Resource not found") -> Dict[str, Any]:
        """
        Format not found response
        
        Args:
            message: Not found message
            
        Returns:
            Formatted not found response
        """
        return ResponseFormatter.error(
            message=message,
            status_code=404,
            error_code='NOT_FOUND'
        )
    
    @staticmethod
    def rate_limited(message: str = "Rate limit exceeded", 
                    retry_after: int = None) -> Dict[str, Any]:
        """
        Format rate limited response
        
        Args:
            message: Rate limit message
            retry_after: Seconds until retry is allowed
            
        Returns:
            Formatted rate limited response
        """
        meta = {}
        if retry_after:
            meta['retry_after'] = retry_after
        
        return ResponseFormatter.error(
            message=message,
            status_code=429,
            error_code='RATE_LIMITED',
            meta=meta
        )
    
    @staticmethod
    def paginated(items: List[Any], pagination: PaginationMeta, 
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
        meta = asdict(pagination)
        meta.update(ResponseFormatter._build_meta(200))
        
        return {
            'success': True,
            'status': ResponseStatus.SUCCESS.value,
            'data': items,
            'message': message or f"Retrieved {len(items)} items",
            'errors': [],
            'meta': meta
        }
    
    @staticmethod
    def created(data: Any = None, message: str = None, 
               location: str = None) -> Dict[str, Any]:
        """
        Format resource created response
        
        Args:
            data: Created resource data
            message: Success message
            location: Location of created resource
            
        Returns:
            Formatted created response
        """
        meta = {}
        if location:
            meta['location'] = location
        
        return ResponseFormatter.success(
            data=data,
            message=message or "Resource created successfully",
            status_code=201,
            meta=meta
        )
    
    @staticmethod
    def accepted(message: str = None, task_id: str = None) -> Dict[str, Any]:
        """
        Format accepted for processing response
        
        Args:
            message: Acceptance message
            task_id: Task identifier for tracking
            
        Returns:
            Formatted accepted response
        """
        meta = {}
        if task_id:
            meta['task_id'] = task_id
        
        return ResponseFormatter.success(
            message=message or "Request accepted for processing",
            status_code=202,
            meta=meta
        )
    
    @staticmethod
    def no_content() -> Dict[str, Any]:
        """
        Format no content response
        
        Returns:
            Formatted no content response
        """
        return ResponseFormatter.success(
            message="Request successful, no content",
            status_code=204
        )
    
    @staticmethod
    def _build_meta(status_code: int, additional_meta: Dict[str, Any] = None,
                   error_code: str = None) -> Dict[str, Any]:
        """Build response metadata"""
        meta = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'status_code': status_code
        }
        
        if error_code:
            meta['error_code'] = error_code
        
        if additional_meta:
            meta.update(additional_meta)
        
        return meta
    
    @staticmethod
    def _get_status_from_code(status_code: int) -> ResponseStatus:
        """Get response status from HTTP status code"""
        status_map = {
            200: ResponseStatus.SUCCESS,
            201: ResponseStatus.SUCCESS,
            202: ResponseStatus.SUCCESS,
            204: ResponseStatus.SUCCESS,
            400: ResponseStatus.ERROR,
            401: ResponseStatus.UNAUTHORIZED,
            403: ResponseStatus.FORBIDDEN,
            404: ResponseStatus.NOT_FOUND,
            422: ResponseStatus.VALIDATION_ERROR,
            429: ResponseStatus.RATE_LIMITED
        }
        
        return status_map.get(status_code, ResponseStatus.ERROR)

class ValidationErrorBuilder:
    """Helper class for building validation errors"""
    
    def __init__(self):
        self.errors: List[ErrorDetail] = []
    
    def add_field_error(self, field: str, message: str, code: str = "INVALID") -> 'ValidationErrorBuilder':
        """Add field validation error"""
        self.errors.append(ErrorDetail(field=field, message=message, code=code))
        return self
    
    def add_general_error(self, message: str, code: str = "VALIDATION_ERROR") -> 'ValidationErrorBuilder':
        """Add general validation error"""
        self.errors.append(ErrorDetail(message=message, code=code))
        return self
    
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    def build_response(self, message: str = "Validation failed") -> Dict[str, Any]:
        """Build validation error response"""
        return ResponseFormatter.validation_error(message, self.errors)
    
    def get_errors(self) -> List[ErrorDetail]:
        """Get list of errors"""
        return self.errors.copy()

class RateLimitInfo:
    """Rate limit information"""
    
    def __init__(self, limit: int, remaining: int, reset_time: datetime):
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers"""
        return {
            'X-RateLimit-Limit': str(self.limit),
            'X-RateLimit-Remaining': str(self.remaining),
            'X-RateLimit-Reset': str(int(self.reset_time.timestamp()))
        }
    
    def to_meta(self) -> Dict[str, Any]:
        """Convert to response metadata"""
        return {
            'rate_limit': {
                'limit': self.limit,
                'remaining': self.remaining,
                'reset_time': self.reset_time.isoformat() + 'Z'
            }
        }

class ResponseValidator:
    """Validate response format consistency"""
    
    REQUIRED_FIELDS = ['success', 'status', 'data', 'message', 'errors', 'meta']
    
    @staticmethod
    def validate_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate response format
        
        Args:
            response: Response dictionary to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field in ResponseValidator.REQUIRED_FIELDS:
            if field not in response:
                errors.append(f"Missing required field: {field}")
        
        # Validate field types
        if 'success' in response and not isinstance(response['success'], bool):
            errors.append("Field 'success' must be boolean")
        
        if 'status' in response and not isinstance(response['status'], str):
            errors.append("Field 'status' must be string")
        
        if 'message' in response and not isinstance(response['message'], str):
            errors.append("Field 'message' must be string")
        
        if 'errors' in response and not isinstance(response['errors'], list):
            errors.append("Field 'errors' must be list")
        
        if 'meta' in response and not isinstance(response['meta'], dict):
            errors.append("Field 'meta' must be dictionary")
        
        # Validate meta structure
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
        
        # Validate success/error consistency
        if 'success' in response and 'data' in response:
            if response['success'] and response['data'] is None:
                warnings.append("Success response with null data may be unexpected")
            elif not response['success'] and response['data'] is not None:
                warnings.append("Error response with non-null data may be unexpected")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

# Utility functions for common response patterns
def success_with_data(data: Any, message: str = None) -> Dict[str, Any]:
    """Quick success response with data"""
    return ResponseFormatter.success(data=data, message=message)

def error_with_message(message: str, status_code: int = 400) -> Dict[str, Any]:
    """Quick error response with message"""
    return ResponseFormatter.error(message=message, status_code=status_code)

def validation_errors_from_dict(errors_dict: Dict[str, str]) -> List[ErrorDetail]:
    """Convert dictionary of field errors to ErrorDetail list"""
    return [
        ErrorDetail(field=field, message=message, code="INVALID")
        for field, message in errors_dict.items()
    ]

def paginate_response(items: List[Any], page: int, per_page: int, 
                     total: int, message: str = None) -> Dict[str, Any]:
    """Quick paginated response"""
    pagination = PaginationMeta(
        page=page,
        per_page=per_page,
        total=total
    )
    return ResponseFormatter.paginated(items, pagination, message)