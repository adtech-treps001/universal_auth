"""
Project Configuration Service

This service handles project-specific configurations, workflow selection,
and configuration inheritance logic.
"""

from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime
import json
import uuid
import logging

from models.project import (
    Project, ProjectConfiguration, ProjectWorkflow, ProjectTheme,
    ConfigurationTemplate, ProjectConfigurationHistory
)

logger = logging.getLogger(__name__)

class ProjectConfigurationService:
    """Service for managing project configurations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_project(self, name: str, slug: str, owner_id: str, 
                      tenant_id: str = None, description: str = None,
                      template_id: str = None) -> Project:
        """
        Create a new project with optional template
        
        Args:
            name: Project name
            slug: Unique project slug
            owner_id: User ID of project owner
            tenant_id: Optional tenant association
            description: Project description
            template_id: Optional configuration template to apply
            
        Returns:
            Created project
        """
        # Check if slug is unique
        existing = self.db.query(Project).filter(Project.slug == slug).first()
        if existing:
            raise ValueError(f"Project slug '{slug}' already exists")
        
        # Create project
        project = Project(
            name=name,
            slug=slug,
            owner_id=owner_id,
            tenant_id=tenant_id,
            description=description
        )
        
        self.db.add(project)
        self.db.flush()  # Get project ID
        
        # Apply template if provided
        if template_id:
            self.apply_configuration_template(project.id, template_id, owner_id)
        else:
            # Apply default configurations
            self._apply_default_configurations(project.id, owner_id)
        
        self.db.commit()
        
        logger.info(f"Created project {project.id} with slug '{slug}'")
        return project
    
    def get_project(self, project_id: str = None, slug: str = None) -> Optional[Project]:
        """
        Get project by ID or slug
        
        Args:
            project_id: Project ID
            slug: Project slug
            
        Returns:
            Project if found
        """
        if project_id:
            return self.db.query(Project).filter(Project.id == project_id).first()
        elif slug:
            return self.db.query(Project).filter(Project.slug == slug).first()
        else:
            raise ValueError("Either project_id or slug must be provided")
    
    def set_configuration(self, project_id: str, config_type: str, config_key: str,
                         config_value: Any, user_id: str, override_level: int = 0,
                         inherits_from: str = None) -> ProjectConfiguration:
        """
        Set project configuration value
        
        Args:
            project_id: Project ID
            config_type: Configuration type ('auth', 'ui', 'workflow', 'integration')
            config_key: Configuration key
            config_value: Configuration value
            user_id: User making the change
            override_level: Override level for inheritance
            inherits_from: Parent configuration ID
            
        Returns:
            Created or updated configuration
        """
        # Check if configuration exists
        existing = self.db.query(ProjectConfiguration).filter(
            and_(
                ProjectConfiguration.project_id == project_id,
                ProjectConfiguration.config_type == config_type,
                ProjectConfiguration.config_key == config_key
            )
        ).first()
        
        if existing:
            # Record history
            self._record_configuration_change(
                project_id, existing.id, 'update', 
                existing.config_value, config_value, user_id
            )
            
            # Update existing
            existing.config_value = config_value
            existing.updated_by = user_id
            existing.updated_at = datetime.utcnow()
            existing.override_level = override_level
            existing.inherits_from = inherits_from
            
            configuration = existing
        else:
            # Create new configuration
            configuration = ProjectConfiguration(
                project_id=project_id,
                config_type=config_type,
                config_key=config_key,
                config_value=config_value,
                override_level=override_level,
                inherits_from=inherits_from,
                created_by=user_id,
                updated_by=user_id
            )
            
            self.db.add(configuration)
            self.db.flush()  # Get configuration ID
            
            # Record history
            self._record_configuration_change(
                project_id, configuration.id, 'create',
                None, config_value, user_id
            )
        
        self.db.commit()
        
        logger.info(f"Set configuration {config_type}.{config_key} for project {project_id}")
        return configuration
    
    def get_configuration(self, project_id: str, config_type: str = None,
                         config_key: str = None, resolve_inheritance: bool = True) -> Union[Dict[str, Any], Any]:
        """
        Get project configuration with inheritance resolution
        
        Args:
            project_id: Project ID
            config_type: Optional config type filter
            config_key: Optional specific config key
            resolve_inheritance: Whether to resolve inheritance chain
            
        Returns:
            Configuration value(s)
        """
        query = self.db.query(ProjectConfiguration).filter(
            ProjectConfiguration.project_id == project_id,
            ProjectConfiguration.is_active == True
        )
        
        if config_type:
            query = query.filter(ProjectConfiguration.config_type == config_type)
        
        if config_key:
            query = query.filter(ProjectConfiguration.config_key == config_key)
        
        configurations = query.order_by(desc(ProjectConfiguration.override_level)).all()
        
        if not configurations:
            return None if config_key else {}
        
        if config_key:
            # Return single configuration value
            config = configurations[0]  # Highest override level
            if resolve_inheritance and config.inherits_from:
                return self._resolve_configuration_inheritance(config)
            return config.config_value
        
        # Return all configurations as dictionary
        result = {}
        for config in configurations:
            key = f"{config.config_type}.{config.config_key}"
            if resolve_inheritance and config.inherits_from:
                result[key] = self._resolve_configuration_inheritance(config)
            else:
                result[key] = config.config_value
        
        return result
    
    def create_workflow(self, project_id: str, workflow_name: str, workflow_type: str,
                       workflow_steps: List[Dict[str, Any]], user_id: str,
                       workflow_config: Dict[str, Any] = None,
                       is_default: bool = False, conditions: Dict[str, Any] = None) -> ProjectWorkflow:
        """
        Create project workflow
        
        Args:
            project_id: Project ID
            workflow_name: Workflow name
            workflow_type: Workflow type
            workflow_steps: Array of workflow steps
            user_id: User creating workflow
            workflow_config: Workflow configuration
            is_default: Whether this is the default workflow
            conditions: Conditions for workflow execution
            
        Returns:
            Created workflow
        """
        # If setting as default, unset other defaults
        if is_default:
            self.db.query(ProjectWorkflow).filter(
                and_(
                    ProjectWorkflow.project_id == project_id,
                    ProjectWorkflow.workflow_type == workflow_type,
                    ProjectWorkflow.is_default == True
                )
            ).update({ProjectWorkflow.is_default: False})
        
        workflow = ProjectWorkflow(
            project_id=project_id,
            workflow_name=workflow_name,
            workflow_type=workflow_type,
            workflow_steps=workflow_steps,
            workflow_config=workflow_config or {},
            is_default=is_default,
            conditions=conditions,
            created_by=user_id
        )
        
        self.db.add(workflow)
        self.db.commit()
        
        logger.info(f"Created workflow '{workflow_name}' for project {project_id}")
        return workflow
    
    def get_workflows(self, project_id: str, workflow_type: str = None,
                     active_only: bool = True) -> List[ProjectWorkflow]:
        """
        Get project workflows
        
        Args:
            project_id: Project ID
            workflow_type: Optional workflow type filter
            active_only: Whether to return only active workflows
            
        Returns:
            List of workflows
        """
        query = self.db.query(ProjectWorkflow).filter(
            ProjectWorkflow.project_id == project_id
        )
        
        if workflow_type:
            query = query.filter(ProjectWorkflow.workflow_type == workflow_type)
        
        if active_only:
            query = query.filter(ProjectWorkflow.is_active == True)
        
        return query.order_by(ProjectWorkflow.execution_order, ProjectWorkflow.created_at).all()
    
    def get_default_workflow(self, project_id: str, workflow_type: str) -> Optional[ProjectWorkflow]:
        """
        Get default workflow for project and type
        
        Args:
            project_id: Project ID
            workflow_type: Workflow type
            
        Returns:
            Default workflow if found
        """
        return self.db.query(ProjectWorkflow).filter(
            and_(
                ProjectWorkflow.project_id == project_id,
                ProjectWorkflow.workflow_type == workflow_type,
                ProjectWorkflow.is_default == True,
                ProjectWorkflow.is_active == True
            )
        ).first()
    
    def create_theme(self, project_id: str, theme_name: str, user_id: str,
                    theme_config: Dict[str, Any], is_default: bool = False) -> ProjectTheme:
        """
        Create project theme
        
        Args:
            project_id: Project ID
            theme_name: Theme name
            user_id: User creating theme
            theme_config: Theme configuration
            is_default: Whether this is the default theme
            
        Returns:
            Created theme
        """
        # If setting as default, unset other defaults
        if is_default:
            self.db.query(ProjectTheme).filter(
                and_(
                    ProjectTheme.project_id == project_id,
                    ProjectTheme.is_default == True
                )
            ).update({ProjectTheme.is_default: False})
        
        theme = ProjectTheme(
            project_id=project_id,
            theme_name=theme_name,
            is_default=is_default,
            created_by=user_id,
            **theme_config  # Unpack theme configuration fields
        )
        
        self.db.add(theme)
        self.db.commit()
        
        logger.info(f"Created theme '{theme_name}' for project {project_id}")
        return theme
    
    def get_theme(self, project_id: str, theme_name: str = None) -> Optional[ProjectTheme]:
        """
        Get project theme (default if no name specified)
        
        Args:
            project_id: Project ID
            theme_name: Optional theme name
            
        Returns:
            Theme if found
        """
        query = self.db.query(ProjectTheme).filter(
            ProjectTheme.project_id == project_id,
            ProjectTheme.is_active == True
        )
        
        if theme_name:
            query = query.filter(ProjectTheme.theme_name == theme_name)
        else:
            query = query.filter(ProjectTheme.is_default == True)
        
        return query.first()
    
    def apply_configuration_template(self, project_id: str, template_id: str, user_id: str):
        """
        Apply configuration template to project
        
        Args:
            project_id: Project ID
            template_id: Template ID
            user_id: User applying template
        """
        template = self.db.query(ConfigurationTemplate).filter(
            ConfigurationTemplate.id == template_id
        ).first()
        
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Apply template configurations
        template_config = template.template_config
        
        for config_type, type_configs in template_config.items():
            for config_key, config_value in type_configs.items():
                self.set_configuration(
                    project_id, config_type, config_key, config_value, user_id
                )
        
        # Update template usage count
        template.usage_count += 1
        self.db.commit()
        
        logger.info(f"Applied template {template_id} to project {project_id}")
    
    def get_configuration_templates(self, template_type: str = None,
                                  category: str = None, public_only: bool = True) -> List[ConfigurationTemplate]:
        """
        Get available configuration templates
        
        Args:
            template_type: Optional template type filter
            category: Optional category filter
            public_only: Whether to return only public templates
            
        Returns:
            List of templates
        """
        query = self.db.query(ConfigurationTemplate)
        
        if template_type:
            query = query.filter(ConfigurationTemplate.template_type == template_type)
        
        if category:
            query = query.filter(ConfigurationTemplate.template_category == category)
        
        if public_only:
            query = query.filter(ConfigurationTemplate.is_public == True)
        
        return query.order_by(
            desc(ConfigurationTemplate.is_featured),
            desc(ConfigurationTemplate.usage_count)
        ).all()
    
    def get_configuration_history(self, project_id: str, configuration_id: str = None,
                                limit: int = 50) -> List[ProjectConfigurationHistory]:
        """
        Get configuration change history
        
        Args:
            project_id: Project ID
            configuration_id: Optional specific configuration ID
            limit: Maximum number of history entries
            
        Returns:
            List of history entries
        """
        query = self.db.query(ProjectConfigurationHistory).filter(
            ProjectConfigurationHistory.project_id == project_id
        )
        
        if configuration_id:
            query = query.filter(
                ProjectConfigurationHistory.configuration_id == configuration_id
            )
        
        return query.order_by(desc(ProjectConfigurationHistory.changed_at)).limit(limit).all()
    
    def _apply_default_configurations(self, project_id: str, user_id: str):
        """Apply default configurations to new project"""
        default_configs = {
            'auth': {
                'require_email_verification': True,
                'allow_social_login': True,
                'session_timeout_minutes': 60,
                'max_login_attempts': 5
            },
            'ui': {
                'theme': 'default',
                'show_branding': True,
                'custom_css_enabled': False
            },
            'workflow': {
                'onboarding_enabled': True,
                'progressive_profiling': True,
                'approval_required': False
            }
        }
        
        for config_type, type_configs in default_configs.items():
            for config_key, config_value in type_configs.items():
                self.set_configuration(
                    project_id, config_type, config_key, config_value, user_id
                )
    
    def _resolve_configuration_inheritance(self, config: ProjectConfiguration) -> Any:
        """Resolve configuration inheritance chain"""
        if not config.inherits_from:
            return config.config_value
        
        # Get parent configuration
        parent = self.db.query(ProjectConfiguration).filter(
            ProjectConfiguration.id == config.inherits_from
        ).first()
        
        if not parent:
            return config.config_value
        
        # Merge parent and current values
        if isinstance(config.config_value, dict) and isinstance(parent.config_value, dict):
            # Deep merge dictionaries
            result = parent.config_value.copy()
            result.update(config.config_value)
            return result
        
        # For non-dict values, current overrides parent
        return config.config_value
    
    def _record_configuration_change(self, project_id: str, configuration_id: str,
                                   change_type: str, old_value: Any, new_value: Any,
                                   user_id: str, reason: str = None):
        """Record configuration change in history"""
        history = ProjectConfigurationHistory(
            project_id=project_id,
            configuration_id=configuration_id,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            changed_by=user_id,
            change_reason=reason
        )
        
        self.db.add(history)
    
    def delete_project(self, project_id: str, user_id: str) -> bool:
        """
        Delete project and all associated configurations
        
        Args:
            project_id: Project ID
            user_id: User performing deletion
            
        Returns:
            Success status
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return False
        
        # Record deletion in history for all configurations
        configurations = self.db.query(ProjectConfiguration).filter(
            ProjectConfiguration.project_id == project_id
        ).all()
        
        for config in configurations:
            self._record_configuration_change(
                project_id, config.id, 'delete',
                config.config_value, None, user_id, "Project deletion"
            )
        
        # Delete project (cascades to related records)
        self.db.delete(project)
        self.db.commit()
        
        logger.info(f"Deleted project {project_id}")
        return True