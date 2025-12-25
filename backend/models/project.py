"""
Project Configuration Models

This module defines the database models for project-specific configurations,
workflows, and customization settings.
"""

from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid

from database import Base

class Project(Base):
    """Main project model"""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Project metadata
    owner_id = Column(String, nullable=False)  # User ID of project owner
    tenant_id = Column(String, nullable=True)  # Optional tenant association
    
    # Project status
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    configurations = relationship("ProjectConfiguration", back_populates="project", cascade="all, delete-orphan")
    workflows = relationship("ProjectWorkflow", back_populates="project", cascade="all, delete-orphan")
    themes = relationship("ProjectTheme", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, slug={self.slug})>"

class ProjectConfiguration(Base):
    """Project-specific configuration settings"""
    __tablename__ = "project_configurations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Configuration metadata
    config_type = Column(String, nullable=False)  # 'auth', 'ui', 'workflow', 'integration'
    config_key = Column(String, nullable=False)
    config_value = Column(JSON, nullable=False)
    
    # Configuration inheritance
    inherits_from = Column(String, nullable=True)  # Parent configuration ID
    override_level = Column(Integer, default=0)  # 0=base, higher=more specific
    
    # Configuration status
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)  # Prevents modification
    
    # Validation and schema
    schema_version = Column(String, default="1.0")
    validation_rules = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=True)  # User ID who created
    updated_by = Column(String, nullable=True)  # User ID who last updated
    
    # Relationships
    project = relationship("Project", back_populates="configurations")
    
    def __repr__(self):
        return f"<ProjectConfiguration(project_id={self.project_id}, type={self.config_type}, key={self.config_key})>"

class ProjectWorkflow(Base):
    """Project workflow configurations"""
    __tablename__ = "project_workflows"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Workflow metadata
    workflow_name = Column(String, nullable=False)
    workflow_type = Column(String, nullable=False)  # 'authentication', 'onboarding', 'approval'
    workflow_version = Column(String, default="1.0")
    
    # Workflow definition
    workflow_steps = Column(JSON, nullable=False)  # Array of step definitions
    workflow_config = Column(JSON, default=dict)  # Workflow-specific configuration
    
    # Workflow behavior
    is_default = Column(Boolean, default=False)
    is_required = Column(Boolean, default=False)
    execution_order = Column(Integer, default=0)
    
    # Conditional execution
    conditions = Column(JSON, nullable=True)  # Conditions for workflow execution
    triggers = Column(JSON, nullable=True)  # Events that trigger workflow
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="workflows")
    
    def __repr__(self):
        return f"<ProjectWorkflow(project_id={self.project_id}, name={self.workflow_name}, type={self.workflow_type})>"

class ProjectTheme(Base):
    """Project theme and UI customization"""
    __tablename__ = "project_themes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Theme metadata
    theme_name = Column(String, nullable=False)
    theme_version = Column(String, default="1.0")
    is_default = Column(Boolean, default=False)
    
    # Color scheme
    primary_color = Column(String, nullable=True)  # Hex color
    secondary_color = Column(String, nullable=True)
    accent_color = Column(String, nullable=True)
    background_color = Column(String, nullable=True)
    text_color = Column(String, nullable=True)
    
    # Typography
    font_family = Column(String, nullable=True)
    font_size_base = Column(String, nullable=True)
    font_weight_normal = Column(String, nullable=True)
    font_weight_bold = Column(String, nullable=True)
    
    # Layout and spacing
    border_radius = Column(String, nullable=True)
    spacing_unit = Column(String, nullable=True)
    container_max_width = Column(String, nullable=True)
    
    # Branding
    logo_url = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    brand_name = Column(String, nullable=True)
    
    # Custom CSS
    custom_css = Column(Text, nullable=True)
    css_variables = Column(JSON, nullable=True)  # CSS custom properties
    
    # Responsive settings
    breakpoints = Column(JSON, nullable=True)
    mobile_config = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="themes")
    
    def __repr__(self):
        return f"<ProjectTheme(project_id={self.project_id}, name={self.theme_name})>"

class ConfigurationTemplate(Base):
    """Templates for common configuration patterns"""
    __tablename__ = "configuration_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Template metadata
    template_name = Column(String, nullable=False)
    template_type = Column(String, nullable=False)  # 'auth', 'workflow', 'theme'
    template_category = Column(String, nullable=True)  # 'enterprise', 'startup', 'saas'
    
    # Template definition
    template_config = Column(JSON, nullable=False)
    default_values = Column(JSON, nullable=True)
    required_fields = Column(JSON, nullable=True)
    
    # Template metadata
    description = Column(Text, nullable=True)
    documentation_url = Column(String, nullable=True)
    version = Column(String, default="1.0")
    
    # Template status
    is_public = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<ConfigurationTemplate(name={self.template_name}, type={self.template_type})>"

class ProjectConfigurationHistory(Base):
    """History of configuration changes"""
    __tablename__ = "project_configuration_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False)
    configuration_id = Column(String, nullable=False)
    
    # Change metadata
    change_type = Column(String, nullable=False)  # 'create', 'update', 'delete'
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    
    # Change context
    changed_by = Column(String, nullable=False)  # User ID
    change_reason = Column(Text, nullable=True)
    change_source = Column(String, nullable=True)  # 'ui', 'api', 'import'
    
    # Timestamps
    changed_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<ProjectConfigurationHistory(project_id={self.project_id}, type={self.change_type})>"