"""
Project Configuration Routes

This module provides API endpoints for managing project-specific configurations,
workflows, and themes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from database import get_db
from services.project_service import ProjectConfigurationService
from auth.middleware import get_current_user, require_capability

router = APIRouter(prefix="/projects", tags=["projects"])

# Pydantic models for request/response
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z0-9-]+$')
    description: Optional[str] = Field(None, max_length=500)
    tenant_id: Optional[str] = None
    template_id: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    owner_id: str
    tenant_id: Optional[str]
    is_active: bool
    is_public: bool
    created_at: datetime
    updated_at: datetime

class ConfigurationSet(BaseModel):
    config_type: str = Field(..., pattern=r'^(auth|ui|workflow|integration)$')
    config_key: str = Field(..., min_length=1, max_length=100)
    config_value: Any
    override_level: int = Field(0, ge=0, le=10)
    inherits_from: Optional[str] = None

class ConfigurationResponse(BaseModel):
    id: str
    config_type: str
    config_key: str
    config_value: Any
    override_level: int
    inherits_from: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class WorkflowCreate(BaseModel):
    workflow_name: str = Field(..., min_length=1, max_length=100)
    workflow_type: str = Field(..., pattern=r'^(authentication|onboarding|approval|custom)$')
    workflow_steps: List[Dict[str, Any]]
    workflow_config: Optional[Dict[str, Any]] = {}
    is_default: bool = False
    conditions: Optional[Dict[str, Any]] = None

class WorkflowResponse(BaseModel):
    id: str
    workflow_name: str
    workflow_type: str
    workflow_steps: List[Dict[str, Any]]
    workflow_config: Dict[str, Any]
    is_default: bool
    is_required: bool
    execution_order: int
    conditions: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime

class ThemeCreate(BaseModel):
    theme_name: str = Field(..., min_length=1, max_length=100)
    primary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    secondary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    accent_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    background_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    text_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    font_family: Optional[str] = None
    font_size_base: Optional[str] = None
    border_radius: Optional[str] = None
    logo_url: Optional[str] = None
    brand_name: Optional[str] = None
    custom_css: Optional[str] = None
    is_default: bool = False

class ThemeResponse(BaseModel):
    id: str
    theme_name: str
    primary_color: Optional[str]
    secondary_color: Optional[str]
    accent_color: Optional[str]
    background_color: Optional[str]
    text_color: Optional[str]
    font_family: Optional[str]
    logo_url: Optional[str]
    brand_name: Optional[str]
    is_default: bool
    is_active: bool
    created_at: datetime

# Project management endpoints
@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project"""
    service = ProjectConfigurationService(db)
    
    try:
        project = service.create_project(
            name=project_data.name,
            slug=project_data.slug,
            owner_id=current_user["user_id"],
            tenant_id=project_data.tenant_id,
            description=project_data.description,
            template_id=project_data.template_id
        )
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            owner_id=project.owner_id,
            tenant_id=project.tenant_id,
            is_active=project.is_active,
            is_public=project.is_public,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project by ID"""
    service = ProjectConfigurationService(db)
    project = service.get_project(project_id=project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check access permissions
    if (project.owner_id != current_user["user_id"] and 
        not project.is_public and
        "admin:projects" not in current_user.get("capabilities", [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        owner_id=project.owner_id,
        tenant_id=project.tenant_id,
        is_active=project.is_active,
        is_public=project.is_public,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

@router.get("/slug/{slug}", response_model=ProjectResponse)
async def get_project_by_slug(
    slug: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project by slug"""
    service = ProjectConfigurationService(db)
    project = service.get_project(slug=slug)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check access permissions
    if (project.owner_id != current_user["user_id"] and 
        not project.is_public and
        "admin:projects" not in current_user.get("capabilities", [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        owner_id=project.owner_id,
        tenant_id=project.tenant_id,
        is_active=project.is_active,
        is_public=project.is_public,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

# Configuration management endpoints
@router.post("/{project_id}/config", response_model=ConfigurationResponse)
async def set_configuration(
    project_id: str = Path(...),
    config_data: ConfigurationSet = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set project configuration"""
    service = ProjectConfigurationService(db)
    
    # Check project access
    project = service.get_project(project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if (project.owner_id != current_user["user_id"] and
        "admin:projects" not in current_user.get("capabilities", [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        config = service.set_configuration(
            project_id=project_id,
            config_type=config_data.config_type,
            config_key=config_data.config_key,
            config_value=config_data.config_value,
            user_id=current_user["user_id"],
            override_level=config_data.override_level,
            inherits_from=config_data.inherits_from
        )
        
        return ConfigurationResponse(
            id=config.id,
            config_type=config.config_type,
            config_key=config.config_key,
            config_value=config.config_value,
            override_level=config.override_level,
            inherits_from=config.inherits_from,
            is_active=config.is_active,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}/config")
async def get_configuration(
    project_id: str = Path(...),
    config_type: Optional[str] = Query(None),
    config_key: Optional[str] = Query(None),
    resolve_inheritance: bool = Query(True),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project configuration"""
    service = ProjectConfigurationService(db)
    
    # Check project access
    project = service.get_project(project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if (project.owner_id != current_user["user_id"] and 
        not project.is_public and
        "admin:projects" not in current_user.get("capabilities", [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    config = service.get_configuration(
        project_id=project_id,
        config_type=config_type,
        config_key=config_key,
        resolve_inheritance=resolve_inheritance
    )
    
    if config is None:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return {"configuration": config}

# Workflow management endpoints
@router.post("/{project_id}/workflows", response_model=WorkflowResponse)
async def create_workflow(
    project_id: str = Path(...),
    workflow_data: WorkflowCreate = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create project workflow"""
    service = ProjectConfigurationService(db)
    
    # Check project access
    project = service.get_project(project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if (project.owner_id != current_user["user_id"] and
        "admin:projects" not in current_user.get("capabilities", [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        workflow = service.create_workflow(
            project_id=project_id,
            workflow_name=workflow_data.workflow_name,
            workflow_type=workflow_data.workflow_type,
            workflow_steps=workflow_data.workflow_steps,
            user_id=current_user["user_id"],
            workflow_config=workflow_data.workflow_config,
            is_default=workflow_data.is_default,
            conditions=workflow_data.conditions
        )
        
        return WorkflowResponse(
            id=workflow.id,
            workflow_name=workflow.workflow_name,
            workflow_type=workflow.workflow_type,
            workflow_steps=workflow.workflow_steps,
            workflow_config=workflow.workflow_config,
            is_default=workflow.is_default,
            is_required=workflow.is_required,
            execution_order=workflow.execution_order,
            conditions=workflow.conditions,
            is_active=workflow.is_active,
            created_at=workflow.created_at
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}/workflows", response_model=List[WorkflowResponse])
async def get_workflows(
    project_id: str = Path(...),
    workflow_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project workflows"""
    service = ProjectConfigurationService(db)
    
    # Check project access
    project = service.get_project(project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if (project.owner_id != current_user["user_id"] and 
        not project.is_public and
        "admin:projects" not in current_user.get("capabilities", [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    workflows = service.get_workflows(
        project_id=project_id,
        workflow_type=workflow_type,
        active_only=active_only
    )
    
    return [
        WorkflowResponse(
            id=workflow.id,
            workflow_name=workflow.workflow_name,
            workflow_type=workflow.workflow_type,
            workflow_steps=workflow.workflow_steps,
            workflow_config=workflow.workflow_config,
            is_default=workflow.is_default,
            is_required=workflow.is_required,
            execution_order=workflow.execution_order,
            conditions=workflow.conditions,
            is_active=workflow.is_active,
            created_at=workflow.created_at
        )
        for workflow in workflows
    ]

# Theme management endpoints
@router.post("/{project_id}/themes", response_model=ThemeResponse)
async def create_theme(
    project_id: str = Path(...),
    theme_data: ThemeCreate = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create project theme"""
    service = ProjectConfigurationService(db)
    
    # Check project access
    project = service.get_project(project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if (project.owner_id != current_user["user_id"] and
        "admin:projects" not in current_user.get("capabilities", [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Convert Pydantic model to dict for theme config
        theme_config = theme_data.dict(exclude={'theme_name', 'is_default'}, exclude_none=True)
        
        theme = service.create_theme(
            project_id=project_id,
            theme_name=theme_data.theme_name,
            user_id=current_user["user_id"],
            theme_config=theme_config,
            is_default=theme_data.is_default
        )
        
        return ThemeResponse(
            id=theme.id,
            theme_name=theme.theme_name,
            primary_color=theme.primary_color,
            secondary_color=theme.secondary_color,
            accent_color=theme.accent_color,
            background_color=theme.background_color,
            text_color=theme.text_color,
            font_family=theme.font_family,
            logo_url=theme.logo_url,
            brand_name=theme.brand_name,
            is_default=theme.is_default,
            is_active=theme.is_active,
            created_at=theme.created_at
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}/themes/{theme_name}", response_model=ThemeResponse)
async def get_theme(
    project_id: str = Path(...),
    theme_name: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project theme"""
    service = ProjectConfigurationService(db)
    
    # Check project access
    project = service.get_project(project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if (project.owner_id != current_user["user_id"] and 
        not project.is_public and
        "admin:projects" not in current_user.get("capabilities", [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    theme = service.get_theme(project_id=project_id, theme_name=theme_name)
    
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    return ThemeResponse(
        id=theme.id,
        theme_name=theme.theme_name,
        primary_color=theme.primary_color,
        secondary_color=theme.secondary_color,
        accent_color=theme.accent_color,
        background_color=theme.background_color,
        text_color=theme.text_color,
        font_family=theme.font_family,
        logo_url=theme.logo_url,
        brand_name=theme.brand_name,
        is_default=theme.is_default,
        is_active=theme.is_active,
        created_at=theme.created_at
    )

@router.get("/{project_id}/themes", response_model=ThemeResponse)
async def get_default_theme(
    project_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project default theme"""
    service = ProjectConfigurationService(db)
    
    # Check project access
    project = service.get_project(project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if (project.owner_id != current_user["user_id"] and 
        not project.is_public and
        "admin:projects" not in current_user.get("capabilities", [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    theme = service.get_theme(project_id=project_id)  # Gets default theme
    
    if not theme:
        raise HTTPException(status_code=404, detail="No default theme found")
    
    return ThemeResponse(
        id=theme.id,
        theme_name=theme.theme_name,
        primary_color=theme.primary_color,
        secondary_color=theme.secondary_color,
        accent_color=theme.accent_color,
        background_color=theme.background_color,
        text_color=theme.text_color,
        font_family=theme.font_family,
        logo_url=theme.logo_url,
        brand_name=theme.brand_name,
        is_default=theme.is_default,
        is_active=theme.is_active,
        created_at=theme.created_at
    )

# Template management endpoints
@router.get("/templates", response_model=List[Dict[str, Any]])
async def get_configuration_templates(
    template_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get available configuration templates"""
    service = ProjectConfigurationService(db)
    
    templates = service.get_configuration_templates(
        template_type=template_type,
        category=category,
        public_only=True
    )
    
    return [
        {
            "id": template.id,
            "template_name": template.template_name,
            "template_type": template.template_type,
            "template_category": template.template_category,
            "description": template.description,
            "version": template.version,
            "usage_count": template.usage_count,
            "is_featured": template.is_featured
        }
        for template in templates
    ]

@router.get("/templates/regions")
async def get_available_regions(db: Session = Depends(get_db)):
    """Get available template regions"""
    from services.template_service import TemplateService
    template_service = TemplateService(db)
    
    regions = template_service.get_available_regions()
    return {"regions": regions}

@router.get("/templates/regions/{region}")
async def get_templates_by_region(
    region: str = Path(...),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get templates filtered by region and optionally by category"""
    from services.template_service import TemplateService
    template_service = TemplateService(db)
    
    if category:
        templates = template_service.get_templates_by_category_and_region(category, region)
    else:
        templates = template_service.get_templates_by_region(region)
    
    return {"templates": templates}

@router.get("/templates/regions/{region}/categories")
async def get_categories_by_region(
    region: str = Path(...),
    db: Session = Depends(get_db)
):
    """Get available categories for a specific region"""
    from services.template_service import TemplateService
    template_service = TemplateService(db)
    
    categories = template_service.get_available_categories_by_region(region)
    return {"categories": categories}

@router.get("/templates/{template_id}")
async def get_template_details(
    template_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """Get detailed template configuration"""
    from services.template_service import TemplateService
    template_service = TemplateService(db)
    
    template = template_service.get_template_by_id(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"template": template}

@router.post("/{project_id}/apply-template")
async def apply_template_to_project(
    project_id: str = Path(...),
    template_id: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply a template configuration to a project"""
    from services.template_service import TemplateService
    
    service = ProjectConfigurationService(db)
    template_service = TemplateService(db)
    
    # Check project access
    project = service.get_project(project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if (project.owner_id != current_user["user_id"] and
        "admin:projects" not in current_user.get("capabilities", [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get template configuration
    template = template_service.get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    try:
        # Apply template configuration to project
        template_config = template["config"]
        user_id = current_user["user_id"]
        
        # Apply auth configuration
        if "auth" in template_config:
            for key, value in template_config["auth"].items():
                service.set_configuration(
                    project_id=project_id,
                    config_type="auth",
                    config_key=key,
                    config_value=value,
                    user_id=user_id,
                    override_level=5
                )
        
        # Apply UI configuration
        if "ui" in template_config:
            ui_config = template_config["ui"]
            for key, value in ui_config.items():
                if key != "theme":  # Handle theme separately
                    service.set_configuration(
                        project_id=project_id,
                        config_type="ui",
                        config_key=key,
                        config_value=value,
                        user_id=user_id,
                        override_level=5
                    )
            
            # Apply theme if specified
            if "theme" in ui_config:
                theme_name = ui_config["theme"]
                theme_template = template_service.get_theme_template(theme_name)
                
                if theme_template:
                    # Create theme from template
                    service.create_theme(
                        project_id=project_id,
                        theme_name=theme_name,
                        user_id=user_id,
                        theme_config=theme_template,
                        is_default=True
                    )
        
        # Apply workflow configuration
        if "workflow" in template_config:
            workflow_config = template_config["workflow"]
            
            # Set workflow configuration values
            for key, value in workflow_config.items():
                if key not in ["progressive_steps", "progressive_kyc_steps"]:
                    service.set_configuration(
                        project_id=project_id,
                        config_type="workflow",
                        config_key=key,
                        config_value=value,
                        user_id=user_id,
                        override_level=5
                    )
            
            # Create progressive profiling workflow if specified
            if "progressive_steps" in workflow_config or "progressive_kyc_steps" in workflow_config:
                steps = workflow_config.get("progressive_steps") or workflow_config.get("progressive_kyc_steps", [])
                
                service.create_workflow(
                    project_id=project_id,
                    workflow_name="Progressive Profiling",
                    workflow_type="profiling",
                    workflow_steps=steps,
                    user_id=user_id,
                    workflow_config={"template_source": template_id},
                    is_default=True
                )
        
        # Apply integration configuration
        if "integration" in template_config:
            for key, value in template_config["integration"].items():
                service.set_configuration(
                    project_id=project_id,
                    config_type="integration",
                    config_key=key,
                    config_value=value,
                    user_id=user_id,
                    override_level=5
                )
        
        return {
            "message": "Template applied successfully",
            "template_id": template_id,
            "template_name": template["name"],
            "applied_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to apply template: {str(e)}")

@router.get("/templates/indian")
async def get_indian_templates(db: Session = Depends(get_db)):
    """Get templates specifically designed for Indian market"""
    from services.template_service import TemplateService
    template_service = TemplateService(db)
    
    templates = template_service.get_indian_templates()
    return {"templates": templates}

@router.get("/templates/global")
async def get_global_templates(db: Session = Depends(get_db)):
    """Get global templates (non-region specific)"""
    from services.template_service import TemplateService
    template_service = TemplateService(db)
    
    templates = template_service.get_global_templates()
    return {"templates": templates}

@router.delete("/{project_id}")
async def delete_project(
    project_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete project"""
    service = ProjectConfigurationService(db)
    
    # Check project access
    project = service.get_project(project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if (project.owner_id != current_user["user_id"] and
        "admin:projects" not in current_user.get("capabilities", [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = service.delete_project(project_id, current_user["user_id"])
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete project")
    
    return {"message": "Project deleted successfully"}