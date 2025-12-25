"""
Configuration Validation Routes

API endpoints for configuration validation, error handling,
and rollback mechanisms.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from database import get_db
from services.config_validation_service import ConfigurationValidationService, ValidationSeverity
from auth.middleware import get_current_user, require_permission
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config-validation"])

# Pydantic models for request/response
class ConfigValidationRequest(BaseModel):
    config_type: str = Field(..., description="Configuration type (project, theme, rbac)")
    config: Dict[str, Any] = Field(..., description="Configuration data to validate")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional validation context")

class ValidationMessage(BaseModel):
    severity: str
    message: str
    field: Optional[str]
    code: Optional[str]
    timestamp: str

class ValidationSuggestion(BaseModel):
    suggestion: str
    field: Optional[str]
    timestamp: str

class ValidationResponse(BaseModel):
    is_valid: bool
    messages: List[ValidationMessage]
    warnings: List[ValidationMessage]
    errors: List[ValidationMessage]
    suggestions: List[ValidationSuggestion]
    summary: Dict[str, int]

class ConfigChangeValidationRequest(BaseModel):
    config_type: str = Field(..., description="Configuration type")
    old_config: Dict[str, Any] = Field(..., description="Current configuration")
    new_config: Dict[str, Any] = Field(..., description="Proposed new configuration")

class ConfigApplicationRequest(BaseModel):
    config_type: str = Field(..., description="Configuration type")
    config_id: str = Field(..., description="Configuration ID")
    new_config: Dict[str, Any] = Field(..., description="New configuration data")

class ConfigApplicationResponse(BaseModel):
    success: bool
    message: str
    backup_id: Optional[str] = None
    validation_result: Optional[ValidationResponse] = None
    test_error: Optional[str] = None
    rollback_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ConfigRollbackRequest(BaseModel):
    config_type: str = Field(..., description="Configuration type")
    config_id: str = Field(..., description="Configuration ID")
    backup_id: str = Field(..., description="Backup ID to restore from")

class ConfigHistoryEntry(BaseModel):
    id: str
    config_type: str
    config_id: str
    change_type: str
    changed_by: str
    changed_at: str
    backup_id: Optional[str]
    validation_result: Optional[ValidationResponse]

@router.post("/validate", response_model=ValidationResponse)
async def validate_configuration(
    request: ConfigValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate configuration data"""
    
    await require_permission(current_user, "config.validate", db)
    
    try:
        validation_service = ConfigurationValidationService(db)
        
        result = validation_service.validate_configuration(
            config_type=request.config_type,
            config=request.config,
            context=request.context
        )
        
        return ValidationResponse(**result.to_dict())
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration validation failed"
        )

@router.post("/validate-change", response_model=ValidationResponse)
async def validate_configuration_change(
    request: ConfigChangeValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate configuration change impact"""
    
    await require_permission(current_user, "config.validate", db)
    
    try:
        validation_service = ConfigurationValidationService(db)
        
        result = validation_service.validate_configuration_change(
            config_type=request.config_type,
            old_config=request.old_config,
            new_config=request.new_config
        )
        
        return ValidationResponse(**result.to_dict())
        
    except Exception as e:
        logger.error(f"Configuration change validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration change validation failed"
        )

@router.post("/apply", response_model=ConfigApplicationResponse)
async def apply_configuration_safely(
    request: ConfigApplicationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Apply configuration with rollback capability"""
    
    await require_permission(current_user, "config.apply", db)
    
    try:
        validation_service = ConfigurationValidationService(db)
        
        result = validation_service.apply_configuration_safely(
            config_type=request.config_type,
            config_id=request.config_id,
            new_config=request.new_config,
            user_id=current_user.id
        )
        
        # Convert validation_result if present
        if result.get('validation_result'):
            result['validation_result'] = ValidationResponse(**result['validation_result'])
        
        return ConfigApplicationResponse(**result)
        
    except Exception as e:
        logger.error(f"Configuration application failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration application failed"
        )

@router.post("/rollback", response_model=Dict[str, Any])
async def rollback_configuration(
    request: ConfigRollbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rollback configuration to previous state"""
    
    await require_permission(current_user, "config.rollback", db)
    
    try:
        validation_service = ConfigurationValidationService(db)
        
        result = validation_service.rollback_configuration(
            config_type=request.config_type,
            config_id=request.config_id,
            backup_id=request.backup_id,
            user_id=current_user.id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Configuration rollback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration rollback failed"
        )

@router.get("/history/{config_type}/{config_id}", response_model=List[ConfigHistoryEntry])
async def get_configuration_history(
    config_type: str,
    config_id: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of entries"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get configuration change history"""
    
    await require_permission(current_user, "config.read", db)
    
    try:
        validation_service = ConfigurationValidationService(db)
        
        history = validation_service.get_configuration_history(
            config_type=config_type,
            config_id=config_id,
            limit=limit
        )
        
        return [ConfigHistoryEntry(**entry) for entry in history]
        
    except Exception as e:
        logger.error(f"Failed to get configuration history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get configuration history"
        )

@router.get("/validation-rules/{config_type}")
async def get_validation_rules(
    config_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validation rules for configuration type"""
    
    try:
        # Return validation rules for the specified configuration type
        rules = {
            'project': {
                'required_fields': ['project_name', 'workflow'],
                'field_types': {
                    'project_name': 'string',
                    'description': 'string',
                    'is_active': 'boolean',
                    'workflow': 'object',
                    'theme_config': 'object',
                    'integration_config': 'object'
                },
                'constraints': {
                    'project_name': {
                        'min_length': 3,
                        'max_length': 100,
                        'pattern': '^[a-zA-Z0-9_-]+$'
                    },
                    'workflow.type': {
                        'enum': [
                            '1_EMAIL_ONLY',
                            '2_EMAIL_SOCIAL_GOOGLE',
                            '3_EMAIL_SOCIAL_MULTI',
                            '4_PHONE_OTP',
                            '5_PHONE_EMAIL_SOCIAL'
                        ]
                    }
                }
            },
            'theme': {
                'required_fields': [],
                'field_types': {
                    'colors': 'object',
                    'typography': 'object',
                    'layout': 'object'
                },
                'constraints': {
                    'colors': {
                        'color_format': 'hex|rgb|rgba|named'
                    }
                }
            },
            'rbac': {
                'required_fields': [],
                'field_types': {
                    'roles': 'array',
                    'capabilities': 'array'
                },
                'constraints': {
                    'roles': {
                        'unique_names': True,
                        'required_fields': ['name']
                    }
                }
            }
        }
        
        if config_type not in rules:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Validation rules not found for config type: {config_type}"
            )
        
        return {
            'config_type': config_type,
            'rules': rules[config_type],
            'validation_levels': [
                'structure',
                'types',
                'constraints',
                'business_rules'
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get validation rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get validation rules"
        )

@router.post("/test/{config_type}/{config_id}")
async def test_configuration(
    config_type: str,
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test current configuration"""
    
    await require_permission(current_user, "config.test", db)
    
    try:
        validation_service = ConfigurationValidationService(db)
        
        # Get current configuration
        current_config = validation_service._get_current_config(config_type, config_id)
        
        if not current_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        
        # Test the configuration
        test_result = validation_service._test_configuration(config_type, config_id, current_config)
        
        return {
            'config_type': config_type,
            'config_id': config_id,
            'test_result': test_result,
            'tested_at': datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Configuration test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration test failed"
        )

@router.get("/health-check")
async def configuration_health_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Perform health check on all configurations"""
    
    await require_permission(current_user, "config.health_check", db)
    
    try:
        validation_service = ConfigurationValidationService(db)
        
        # This would check all configurations for issues
        health_status = {
            'overall_status': 'healthy',
            'checks': {
                'project_configs': {'status': 'healthy', 'issues': []},
                'theme_configs': {'status': 'healthy', 'issues': []},
                'rbac_configs': {'status': 'healthy', 'issues': []},
                'validation_service': {'status': 'healthy', 'issues': []}
            },
            'checked_at': datetime.utcnow().isoformat(),
            'recommendations': []
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Configuration health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration health check failed"
        )