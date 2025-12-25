"""
Admin Dashboard Routes

API endpoints for admin dashboard management, panels, widgets,
and integration wizards.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from database import get_db
from services.admin_service import AdminService, AdminPanelBuilder
from auth.middleware import get_current_user, require_permission
from models.user import User
from models.admin import AdminPanelType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Pydantic models for request/response
class AdminPanelCreateRequest(BaseModel):
    panel_name: str = Field(..., min_length=1, max_length=100)
    panel_type: str = Field(..., description="Panel type")
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=50)
    tenant_id: Optional[str] = None
    required_roles: Optional[List[str]] = None
    required_capabilities: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    layout: Optional[Dict[str, Any]] = None
    widgets: Optional[List[str]] = None
    is_enabled: bool = True
    is_default: bool = False
    sort_order: int = 0

class AdminPanelResponse(BaseModel):
    id: str
    panel_name: str
    panel_type: str
    display_name: str
    description: Optional[str]
    icon: Optional[str]
    tenant_id: Optional[str]
    required_roles: Optional[List[str]]
    required_capabilities: Optional[List[str]]
    config: Optional[Dict[str, Any]]
    layout: Optional[Dict[str, Any]]
    widgets: Optional[List[str]]
    is_enabled: bool
    is_default: bool
    sort_order: int
    created_at: str
    updated_at: str

class AdminWidgetCreateRequest(BaseModel):
    widget_name: str = Field(..., min_length=1, max_length=100)
    widget_type: str = Field(..., description="Widget type (chart, table, form, etc.)")
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    config: Optional[Dict[str, Any]] = None
    data_source: Optional[str] = Field(None, description="Data source endpoint")
    refresh_interval: Optional[int] = Field(None, ge=1, description="Refresh interval in seconds")
    width: int = Field(12, ge=1, le=12, description="Grid width (1-12)")
    height: int = Field(4, ge=1, description="Grid height")
    position_x: int = Field(0, ge=0, description="X position")
    position_y: int = Field(0, ge=0, description="Y position")
    is_enabled: bool = True
    is_visible: bool = True
    panel_id: str = Field(..., description="Parent panel ID")

class AdminWidgetResponse(BaseModel):
    id: str
    widget_name: str
    widget_type: str
    display_name: str
    description: Optional[str]
    config: Optional[Dict[str, Any]]
    data_source: Optional[str]
    refresh_interval: Optional[int]
    width: int
    height: int
    position_x: int
    position_y: int
    is_enabled: bool
    is_visible: bool
    panel_id: str
    created_at: str

class IntegrationWizardCreateRequest(BaseModel):
    wizard_name: str = Field(..., min_length=1, max_length=100)
    integration_type: str = Field(..., description="Integration type")
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    steps: List[Dict[str, Any]] = Field(..., description="Wizard steps")
    validation_rules: Optional[Dict[str, Any]] = None
    default_values: Optional[Dict[str, Any]] = None
    provider: Optional[str] = Field(None, description="Integration provider")
    endpoints: Optional[Dict[str, Any]] = None
    auth_config: Optional[Dict[str, Any]] = None
    is_enabled: bool = True

class IntegrationWizardResponse(BaseModel):
    id: str
    wizard_name: str
    integration_type: str
    display_name: str
    description: Optional[str]
    steps: List[Dict[str, Any]]
    validation_rules: Optional[Dict[str, Any]]
    default_values: Optional[Dict[str, Any]]
    provider: Optional[str]
    endpoints: Optional[Dict[str, Any]]
    auth_config: Optional[Dict[str, Any]]
    is_enabled: bool
    completion_rate: int
    created_at: str

class WizardStepExecuteRequest(BaseModel):
    step_data: Dict[str, Any] = Field(..., description="Step input data")

class AdminDashboardCreateRequest(BaseModel):
    dashboard_name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    layout: Optional[Dict[str, Any]] = None
    panels: Optional[List[str]] = None
    theme: str = Field("default", description="Dashboard theme")
    tenant_id: Optional[str] = None
    is_public: bool = False
    shared_with: Optional[List[str]] = None
    is_default: bool = False
    is_enabled: bool = True

class AdminDashboardResponse(BaseModel):
    id: str
    dashboard_name: str
    display_name: str
    description: Optional[str]
    layout: Optional[Dict[str, Any]]
    panels: Optional[List[str]]
    theme: str
    tenant_id: Optional[str]
    owner_id: str
    is_public: bool
    shared_with: Optional[List[str]]
    is_default: bool
    is_enabled: bool
    created_at: str
    updated_at: str

# Admin Panel Management
@router.post("/panels", response_model=AdminPanelResponse)
async def create_admin_panel(
    request: AdminPanelCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new admin panel"""
    
    await require_permission(current_user, "admin.panel.create", db)
    
    try:
        admin_service = AdminService(db)
        
        panel = admin_service.create_admin_panel(
            panel_data=request.dict(),
            user_id=current_user.id
        )
        
        return AdminPanelResponse(
            id=panel.id,
            panel_name=panel.panel_name,
            panel_type=panel.panel_type,
            display_name=panel.display_name,
            description=panel.description,
            icon=panel.icon,
            tenant_id=panel.tenant_id,
            required_roles=panel.required_roles,
            required_capabilities=panel.required_capabilities,
            config=panel.config,
            layout=panel.layout,
            widgets=panel.widgets,
            is_enabled=panel.is_enabled,
            is_default=panel.is_default,
            sort_order=panel.sort_order,
            created_at=panel.created_at.isoformat(),
            updated_at=panel.updated_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating admin panel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create admin panel"
        )

@router.get("/panels", response_model=List[AdminPanelResponse])
async def list_admin_panels(
    panel_type: Optional[str] = Query(None, description="Filter by panel type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List admin panels accessible to user"""
    
    try:
        admin_service = AdminService(db)
        
        panels = admin_service.get_admin_panels(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            panel_type=panel_type
        )
        
        return [
            AdminPanelResponse(
                id=panel.id,
                panel_name=panel.panel_name,
                panel_type=panel.panel_type,
                display_name=panel.display_name,
                description=panel.description,
                icon=panel.icon,
                tenant_id=panel.tenant_id,
                required_roles=panel.required_roles,
                required_capabilities=panel.required_capabilities,
                config=panel.config,
                layout=panel.layout,
                widgets=panel.widgets,
                is_enabled=panel.is_enabled,
                is_default=panel.is_default,
                sort_order=panel.sort_order,
                created_at=panel.created_at.isoformat(),
                updated_at=panel.updated_at.isoformat()
            )
            for panel in panels
        ]
        
    except Exception as e:
        logger.error(f"Error listing admin panels: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list admin panels"
        )

@router.put("/panels/{panel_id}", response_model=AdminPanelResponse)
async def update_admin_panel(
    panel_id: str,
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update admin panel configuration"""
    
    await require_permission(current_user, "admin.panel.update", db)
    
    try:
        admin_service = AdminService(db)
        
        panel = admin_service.update_admin_panel(
            panel_id=panel_id,
            updates=updates,
            user_id=current_user.id
        )
        
        return AdminPanelResponse(
            id=panel.id,
            panel_name=panel.panel_name,
            panel_type=panel.panel_type,
            display_name=panel.display_name,
            description=panel.description,
            icon=panel.icon,
            tenant_id=panel.tenant_id,
            required_roles=panel.required_roles,
            required_capabilities=panel.required_capabilities,
            config=panel.config,
            layout=panel.layout,
            widgets=panel.widgets,
            is_enabled=panel.is_enabled,
            is_default=panel.is_default,
            sort_order=panel.sort_order,
            created_at=panel.created_at.isoformat(),
            updated_at=panel.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating admin panel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update admin panel"
        )

# Widget Management
@router.post("/widgets", response_model=AdminWidgetResponse)
async def create_admin_widget(
    request: AdminWidgetCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new admin widget"""
    
    await require_permission(current_user, "admin.widget.create", db)
    
    try:
        admin_service = AdminService(db)
        
        widget = admin_service.create_admin_widget(
            widget_data=request.dict(),
            user_id=current_user.id
        )
        
        return AdminWidgetResponse(
            id=widget.id,
            widget_name=widget.widget_name,
            widget_type=widget.widget_type,
            display_name=widget.display_name,
            description=widget.description,
            config=widget.config,
            data_source=widget.data_source,
            refresh_interval=widget.refresh_interval,
            width=widget.width,
            height=widget.height,
            position_x=widget.position_x,
            position_y=widget.position_y,
            is_enabled=widget.is_enabled,
            is_visible=widget.is_visible,
            panel_id=widget.panel_id,
            created_at=widget.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating admin widget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create admin widget"
        )

# Integration Wizard Management
@router.post("/wizards", response_model=IntegrationWizardResponse)
async def create_integration_wizard(
    request: IntegrationWizardCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new integration wizard"""
    
    await require_permission(current_user, "admin.wizard.create", db)
    
    try:
        admin_service = AdminService(db)
        
        wizard = admin_service.create_integration_wizard(
            wizard_data=request.dict(),
            user_id=current_user.id
        )
        
        return IntegrationWizardResponse(
            id=wizard.id,
            wizard_name=wizard.wizard_name,
            integration_type=wizard.integration_type,
            display_name=wizard.display_name,
            description=wizard.description,
            steps=wizard.steps,
            validation_rules=wizard.validation_rules,
            default_values=wizard.default_values,
            provider=wizard.provider,
            endpoints=wizard.endpoints,
            auth_config=wizard.auth_config,
            is_enabled=wizard.is_enabled,
            completion_rate=wizard.completion_rate,
            created_at=wizard.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating integration wizard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create integration wizard"
        )

@router.get("/wizards", response_model=List[IntegrationWizardResponse])
async def list_integration_wizards(
    integration_type: Optional[str] = Query(None, description="Filter by integration type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List available integration wizards"""
    
    try:
        admin_service = AdminService(db)
        
        wizards = admin_service.get_integration_wizards(integration_type=integration_type)
        
        return [
            IntegrationWizardResponse(
                id=wizard.id,
                wizard_name=wizard.wizard_name,
                integration_type=wizard.integration_type,
                display_name=wizard.display_name,
                description=wizard.description,
                steps=wizard.steps,
                validation_rules=wizard.validation_rules,
                default_values=wizard.default_values,
                provider=wizard.provider,
                endpoints=wizard.endpoints,
                auth_config=wizard.auth_config,
                is_enabled=wizard.is_enabled,
                completion_rate=wizard.completion_rate,
                created_at=wizard.created_at.isoformat()
            )
            for wizard in wizards
        ]
        
    except Exception as e:
        logger.error(f"Error listing integration wizards: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list integration wizards"
        )

@router.post("/wizards/{wizard_id}/steps/{step_index}/execute")
async def execute_wizard_step(
    wizard_id: str,
    step_index: int,
    request: WizardStepExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute a wizard step"""
    
    try:
        admin_service = AdminService(db)
        
        result = admin_service.execute_wizard_step(
            wizard_id=wizard_id,
            step_index=step_index,
            step_data=request.step_data,
            user_id=current_user.id
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error executing wizard step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute wizard step"
        )

# Dashboard Management
@router.post("/dashboards", response_model=AdminDashboardResponse)
async def create_admin_dashboard(
    request: AdminDashboardCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new admin dashboard"""
    
    await require_permission(current_user, "admin.dashboard.create", db)
    
    try:
        admin_service = AdminService(db)
        
        dashboard = admin_service.create_admin_dashboard(
            dashboard_data=request.dict(),
            user_id=current_user.id
        )
        
        return AdminDashboardResponse(
            id=dashboard.id,
            dashboard_name=dashboard.dashboard_name,
            display_name=dashboard.display_name,
            description=dashboard.description,
            layout=dashboard.layout,
            panels=dashboard.panels,
            theme=dashboard.theme,
            tenant_id=dashboard.tenant_id,
            owner_id=dashboard.owner_id,
            is_public=dashboard.is_public,
            shared_with=dashboard.shared_with,
            is_default=dashboard.is_default,
            is_enabled=dashboard.is_enabled,
            created_at=dashboard.created_at.isoformat(),
            updated_at=dashboard.updated_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating admin dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create admin dashboard"
        )

@router.get("/dashboards/{dashboard_id}/data")
async def get_dashboard_data(
    dashboard_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard data with widgets and panels"""
    
    try:
        admin_service = AdminService(db)
        
        dashboard_data = admin_service.get_dashboard_data(
            dashboard_id=dashboard_id,
            user_id=current_user.id
        )
        
        return dashboard_data
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard data"
        )

# Standard Panel Creation
@router.post("/panels/standard/project-config", response_model=AdminPanelResponse)
async def create_project_config_panel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create standard project configuration panel"""
    
    await require_permission(current_user, "admin.panel.create", db)
    
    try:
        admin_service = AdminService(db)
        
        panel_data = AdminPanelBuilder.create_project_config_panel()
        panel_data['tenant_id'] = current_user.tenant_id
        
        panel = admin_service.create_admin_panel(
            panel_data=panel_data,
            user_id=current_user.id
        )
        
        return AdminPanelResponse(
            id=panel.id,
            panel_name=panel.panel_name,
            panel_type=panel.panel_type,
            display_name=panel.display_name,
            description=panel.description,
            icon=panel.icon,
            tenant_id=panel.tenant_id,
            required_roles=panel.required_roles,
            required_capabilities=panel.required_capabilities,
            config=panel.config,
            layout=panel.layout,
            widgets=panel.widgets,
            is_enabled=panel.is_enabled,
            is_default=panel.is_default,
            sort_order=panel.sort_order,
            created_at=panel.created_at.isoformat(),
            updated_at=panel.updated_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating project config panel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project config panel"
        )

@router.post("/panels/standard/role-management", response_model=AdminPanelResponse)
async def create_role_management_panel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create standard role management panel"""
    
    await require_permission(current_user, "admin.panel.create", db)
    
    try:
        admin_service = AdminService(db)
        
        panel_data = AdminPanelBuilder.create_role_management_panel()
        panel_data['tenant_id'] = current_user.tenant_id
        
        panel = admin_service.create_admin_panel(
            panel_data=panel_data,
            user_id=current_user.id
        )
        
        return AdminPanelResponse(
            id=panel.id,
            panel_name=panel.panel_name,
            panel_type=panel.panel_type,
            display_name=panel.display_name,
            description=panel.description,
            icon=panel.icon,
            tenant_id=panel.tenant_id,
            required_roles=panel.required_roles,
            required_capabilities=panel.required_capabilities,
            config=panel.config,
            layout=panel.layout,
            widgets=panel.widgets,
            is_enabled=panel.is_enabled,
            is_default=panel.is_default,
            sort_order=panel.sort_order,
            created_at=panel.created_at.isoformat(),
            updated_at=panel.updated_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating role management panel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create role management panel"
        )

@router.post("/panels/standard/api-key-management", response_model=AdminPanelResponse)
async def create_api_key_management_panel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create standard API key management panel"""
    
    await require_permission(current_user, "admin.panel.create", db)
    
    try:
        admin_service = AdminService(db)
        
        panel_data = AdminPanelBuilder.create_api_key_management_panel()
        panel_data['tenant_id'] = current_user.tenant_id
        
        panel = admin_service.create_admin_panel(
            panel_data=panel_data,
            user_id=current_user.id
        )
        
        return AdminPanelResponse(
            id=panel.id,
            panel_name=panel.panel_name,
            panel_type=panel.panel_type,
            display_name=panel.display_name,
            description=panel.description,
            icon=panel.icon,
            tenant_id=panel.tenant_id,
            required_roles=panel.required_roles,
            required_capabilities=panel.required_capabilities,
            config=panel.config,
            layout=panel.layout,
            widgets=panel.widgets,
            is_enabled=panel.is_enabled,
            is_default=panel.is_default,
            sort_order=panel.sort_order,
            created_at=panel.created_at.isoformat(),
            updated_at=panel.updated_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating API key management panel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key management panel"
        )