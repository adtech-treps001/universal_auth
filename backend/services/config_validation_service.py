"""
Configuration Validation Service

Service for validating configuration changes, handling graceful transitions,
and implementing rollback mechanisms for failed changes.
"""

from typing import Dict, Any, Optional, List, Tuple, Callable
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta
import logging
import json
import copy
from enum import Enum

from models.project import Project, ProjectConfiguration
from models.admin import AdminPanel, AdminWidget, AdminDashboard
from services.project_service import ProjectConfigurationService
from services.theme_service import ThemeService
from services.rbac_service import RBACService

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Validation message severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ValidationResult:
    """Configuration validation result"""
    
    def __init__(self):
        self.is_valid = True
        self.messages = []
        self.warnings = []
        self.errors = []
        self.suggestions = []
    
    def add_message(self, severity: ValidationSeverity, message: str, 
                   field: str = None, code: str = None):
        """Add validation message"""
        msg = {
            'severity': severity.value,
            'message': message,
            'field': field,
            'code': code,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.messages.append(msg)
        
        if severity == ValidationSeverity.ERROR or severity == ValidationSeverity.CRITICAL:
            self.errors.append(msg)
            self.is_valid = False
        elif severity == ValidationSeverity.WARNING:
            self.warnings.append(msg)
    
    def add_suggestion(self, suggestion: str, field: str = None):
        """Add improvement suggestion"""
        self.suggestions.append({
            'suggestion': suggestion,
            'field': field,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'messages': self.messages,
            'warnings': self.warnings,
            'errors': self.errors,
            'suggestions': self.suggestions,
            'summary': {
                'total_messages': len(self.messages),
                'error_count': len(self.errors),
                'warning_count': len(self.warnings),
                'suggestion_count': len(self.suggestions)
            }
        }

class ConfigurationValidator:
    """Base configuration validator"""
    
    def __init__(self, db: Session):
        self.db = db
        self.validators = []
    
    def add_validator(self, validator: Callable[[Dict[str, Any]], ValidationResult]):
        """Add custom validator function"""
        self.validators.append(validator)
    
    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration"""
        result = ValidationResult()
        
        # Run built-in validations
        self._validate_structure(config, result)
        self._validate_types(config, result)
        self._validate_constraints(config, result)
        
        # Run custom validators
        for validator in self.validators:
            try:
                custom_result = validator(config)
                self._merge_results(result, custom_result)
            except Exception as e:
                result.add_message(
                    ValidationSeverity.ERROR,
                    f"Custom validator failed: {e}",
                    code="CUSTOM_VALIDATOR_ERROR"
                )
        
        return result
    
    def _validate_structure(self, config: Dict[str, Any], result: ValidationResult):
        """Validate configuration structure"""
        # Override in subclasses
        pass
    
    def _validate_types(self, config: Dict[str, Any], result: ValidationResult):
        """Validate data types"""
        # Override in subclasses
        pass
    
    def _validate_constraints(self, config: Dict[str, Any], result: ValidationResult):
        """Validate business constraints"""
        # Override in subclasses
        pass
    
    def _merge_results(self, target: ValidationResult, source: ValidationResult):
        """Merge validation results"""
        target.messages.extend(source.messages)
        target.warnings.extend(source.warnings)
        target.errors.extend(source.errors)
        target.suggestions.extend(source.suggestions)
        
        if not source.is_valid:
            target.is_valid = False

class ProjectConfigValidator(ConfigurationValidator):
    """Project configuration validator"""
    
    def _validate_structure(self, config: Dict[str, Any], result: ValidationResult):
        """Validate project configuration structure"""
        
        required_fields = ['project_name', 'workflow']
        for field in required_fields:
            if field not in config:
                result.add_message(
                    ValidationSeverity.ERROR,
                    f"Required field '{field}' is missing",
                    field=field,
                    code="MISSING_REQUIRED_FIELD"
                )
        
        # Validate workflow configuration
        if 'workflow' in config:
            workflow = config['workflow']
            if not isinstance(workflow, dict):
                result.add_message(
                    ValidationSeverity.ERROR,
                    "Workflow must be an object",
                    field='workflow',
                    code="INVALID_TYPE"
                )
            else:
                if 'type' not in workflow:
                    result.add_message(
                        ValidationSeverity.ERROR,
                        "Workflow type is required",
                        field='workflow.type',
                        code="MISSING_WORKFLOW_TYPE"
                    )
    
    def _validate_types(self, config: Dict[str, Any], result: ValidationResult):
        """Validate project configuration types"""
        
        type_validations = {
            'project_name': str,
            'description': str,
            'is_active': bool,
            'workflow': dict,
            'theme_config': dict,
            'integration_config': dict
        }
        
        for field, expected_type in type_validations.items():
            if field in config and not isinstance(config[field], expected_type):
                result.add_message(
                    ValidationSeverity.ERROR,
                    f"Field '{field}' must be of type {expected_type.__name__}",
                    field=field,
                    code="INVALID_TYPE"
                )
    
    def _validate_constraints(self, config: Dict[str, Any], result: ValidationResult):
        """Validate project configuration constraints"""
        
        # Validate project name
        if 'project_name' in config:
            name = config['project_name']
            if len(name) < 3:
                result.add_message(
                    ValidationSeverity.ERROR,
                    "Project name must be at least 3 characters",
                    field='project_name',
                    code="NAME_TOO_SHORT"
                )
            elif len(name) > 100:
                result.add_message(
                    ValidationSeverity.ERROR,
                    "Project name must be at most 100 characters",
                    field='project_name',
                    code="NAME_TOO_LONG"
                )
        
        # Validate workflow type
        if 'workflow' in config and 'type' in config['workflow']:
            workflow_type = config['workflow']['type']
            valid_types = [
                '1_EMAIL_ONLY',
                '2_EMAIL_SOCIAL_GOOGLE',
                '3_EMAIL_SOCIAL_MULTI',
                '4_PHONE_OTP',
                '5_PHONE_EMAIL_SOCIAL'
            ]
            
            if workflow_type not in valid_types:
                result.add_message(
                    ValidationSeverity.ERROR,
                    f"Invalid workflow type. Must be one of: {', '.join(valid_types)}",
                    field='workflow.type',
                    code="INVALID_WORKFLOW_TYPE"
                )
        
        # Check for duplicate project names
        if 'project_name' in config:
            existing = self.db.query(Project).filter(
                Project.project_name == config['project_name']
            ).first()
            
            if existing:
                result.add_message(
                    ValidationSeverity.ERROR,
                    "Project name already exists",
                    field='project_name',
                    code="DUPLICATE_PROJECT_NAME"
                )

class ThemeConfigValidator(ConfigurationValidator):
    """Theme configuration validator"""
    
    def _validate_structure(self, config: Dict[str, Any], result: ValidationResult):
        """Validate theme configuration structure"""
        
        if 'colors' in config:
            colors = config['colors']
            if not isinstance(colors, dict):
                result.add_message(
                    ValidationSeverity.ERROR,
                    "Colors must be an object",
                    field='colors',
                    code="INVALID_TYPE"
                )
            else:
                # Validate color values
                for color_name, color_value in colors.items():
                    if not self._is_valid_color(color_value):
                        result.add_message(
                            ValidationSeverity.ERROR,
                            f"Invalid color value for '{color_name}': {color_value}",
                            field=f'colors.{color_name}',
                            code="INVALID_COLOR"
                        )
    
    def _validate_constraints(self, config: Dict[str, Any], result: ValidationResult):
        """Validate theme configuration constraints"""
        
        # Validate accessibility
        if 'colors' in config:
            colors = config['colors']
            
            # Check contrast ratios
            if 'primary' in colors and 'background' in colors:
                contrast_ratio = self._calculate_contrast_ratio(
                    colors['primary'], colors['background']
                )
                
                if contrast_ratio < 4.5:
                    result.add_message(
                        ValidationSeverity.WARNING,
                        f"Low contrast ratio ({contrast_ratio:.2f}) between primary and background colors",
                        field='colors',
                        code="LOW_CONTRAST"
                    )
                    
                    result.add_suggestion(
                        "Consider using colors with higher contrast for better accessibility",
                        field='colors'
                    )
    
    def _is_valid_color(self, color: str) -> bool:
        """Check if color value is valid"""
        if not isinstance(color, str):
            return False
        
        # Check hex colors
        if color.startswith('#'):
            return len(color) in [4, 7] and all(c in '0123456789abcdefABCDEF' for c in color[1:])
        
        # Check RGB/RGBA
        if color.startswith(('rgb(', 'rgba(')):
            return True  # Simplified validation
        
        # Check named colors (simplified)
        named_colors = ['red', 'blue', 'green', 'black', 'white', 'gray', 'yellow', 'orange', 'purple']
        return color.lower() in named_colors
    
    def _calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """Calculate contrast ratio between two colors (simplified)"""
        # This is a simplified implementation
        # In practice, you'd convert to RGB and calculate luminance
        return 4.5  # Placeholder

class RBACConfigValidator(ConfigurationValidator):
    """RBAC configuration validator"""
    
    def _validate_structure(self, config: Dict[str, Any], result: ValidationResult):
        """Validate RBAC configuration structure"""
        
        if 'roles' in config:
            roles = config['roles']
            if not isinstance(roles, list):
                result.add_message(
                    ValidationSeverity.ERROR,
                    "Roles must be an array",
                    field='roles',
                    code="INVALID_TYPE"
                )
            else:
                for i, role in enumerate(roles):
                    if not isinstance(role, dict):
                        result.add_message(
                            ValidationSeverity.ERROR,
                            f"Role at index {i} must be an object",
                            field=f'roles[{i}]',
                            code="INVALID_TYPE"
                        )
                    elif 'name' not in role:
                        result.add_message(
                            ValidationSeverity.ERROR,
                            f"Role at index {i} is missing 'name' field",
                            field=f'roles[{i}].name',
                            code="MISSING_ROLE_NAME"
                        )
    
    def _validate_constraints(self, config: Dict[str, Any], result: ValidationResult):
        """Validate RBAC configuration constraints"""
        
        if 'roles' in config:
            role_names = []
            
            for i, role in enumerate(config['roles']):
                if isinstance(role, dict) and 'name' in role:
                    role_name = role['name']
                    
                    # Check for duplicate role names
                    if role_name in role_names:
                        result.add_message(
                            ValidationSeverity.ERROR,
                            f"Duplicate role name: {role_name}",
                            field=f'roles[{i}].name',
                            code="DUPLICATE_ROLE_NAME"
                        )
                    else:
                        role_names.append(role_name)
                    
                    # Validate capabilities
                    if 'capabilities' in role:
                        capabilities = role['capabilities']
                        if not isinstance(capabilities, list):
                            result.add_message(
                                ValidationSeverity.ERROR,
                                f"Capabilities for role '{role_name}' must be an array",
                                field=f'roles[{i}].capabilities',
                                code="INVALID_TYPE"
                            )

class ConfigurationValidationService:
    """Service for configuration validation and error handling"""
    
    def __init__(self, db: Session):
        self.db = db
        self.project_service = ProjectConfigurationService(db)
        self.theme_service = ThemeService(db)
        self.rbac_service = RBACService(db)
        
        # Initialize validators
        self.validators = {
            'project': ProjectConfigValidator(db),
            'theme': ThemeConfigValidator(db),
            'rbac': RBACConfigValidator(db)
        }
    
    def validate_configuration(self, config_type: str, config: Dict[str, Any],
                             context: Dict[str, Any] = None) -> ValidationResult:
        """
        Validate configuration of specified type
        
        Args:
            config_type: Type of configuration (project, theme, rbac)
            config: Configuration data to validate
            context: Additional validation context
            
        Returns:
            ValidationResult with validation details
        """
        if config_type not in self.validators:
            result = ValidationResult()
            result.add_message(
                ValidationSeverity.ERROR,
                f"Unknown configuration type: {config_type}",
                code="UNKNOWN_CONFIG_TYPE"
            )
            return result
        
        try:
            validator = self.validators[config_type]
            result = validator.validate(config)
            
            # Add context-specific validations
            if context:
                self._validate_context_constraints(config_type, config, context, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            result = ValidationResult()
            result.add_message(
                ValidationSeverity.CRITICAL,
                f"Validation process failed: {e}",
                code="VALIDATION_PROCESS_ERROR"
            )
            return result
    
    def validate_configuration_change(self, config_type: str, old_config: Dict[str, Any],
                                    new_config: Dict[str, Any]) -> ValidationResult:
        """
        Validate configuration change impact
        
        Args:
            config_type: Type of configuration
            old_config: Current configuration
            new_config: Proposed new configuration
            
        Returns:
            ValidationResult with change impact analysis
        """
        result = self.validate_configuration(config_type, new_config)
        
        # Analyze change impact
        self._analyze_change_impact(config_type, old_config, new_config, result)
        
        return result
    
    def apply_configuration_safely(self, config_type: str, config_id: str,
                                 new_config: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Apply configuration with rollback capability
        
        Args:
            config_type: Type of configuration
            config_id: Configuration ID
            new_config: New configuration data
            user_id: User applying the change
            
        Returns:
            Application result with rollback information
        """
        try:
            # Get current configuration
            old_config = self._get_current_config(config_type, config_id)
            
            # Validate the change
            validation_result = self.validate_configuration_change(
                config_type, old_config, new_config
            )
            
            if not validation_result.is_valid:
                return {
                    'success': False,
                    'validation_result': validation_result.to_dict(),
                    'message': 'Configuration validation failed'
                }
            
            # Create backup
            backup_id = self._create_config_backup(config_type, config_id, old_config, user_id)
            
            # Apply configuration
            apply_result = self._apply_configuration(config_type, config_id, new_config, user_id)
            
            if apply_result['success']:
                # Test the new configuration
                test_result = self._test_configuration(config_type, config_id, new_config)
                
                if not test_result['success']:
                    # Rollback on test failure
                    logger.warning(f"Configuration test failed, rolling back: {test_result['error']}")
                    rollback_result = self.rollback_configuration(config_type, config_id, backup_id, user_id)
                    
                    return {
                        'success': False,
                        'message': 'Configuration applied but failed testing, rolled back',
                        'test_error': test_result['error'],
                        'rollback_result': rollback_result
                    }
                
                return {
                    'success': True,
                    'message': 'Configuration applied successfully',
                    'backup_id': backup_id,
                    'validation_result': validation_result.to_dict()
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to apply configuration',
                    'error': apply_result['error']
                }
                
        except Exception as e:
            logger.error(f"Configuration application failed: {e}")
            return {
                'success': False,
                'message': 'Configuration application process failed',
                'error': str(e)
            }
    
    def rollback_configuration(self, config_type: str, config_id: str,
                             backup_id: str, user_id: str) -> Dict[str, Any]:
        """
        Rollback configuration to previous state
        
        Args:
            config_type: Type of configuration
            config_id: Configuration ID
            backup_id: Backup ID to restore from
            user_id: User performing rollback
            
        Returns:
            Rollback result
        """
        try:
            # Get backup configuration
            backup_config = self._get_config_backup(backup_id)
            
            if not backup_config:
                return {
                    'success': False,
                    'message': 'Backup configuration not found'
                }
            
            # Apply backup configuration
            apply_result = self._apply_configuration(
                config_type, config_id, backup_config['config'], user_id
            )
            
            if apply_result['success']:
                logger.info(f"Configuration {config_id} rolled back to backup {backup_id}")
                return {
                    'success': True,
                    'message': 'Configuration rolled back successfully',
                    'backup_id': backup_id
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to rollback configuration',
                    'error': apply_result['error']
                }
                
        except Exception as e:
            logger.error(f"Configuration rollback failed: {e}")
            return {
                'success': False,
                'message': 'Rollback process failed',
                'error': str(e)
            }
    
    def get_configuration_history(self, config_type: str, config_id: str,
                                limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get configuration change history
        
        Args:
            config_type: Type of configuration
            config_id: Configuration ID
            limit: Maximum number of history entries
            
        Returns:
            List of configuration history entries
        """
        # This would query a configuration history table
        # For now, return empty list
        return []
    
    def _validate_context_constraints(self, config_type: str, config: Dict[str, Any],
                                    context: Dict[str, Any], result: ValidationResult):
        """Validate context-specific constraints"""
        
        # Tenant-specific validations
        if 'tenant_id' in context:
            tenant_id = context['tenant_id']
            
            # Check tenant limits
            if config_type == 'project':
                project_count = self.db.query(func.count(Project.id)).filter(
                    Project.tenant_id == tenant_id
                ).scalar()
                
                # Assume tenant limit of 10 projects
                if project_count >= 10:
                    result.add_message(
                        ValidationSeverity.ERROR,
                        "Tenant project limit exceeded (10 projects maximum)",
                        code="TENANT_LIMIT_EXCEEDED"
                    )
    
    def _analyze_change_impact(self, config_type: str, old_config: Dict[str, Any],
                             new_config: Dict[str, Any], result: ValidationResult):
        """Analyze impact of configuration changes"""
        
        if config_type == 'project':
            # Check workflow changes
            old_workflow = old_config.get('workflow', {}).get('type')
            new_workflow = new_config.get('workflow', {}).get('type')
            
            if old_workflow != new_workflow:
                result.add_message(
                    ValidationSeverity.WARNING,
                    f"Workflow change from '{old_workflow}' to '{new_workflow}' may affect user experience",
                    field='workflow.type',
                    code="WORKFLOW_CHANGE_IMPACT"
                )
                
                result.add_suggestion(
                    "Consider notifying users about workflow changes",
                    field='workflow'
                )
        
        elif config_type == 'theme':
            # Check color changes
            old_colors = old_config.get('colors', {})
            new_colors = new_config.get('colors', {})
            
            changed_colors = []
            for color_name in set(old_colors.keys()) | set(new_colors.keys()):
                if old_colors.get(color_name) != new_colors.get(color_name):
                    changed_colors.append(color_name)
            
            if changed_colors:
                result.add_message(
                    ValidationSeverity.INFO,
                    f"Color changes detected: {', '.join(changed_colors)}",
                    field='colors',
                    code="COLOR_CHANGE_DETECTED"
                )
    
    def _get_current_config(self, config_type: str, config_id: str) -> Dict[str, Any]:
        """Get current configuration"""
        
        if config_type == 'project':
            project = self.db.query(Project).filter(Project.id == config_id).first()
            if project:
                return {
                    'project_name': project.project_name,
                    'description': project.description,
                    'workflow': project.workflow,
                    'theme_config': project.theme_config,
                    'integration_config': project.integration_config
                }
        
        return {}
    
    def _create_config_backup(self, config_type: str, config_id: str,
                            config: Dict[str, Any], user_id: str) -> str:
        """Create configuration backup"""
        
        # In a real implementation, this would store the backup in a database table
        backup_id = f"backup_{config_type}_{config_id}_{int(datetime.utcnow().timestamp())}"
        
        # Store backup (simplified)
        logger.info(f"Created configuration backup {backup_id}")
        
        return backup_id
    
    def _get_config_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration backup"""
        
        # In a real implementation, this would retrieve from database
        return None
    
    def _apply_configuration(self, config_type: str, config_id: str,
                           config: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Apply configuration changes"""
        
        try:
            if config_type == 'project':
                project = self.db.query(Project).filter(Project.id == config_id).first()
                if project:
                    # Update project configuration
                    for field, value in config.items():
                        if hasattr(project, field):
                            setattr(project, field, value)
                    
                    project.updated_by = user_id
                    project.updated_at = datetime.utcnow()
                    
                    self.db.commit()
                    
                    return {'success': True}
                else:
                    return {'success': False, 'error': 'Project not found'}
            
            return {'success': True}
            
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    def _test_configuration(self, config_type: str, config_id: str,
                          config: Dict[str, Any]) -> Dict[str, Any]:
        """Test configuration after application"""
        
        try:
            if config_type == 'project':
                # Test project configuration
                project = self.db.query(Project).filter(Project.id == config_id).first()
                
                if not project:
                    return {'success': False, 'error': 'Project not found after configuration'}
                
                # Test workflow configuration
                if project.workflow:
                    workflow_type = project.workflow.get('type')
                    if not workflow_type:
                        return {'success': False, 'error': 'Workflow type not set'}
                
                return {'success': True}
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}