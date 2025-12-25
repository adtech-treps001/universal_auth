"""
Theme Management Routes

API endpoints for managing project themes and UI customization.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging

from database import get_db
from services.theme_service import ThemeService
from services.project_service import ProjectConfigurationService
from auth.middleware import get_current_user, require_permission
from models.user import User
from models.project import ProjectTheme

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/themes", tags=["themes"])

# Pydantic models for request/response
class ThemeCreateRequest(BaseModel):
    theme_name: str = Field(..., min_length=1, max_length=100)
    project_id: str = Field(..., min_length=1)
    is_default: bool = False
    
    # Color configuration
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    
    # Typography configuration
    font_family: Optional[str] = None
    font_size_base: Optional[str] = None
    font_weight_normal: Optional[str] = None
    font_weight_bold: Optional[str] = None
    
    # Layout configuration
    border_radius: Optional[str] = None
    spacing_unit: Optional[str] = None
    container_max_width: Optional[str] = None
    
    # Branding configuration
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    brand_name: Optional[str] = None
    
    # Advanced configuration
    custom_css: Optional[str] = None
    css_variables: Optional[Dict[str, str]] = None
    breakpoints: Optional[Dict[str, str]] = None
    mobile_config: Optional[Dict[str, Any]] = None

class ThemeUpdateRequest(BaseModel):
    theme_name: Optional[str] = None
    is_default: Optional[bool] = None
    
    # Color configuration
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    
    # Typography configuration
    font_family: Optional[str] = None
    font_size_base: Optional[str] = None
    font_weight_normal: Optional[str] = None
    font_weight_bold: Optional[str] = None
    
    # Layout configuration
    border_radius: Optional[str] = None
    spacing_unit: Optional[str] = None
    container_max_width: Optional[str] = None
    
    # Branding configuration
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    brand_name: Optional[str] = None
    
    # Advanced configuration
    custom_css: Optional[str] = None
    css_variables: Optional[Dict[str, str]] = None
    breakpoints: Optional[Dict[str, str]] = None
    mobile_config: Optional[Dict[str, Any]] = None

class ThemeTemplateRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    template_name: str = Field(..., min_length=1)

class ThemeResponse(BaseModel):
    id: str
    project_id: str
    theme_name: str
    theme_version: str
    is_default: bool
    is_active: bool
    created_at: str
    updated_at: str
    
    # Theme configuration
    primary_color: Optional[str]
    secondary_color: Optional[str]
    accent_color: Optional[str]
    background_color: Optional[str]
    text_color: Optional[str]
    font_family: Optional[str]
    font_size_base: Optional[str]
    border_radius: Optional[str]
    spacing_unit: Optional[str]
    logo_url: Optional[str]
    brand_name: Optional[str]

class ThemePreviewResponse(BaseModel):
    colors: Dict[str, Any]
    typography: Dict[str, Any]
    layout: Dict[str, Any]
    components: Dict[str, Any]

class AccessibilityValidationResponse(BaseModel):
    is_accessible: bool
    score: int
    issues: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]

@router.post("/", response_model=ThemeResponse)
async def create_theme(
    request: ThemeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new theme for a project"""
    
    # Check project access
    project_service = ProjectConfigurationService(db)
    project = project_service.get_project(request.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions (project owner or admin)
    if project.owner_id != current_user.id:
        await require_permission(current_user, "project.theme.create", db)
    
    try:
        theme_service = ThemeService(db)
        
        # Convert request to theme config
        theme_config = request.dict(exclude={'theme_name', 'project_id', 'is_default'})
        # Remove None values
        theme_config = {k: v for k, v in theme_config.items() if v is not None}
        
        theme = theme_service.create_theme(
            project_id=request.project_id,
            theme_name=request.theme_name,
            user_id=current_user.id,
            theme_config=theme_config,
            is_default=request.is_default
        )
        
        return ThemeResponse(
            id=theme.id,
            project_id=theme.project_id,
            theme_name=theme.theme_name,
            theme_version=theme.theme_version,
            is_default=theme.is_default,
            is_active=theme.is_active,
            created_at=theme.created_at.isoformat(),
            updated_at=theme.updated_at.isoformat(),
            primary_color=theme.primary_color,
            secondary_color=theme.secondary_color,
            accent_color=theme.accent_color,
            background_color=theme.background_color,
            text_color=theme.text_color,
            font_family=theme.font_family,
            font_size_base=theme.font_size_base,
            border_radius=theme.border_radius,
            spacing_unit=theme.spacing_unit,
            logo_url=theme.logo_url,
            brand_name=theme.brand_name
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating theme: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create theme"
        )

@router.get("/project/{project_id}", response_model=List[ThemeResponse])
async def get_project_themes(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all themes for a project"""
    
    # Check project access
    project_service = ProjectConfigurationService(db)
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions
    if project.owner_id != current_user.id:
        await require_permission(current_user, "project.theme.read", db)
    
    try:
        theme_service = ThemeService(db)
        themes = theme_service.get_project_themes(project_id)
        
        return [
            ThemeResponse(
                id=theme.id,
                project_id=theme.project_id,
                theme_name=theme.theme_name,
                theme_version=theme.theme_version,
                is_default=theme.is_default,
                is_active=theme.is_active,
                created_at=theme.created_at.isoformat(),
                updated_at=theme.updated_at.isoformat(),
                primary_color=theme.primary_color,
                secondary_color=theme.secondary_color,
                accent_color=theme.accent_color,
                background_color=theme.background_color,
                text_color=theme.text_color,
                font_family=theme.font_family,
                font_size_base=theme.font_size_base,
                border_radius=theme.border_radius,
                spacing_unit=theme.spacing_unit,
                logo_url=theme.logo_url,
                brand_name=theme.brand_name
            )
            for theme in themes
        ]
        
    except Exception as e:
        logger.error(f"Error getting project themes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get themes"
        )

@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_theme(
    theme_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific theme"""
    
    # Get theme
    theme = db.query(ProjectTheme).filter(ProjectTheme.id == theme_id).first()
    
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found"
        )
    
    # Check project access
    project_service = ProjectConfigurationService(db)
    project = project_service.get_project(theme.project_id)
    if project.owner_id != current_user.id:
        await require_permission(current_user, "project.theme.read", db)
    
    return ThemeResponse(
        id=theme.id,
        project_id=theme.project_id,
        theme_name=theme.theme_name,
        theme_version=theme.theme_version,
        is_default=theme.is_default,
        is_active=theme.is_active,
        created_at=theme.created_at.isoformat(),
        updated_at=theme.updated_at.isoformat(),
        primary_color=theme.primary_color,
        secondary_color=theme.secondary_color,
        accent_color=theme.accent_color,
        background_color=theme.background_color,
        text_color=theme.text_color,
        font_family=theme.font_family,
        font_size_base=theme.font_size_base,
        border_radius=theme.border_radius,
        spacing_unit=theme.spacing_unit,
        logo_url=theme.logo_url,
        brand_name=theme.brand_name
    )

@router.put("/{theme_id}", response_model=ThemeResponse)
async def update_theme(
    theme_id: str,
    request: ThemeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing theme"""
    
    theme_service = ThemeService(db)
    
    # Get existing theme
    theme = db.query(ProjectTheme).filter(ProjectTheme.id == theme_id).first()
    
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found"
        )
    
    # Check project access
    project_service = ProjectConfigurationService(db)
    project = project_service.get_project(theme.project_id)
    if project.owner_id != current_user.id:
        await require_permission(current_user, "project.theme.update", db)
    
    try:
        # Convert request to theme config
        theme_config = request.dict(exclude={'theme_name', 'is_default'})
        # Remove None values
        theme_config = {k: v for k, v in theme_config.items() if v is not None}
        
        # Handle special fields
        if request.theme_name is not None:
            theme_config['theme_name'] = request.theme_name
        if request.is_default is not None:
            theme_config['is_default'] = request.is_default
        
        updated_theme = theme_service.update_theme(
            theme_id=theme_id,
            user_id=current_user.id,
            theme_config=theme_config
        )
        
        if not updated_theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )
        
        return ThemeResponse(
            id=updated_theme.id,
            project_id=updated_theme.project_id,
            theme_name=updated_theme.theme_name,
            theme_version=updated_theme.theme_version,
            is_default=updated_theme.is_default,
            is_active=updated_theme.is_active,
            created_at=updated_theme.created_at.isoformat(),
            updated_at=updated_theme.updated_at.isoformat(),
            primary_color=updated_theme.primary_color,
            secondary_color=updated_theme.secondary_color,
            accent_color=updated_theme.accent_color,
            background_color=updated_theme.background_color,
            text_color=updated_theme.text_color,
            font_family=updated_theme.font_family,
            font_size_base=updated_theme.font_size_base,
            border_radius=updated_theme.border_radius,
            spacing_unit=updated_theme.spacing_unit,
            logo_url=updated_theme.logo_url,
            brand_name=updated_theme.brand_name
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating theme: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update theme"
        )

@router.get("/{theme_id}/css")
async def get_theme_css(
    theme_id: str,
    include_responsive: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate CSS for a theme"""
    
    theme_service = ThemeService(db)
    
    # Get theme
    theme = db.query(ProjectTheme).filter(ProjectTheme.id == theme_id).first()
    
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found"
        )
    
    # Check project access
    project_service = ProjectConfigurationService(db)
    project = project_service.get_project(theme.project_id)
    if project.owner_id != current_user.id:
        await require_permission(current_user, "project.theme.read", db)
    
    try:
        css = theme_service.generate_css(theme, include_responsive)
        
        return Response(
            content=css,
            media_type="text/css",
            headers={"Content-Disposition": f"inline; filename=theme-{theme.theme_name}.css"}
        )
        
    except Exception as e:
        logger.error(f"Error generating theme CSS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate CSS"
        )

@router.post("/preview", response_model=ThemePreviewResponse)
async def preview_theme(
    request: ThemeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate theme preview without saving"""
    
    try:
        theme_service = ThemeService(db)
        
        # Convert request to theme config
        theme_config = request.dict(exclude={'theme_name', 'project_id', 'is_default'})
        # Remove None values
        theme_config = {k: v for k, v in theme_config.items() if v is not None}
        
        preview = theme_service.generate_theme_preview(theme_config)
        
        return ThemePreviewResponse(**preview)
        
    except Exception as e:
        logger.error(f"Error generating theme preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate preview"
        )

@router.post("/template", response_model=ThemeResponse)
async def apply_theme_template(
    request: ThemeTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Apply a theme template to create a new theme"""
    
    # Check project access
    project_service = ProjectConfigurationService(db)
    project = project_service.get_project(request.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions
    if project.owner_id != current_user.id:
        await require_permission(current_user, "project.theme.create", db)
    
    try:
        theme_service = ThemeService(db)
        theme = theme_service.apply_theme_template(
            project_id=request.project_id,
            template_name=request.template_name,
            user_id=current_user.id
        )
        
        return ThemeResponse(
            id=theme.id,
            project_id=theme.project_id,
            theme_name=theme.theme_name,
            theme_version=theme.theme_version,
            is_default=theme.is_default,
            is_active=theme.is_active,
            created_at=theme.created_at.isoformat(),
            updated_at=theme.updated_at.isoformat(),
            primary_color=theme.primary_color,
            secondary_color=theme.secondary_color,
            accent_color=theme.accent_color,
            background_color=theme.background_color,
            text_color=theme.text_color,
            font_family=theme.font_family,
            font_size_base=theme.font_size_base,
            border_radius=theme.border_radius,
            spacing_unit=theme.spacing_unit,
            logo_url=theme.logo_url,
            brand_name=theme.brand_name
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error applying theme template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply template"
        )

@router.get("/{theme_id}/accessibility", response_model=AccessibilityValidationResponse)
async def validate_theme_accessibility(
    theme_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate theme for accessibility compliance"""
    
    theme_service = ThemeService(db)
    
    # Get theme
    theme = db.query(ProjectTheme).filter(ProjectTheme.id == theme_id).first()
    
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found"
        )
    
    # Check project access
    project_service = ProjectConfigurationService(db)
    project = project_service.get_project(theme.project_id)
    if project.owner_id != current_user.id:
        await require_permission(current_user, "project.theme.read", db)
    
    try:
        validation_result = theme_service.validate_theme_accessibility(theme)
        
        return AccessibilityValidationResponse(**validation_result)
        
    except Exception as e:
        logger.error(f"Error validating theme accessibility: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate accessibility"
        )

@router.delete("/{theme_id}")
async def delete_theme(
    theme_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a theme"""
    
    # Get theme
    theme = db.query(ProjectTheme).filter(ProjectTheme.id == theme_id).first()
    
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found"
        )
    
    # Check project access
    project_service = ProjectConfigurationService(db)
    project = project_service.get_project(theme.project_id)
    if project.owner_id != current_user.id:
        await require_permission(current_user, "project.theme.delete", db)
    
    # Prevent deletion of default theme if it's the only one
    if theme.is_default:
        theme_service = ThemeService(db)
        all_themes = theme_service.get_project_themes(theme.project_id)
        if len(all_themes) == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only theme for a project"
            )
    
    try:
        theme.is_active = False
        db.commit()
        
        return {"message": "Theme deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting theme: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete theme"
        )

@router.get("/templates/list")
async def list_theme_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List available theme templates"""
    
    try:
        theme_service = ThemeService(db)
        template_names = theme_service.template_service.list_theme_template_names()
        
        templates = []
        for name in template_names:
            template = theme_service.template_service.get_theme_template(name)
            if template:
                templates.append({
                    "name": name,
                    "theme_name": template.get("theme_name", name),
                    "description": template.get("description", ""),
                    "primary_color": template.get("primary_color"),
                    "secondary_color": template.get("secondary_color"),
                    "font_family": template.get("font_family")
                })
        
        return {"templates": templates}
        
    except Exception as e:
        logger.error(f"Error listing theme templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list templates"
        )