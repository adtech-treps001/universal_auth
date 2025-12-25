"""
Admin Dashboard Service

Service for managing admin dashboard components, panels, widgets,
and integration wizards.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime
import logging
import json

from models.admin import (
    AdminPanel, AdminWidget, IntegrationWizard, AdminAction, AdminDashboard,
    AdminPanelType
)
from services.rbac_service import RBACService
from services.project_service import ProjectConfigurationService

logger = logging.getLogger(__name__)

class AdminService:
    """Service for admin dashboard management"""
    
    def __init__(self, db: Session):
        self.db = db
        self.rbac_service = RBACService(db)
        self.project_service = ProjectConfigurationService(db)
    
    def create_admin_panel(self, panel_data: Dict[str, Any], user_id: str) -> AdminPanel:
        """
        Create a new admin panel
        
        Args:
            panel_data: Panel configuration data
            user_id: User creating the panel
            
        Returns:
            Created AdminPanel instance
        """
        try:
            panel = AdminPanel(
                panel_name=panel_data['panel_name'],
                panel_type=panel_data['panel_type'],
                display_name=panel_data['display_name'],
                description=panel_data.get('description'),
                icon=panel_data.get('icon'),
                tenant_id=panel_data.get('tenant_id'),
                required_roles=panel_data.get('required_roles'),
                required_capabilities=panel_data.get('required_capabilities'),
                config=panel_data.get('config', {}),
                layout=panel_data.get('layout', {}),
                widgets=panel_data.get('widgets', []),
                is_enabled=panel_data.get('is_enabled', True),
                is_default=panel_data.get('is_default', False),
                sort_order=panel_data.get('sort_order', 0),
                created_by=user_id
            )
            
            self.db.add(panel)
            self.db.commit()
            
            logger.info(f"Created admin panel '{panel.panel_name}' by user {user_id}")
            return panel
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create admin panel: {e}")
            raise
    
    def get_admin_panels(self, user_id: str, tenant_id: str = None,
                        panel_type: str = None) -> List[AdminPanel]:
        """
        Get admin panels accessible to user
        
        Args:
            user_id: User ID
            tenant_id: Optional tenant filter
            panel_type: Optional panel type filter
            
        Returns:
            List of accessible admin panels
        """
        query = self.db.query(AdminPanel).filter(AdminPanel.is_enabled == True)
        
        if tenant_id:
            query = query.filter(
                or_(AdminPanel.tenant_id == tenant_id, AdminPanel.tenant_id.is_(None))
            )
        
        if panel_type:
            query = query.filter(AdminPanel.panel_type == panel_type)
        
        panels = query.order_by(AdminPanel.sort_order, AdminPanel.display_name).all()
        
        # Filter by user permissions
        accessible_panels = []
        for panel in panels:
            if self._check_panel_access(panel, user_id, tenant_id):
                accessible_panels.append(panel)
        
        return accessible_panels
    
    def update_admin_panel(self, panel_id: str, updates: Dict[str, Any],
                          user_id: str) -> AdminPanel:
        """
        Update admin panel configuration
        
        Args:
            panel_id: Panel ID
            updates: Update data
            user_id: User making the update
            
        Returns:
            Updated AdminPanel instance
        """
        panel = self.db.query(AdminPanel).filter(AdminPanel.id == panel_id).first()
        
        if not panel:
            raise ValueError("Admin panel not found")
        
        try:
            # Update allowed fields
            updatable_fields = [
                'display_name', 'description', 'icon', 'config', 'layout',
                'widgets', 'is_enabled', 'sort_order', 'required_roles',
                'required_capabilities'
            ]
            
            for field, value in updates.items():
                if field in updatable_fields and hasattr(panel, field):
                    setattr(panel, field, value)
            
            panel.updated_by = user_id
            panel.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Updated admin panel {panel_id} by user {user_id}")
            return panel
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update admin panel {panel_id}: {e}")
            raise
    
    def create_admin_widget(self, widget_data: Dict[str, Any], user_id: str) -> AdminWidget:
        """
        Create a new admin widget
        
        Args:
            widget_data: Widget configuration data
            user_id: User creating the widget
            
        Returns:
            Created AdminWidget instance
        """
        try:
            widget = AdminWidget(
                widget_name=widget_data['widget_name'],
                widget_type=widget_data['widget_type'],
                display_name=widget_data['display_name'],
                description=widget_data.get('description'),
                config=widget_data.get('config', {}),
                data_source=widget_data.get('data_source'),
                refresh_interval=widget_data.get('refresh_interval'),
                width=widget_data.get('width', 12),
                height=widget_data.get('height', 4),
                position_x=widget_data.get('position_x', 0),
                position_y=widget_data.get('position_y', 0),
                is_enabled=widget_data.get('is_enabled', True),
                is_visible=widget_data.get('is_visible', True),
                panel_id=widget_data['panel_id'],
                created_by=user_id
            )
            
            self.db.add(widget)
            self.db.commit()
            
            logger.info(f"Created admin widget '{widget.widget_name}' by user {user_id}")
            return widget
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create admin widget: {e}")
            raise
    
    def create_integration_wizard(self, wizard_data: Dict[str, Any], user_id: str) -> IntegrationWizard:
        """
        Create a new integration wizard
        
        Args:
            wizard_data: Wizard configuration data
            user_id: User creating the wizard
            
        Returns:
            Created IntegrationWizard instance
        """
        try:
            wizard = IntegrationWizard(
                wizard_name=wizard_data['wizard_name'],
                integration_type=wizard_data['integration_type'],
                display_name=wizard_data['display_name'],
                description=wizard_data.get('description'),
                steps=wizard_data['steps'],
                validation_rules=wizard_data.get('validation_rules', {}),
                default_values=wizard_data.get('default_values', {}),
                provider=wizard_data.get('provider'),
                endpoints=wizard_data.get('endpoints', {}),
                auth_config=wizard_data.get('auth_config', {}),
                is_enabled=wizard_data.get('is_enabled', True),
                created_by=user_id
            )
            
            self.db.add(wizard)
            self.db.commit()
            
            logger.info(f"Created integration wizard '{wizard.wizard_name}' by user {user_id}")
            return wizard
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create integration wizard: {e}")
            raise
    
    def get_integration_wizards(self, integration_type: str = None) -> List[IntegrationWizard]:
        """
        Get available integration wizards
        
        Args:
            integration_type: Optional filter by integration type
            
        Returns:
            List of integration wizards
        """
        query = self.db.query(IntegrationWizard).filter(IntegrationWizard.is_enabled == True)
        
        if integration_type:
            query = query.filter(IntegrationWizard.integration_type == integration_type)
        
        return query.order_by(IntegrationWizard.display_name).all()
    
    def execute_wizard_step(self, wizard_id: str, step_index: int,
                           step_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Execute a wizard step
        
        Args:
            wizard_id: Wizard ID
            step_index: Step index
            step_data: Step input data
            user_id: User executing the step
            
        Returns:
            Step execution result
        """
        wizard = self.db.query(IntegrationWizard).filter(
            IntegrationWizard.id == wizard_id
        ).first()
        
        if not wizard:
            raise ValueError("Integration wizard not found")
        
        if step_index >= len(wizard.steps):
            raise ValueError("Invalid step index")
        
        step = wizard.steps[step_index]
        
        try:
            # Validate step data
            if wizard.validation_rules and str(step_index) in wizard.validation_rules:
                validation_result = self._validate_step_data(
                    step_data, wizard.validation_rules[str(step_index)]
                )
                if not validation_result['valid']:
                    return {
                        'success': False,
                        'errors': validation_result['errors']
                    }
            
            # Execute step based on type
            result = self._execute_step_by_type(step, step_data, user_id)
            
            # Update completion rate if this is the last step
            if step_index == len(wizard.steps) - 1:
                wizard.completion_rate = min(100, wizard.completion_rate + 1)
                self.db.commit()
            
            return {
                'success': True,
                'result': result,
                'next_step': step_index + 1 if step_index + 1 < len(wizard.steps) else None
            }
            
        except Exception as e:
            logger.error(f"Failed to execute wizard step: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_admin_dashboard(self, dashboard_data: Dict[str, Any], user_id: str) -> AdminDashboard:
        """
        Create a new admin dashboard
        
        Args:
            dashboard_data: Dashboard configuration data
            user_id: User creating the dashboard
            
        Returns:
            Created AdminDashboard instance
        """
        try:
            dashboard = AdminDashboard(
                dashboard_name=dashboard_data['dashboard_name'],
                display_name=dashboard_data['display_name'],
                description=dashboard_data.get('description'),
                layout=dashboard_data.get('layout', {}),
                panels=dashboard_data.get('panels', []),
                theme=dashboard_data.get('theme', 'default'),
                tenant_id=dashboard_data.get('tenant_id'),
                owner_id=user_id,
                is_public=dashboard_data.get('is_public', False),
                shared_with=dashboard_data.get('shared_with', []),
                is_default=dashboard_data.get('is_default', False),
                is_enabled=dashboard_data.get('is_enabled', True),
                created_by=user_id
            )
            
            self.db.add(dashboard)
            self.db.commit()
            
            logger.info(f"Created admin dashboard '{dashboard.dashboard_name}' by user {user_id}")
            return dashboard
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create admin dashboard: {e}")
            raise
    
    def get_dashboard_data(self, dashboard_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get dashboard data with widgets and panels
        
        Args:
            dashboard_id: Dashboard ID
            user_id: User requesting the data
            
        Returns:
            Dashboard data with populated widgets
        """
        dashboard = self.db.query(AdminDashboard).filter(
            AdminDashboard.id == dashboard_id
        ).first()
        
        if not dashboard:
            raise ValueError("Dashboard not found")
        
        # Check access permissions
        if not self._check_dashboard_access(dashboard, user_id):
            raise PermissionError("Insufficient permissions to access dashboard")
        
        # Get panels and widgets
        panels_data = []
        if dashboard.panels:
            for panel_id in dashboard.panels:
                panel = self.db.query(AdminPanel).filter(AdminPanel.id == panel_id).first()
                if panel and self._check_panel_access(panel, user_id, dashboard.tenant_id):
                    widgets = self.db.query(AdminWidget).filter(
                        and_(
                            AdminWidget.panel_id == panel_id,
                            AdminWidget.is_enabled == True,
                            AdminWidget.is_visible == True
                        )
                    ).order_by(AdminWidget.position_y, AdminWidget.position_x).all()
                    
                    panels_data.append({
                        'panel': panel,
                        'widgets': widgets
                    })
        
        return {
            'dashboard': dashboard,
            'panels': panels_data,
            'layout': dashboard.layout,
            'theme': dashboard.theme
        }
    
    def _check_panel_access(self, panel: AdminPanel, user_id: str, tenant_id: str = None) -> bool:
        """Check if user has access to admin panel"""
        
        # Check role requirements
        if panel.required_roles:
            user_roles = self.rbac_service.get_user_roles(user_id, tenant_id or panel.tenant_id)
            user_role_names = [role.name for role in user_roles]
            
            if not any(role in panel.required_roles for role in user_role_names):
                return False
        
        # Check capability requirements
        if panel.required_capabilities:
            for capability in panel.required_capabilities:
                if not self.rbac_service.check_permission(user_id, capability, tenant_id or panel.tenant_id):
                    return False
        
        return True
    
    def _check_dashboard_access(self, dashboard: AdminDashboard, user_id: str) -> bool:
        """Check if user has access to dashboard"""
        
        # Owner always has access
        if dashboard.owner_id == user_id:
            return True
        
        # Check if dashboard is public
        if dashboard.is_public:
            return True
        
        # Check if user is in shared_with list
        if dashboard.shared_with and user_id in dashboard.shared_with:
            return True
        
        return False
    
    def _validate_step_data(self, step_data: Dict[str, Any], 
                           validation_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate wizard step data"""
        
        errors = []
        
        for field, rules in validation_rules.items():
            value = step_data.get(field)
            
            # Required field check
            if rules.get('required', False) and not value:
                errors.append(f"Field '{field}' is required")
                continue
            
            if value is not None:
                # Type validation
                expected_type = rules.get('type')
                if expected_type and not isinstance(value, eval(expected_type)):
                    errors.append(f"Field '{field}' must be of type {expected_type}")
                
                # Length validation
                if isinstance(value, str):
                    min_length = rules.get('min_length')
                    max_length = rules.get('max_length')
                    
                    if min_length and len(value) < min_length:
                        errors.append(f"Field '{field}' must be at least {min_length} characters")
                    
                    if max_length and len(value) > max_length:
                        errors.append(f"Field '{field}' must be at most {max_length} characters")
                
                # Pattern validation
                pattern = rules.get('pattern')
                if pattern and isinstance(value, str):
                    import re
                    if not re.match(pattern, value):
                        errors.append(f"Field '{field}' format is invalid")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _execute_step_by_type(self, step: Dict[str, Any], step_data: Dict[str, Any],
                             user_id: str) -> Dict[str, Any]:
        """Execute wizard step based on step type"""
        
        step_type = step.get('type', 'form')
        
        if step_type == 'oauth_config':
            return self._execute_oauth_config_step(step, step_data, user_id)
        elif step_type == 'api_key_config':
            return self._execute_api_key_config_step(step, step_data, user_id)
        elif step_type == 'project_config':
            return self._execute_project_config_step(step, step_data, user_id)
        elif step_type == 'role_assignment':
            return self._execute_role_assignment_step(step, step_data, user_id)
        else:
            # Default form step
            return {'step_data': step_data}
    
    def _execute_oauth_config_step(self, step: Dict[str, Any], step_data: Dict[str, Any],
                                  user_id: str) -> Dict[str, Any]:
        """Execute OAuth configuration step"""
        
        # Create OAuth provider configuration
        provider_config = {
            'provider': step_data['provider'],
            'client_id': step_data['client_id'],
            'client_secret': step_data['client_secret'],
            'scopes': step_data.get('scopes', []),
            'redirect_uri': step_data.get('redirect_uri')
        }
        
        # Store configuration (implementation depends on OAuth service)
        # This would integrate with the OAuth service to store provider config
        
        return {
            'provider_configured': True,
            'provider': step_data['provider'],
            'config_id': f"oauth_{step_data['provider']}_{user_id}"
        }
    
    def _execute_api_key_config_step(self, step: Dict[str, Any], step_data: Dict[str, Any],
                                    user_id: str) -> Dict[str, Any]:
        """Execute API key configuration step"""
        
        # This would integrate with the API key service
        from services.api_key_service import APIKeyService
        
        api_key_service = APIKeyService(self.db)
        
        try:
            api_key = api_key_service.create_api_key(
                project_id=step_data['project_id'],
                key_name=step_data['key_name'],
                provider=step_data['provider'],
                api_key_value=step_data['api_key_value'],
                user_id=user_id,
                scopes=step_data.get('scopes'),
                rate_limits=step_data.get('rate_limits')
            )
            
            return {
                'api_key_created': True,
                'api_key_id': api_key.id,
                'key_name': api_key.key_name
            }
            
        except Exception as e:
            raise Exception(f"Failed to create API key: {e}")
    
    def _execute_project_config_step(self, step: Dict[str, Any], step_data: Dict[str, Any],
                                    user_id: str) -> Dict[str, Any]:
        """Execute project configuration step"""
        
        try:
            project = self.project_service.create_project(
                project_name=step_data['project_name'],
                owner_id=user_id,
                config=step_data.get('config', {}),
                workflow=step_data.get('workflow'),
                theme_config=step_data.get('theme_config')
            )
            
            return {
                'project_created': True,
                'project_id': project.id,
                'project_name': project.project_name
            }
            
        except Exception as e:
            raise Exception(f"Failed to create project: {e}")
    
    def _execute_role_assignment_step(self, step: Dict[str, Any], step_data: Dict[str, Any],
                                     user_id: str) -> Dict[str, Any]:
        """Execute role assignment step"""
        
        try:
            target_user_id = step_data['target_user_id']
            roles = step_data['roles']
            tenant_id = step_data.get('tenant_id')
            
            for role_name in roles:
                self.rbac_service.assign_role_to_user(
                    user_id=target_user_id,
                    role_name=role_name,
                    tenant_id=tenant_id,
                    assigned_by=user_id
                )
            
            return {
                'roles_assigned': True,
                'target_user_id': target_user_id,
                'roles': roles
            }
            
        except Exception as e:
            raise Exception(f"Failed to assign roles: {e}")

class AdminPanelBuilder:
    """Builder for creating standard admin panels"""
    
    @staticmethod
    def create_project_config_panel() -> Dict[str, Any]:
        """Create project configuration panel"""
        return {
            'panel_name': 'project_configuration',
            'panel_type': AdminPanelType.PROJECT_CONFIG.value,
            'display_name': 'Project Configuration',
            'description': 'Manage project settings and configurations',
            'icon': 'settings',
            'required_capabilities': ['project.manage'],
            'config': {
                'sections': [
                    'basic_settings',
                    'workflow_config',
                    'theme_config',
                    'integration_settings'
                ]
            },
            'widgets': [
                'project_overview',
                'workflow_selector',
                'theme_editor',
                'integration_status'
            ]
        }
    
    @staticmethod
    def create_role_management_panel() -> Dict[str, Any]:
        """Create role management panel"""
        return {
            'panel_name': 'role_management',
            'panel_type': AdminPanelType.ROLE_MANAGEMENT.value,
            'display_name': 'Role Management',
            'description': 'Manage user roles and permissions',
            'icon': 'users',
            'required_capabilities': ['rbac.manage'],
            'config': {
                'sections': [
                    'role_list',
                    'role_editor',
                    'user_assignments'
                ]
            },
            'widgets': [
                'role_overview',
                'user_role_matrix',
                'permission_tree'
            ]
        }
    
    @staticmethod
    def create_api_key_management_panel() -> Dict[str, Any]:
        """Create API key management panel"""
        return {
            'panel_name': 'api_key_management',
            'panel_type': AdminPanelType.API_KEY_MANAGEMENT.value,
            'display_name': 'API Key Management',
            'description': 'Manage API keys and access control',
            'icon': 'key',
            'required_capabilities': ['api_key.manage'],
            'config': {
                'sections': [
                    'key_list',
                    'key_editor',
                    'usage_analytics'
                ]
            },
            'widgets': [
                'key_overview',
                'usage_charts',
                'rate_limit_status'
            ]
        }