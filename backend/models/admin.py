"""
Admin Dashboard Models

Database models for admin dashboard functionality including
admin panels, configuration interfaces, and management tools.
"""

from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import enum

from database import Base

class AdminPanelType(enum.Enum):
    """Types of admin panels"""
    PROJECT_CONFIG = "project_config"
    ROLE_MANAGEMENT = "role_management"
    CAPABILITY_MANAGEMENT = "capability_management"
    INTEGRATION_SETUP = "integration_setup"
    USER_MANAGEMENT = "user_management"
    API_KEY_MANAGEMENT = "api_key_management"
    AUDIT_LOGS = "audit_logs"
    SYSTEM_SETTINGS = "system_settings"

class AdminPanel(Base):
    """Admin panel configuration"""
    __tablename__ = "admin_panels"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Panel metadata
    panel_name = Column(String, nullable=False)
    panel_type = Column(String, nullable=False)  # AdminPanelType enum value
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)
    
    # Access control
    tenant_id = Column(String, nullable=True)
    required_roles = Column(JSON, nullable=True)  # List of required roles
    required_capabilities = Column(JSON, nullable=True)  # List of required capabilities
    
    # Panel configuration
    config = Column(JSON, nullable=True)  # Panel-specific configuration
    layout = Column(JSON, nullable=True)  # UI layout configuration
    widgets = Column(JSON, nullable=True)  # Available widgets
    
    # Panel state
    is_enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<AdminPanel(id={self.id}, name={self.panel_name}, type={self.panel_type})>"

class AdminWidget(Base):
    """Admin dashboard widgets"""
    __tablename__ = "admin_widgets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Widget metadata
    widget_name = Column(String, nullable=False)
    widget_type = Column(String, nullable=False)  # chart, table, form, etc.
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Widget configuration
    config = Column(JSON, nullable=True)  # Widget-specific configuration
    data_source = Column(String, nullable=True)  # Data source endpoint
    refresh_interval = Column(Integer, nullable=True)  # Refresh interval in seconds
    
    # Layout
    width = Column(Integer, default=12)  # Grid width (1-12)
    height = Column(Integer, default=4)  # Grid height
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    
    # State
    is_enabled = Column(Boolean, default=True)
    is_visible = Column(Boolean, default=True)
    
    # Relationships
    panel_id = Column(String, ForeignKey("admin_panels.id"), nullable=False)
    panel = relationship("AdminPanel", backref="widgets")
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=False)
    
    def __repr__(self):
        return f"<AdminWidget(id={self.id}, name={self.widget_name}, type={self.widget_type})>"

class IntegrationWizard(Base):
    """Integration setup wizards"""
    __tablename__ = "integration_wizards"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Wizard metadata
    wizard_name = Column(String, nullable=False)
    integration_type = Column(String, nullable=False)  # oauth, api_key, webhook, etc.
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Wizard configuration
    steps = Column(JSON, nullable=False)  # List of wizard steps
    validation_rules = Column(JSON, nullable=True)  # Validation rules per step
    default_values = Column(JSON, nullable=True)  # Default values
    
    # Integration settings
    provider = Column(String, nullable=True)  # Integration provider
    endpoints = Column(JSON, nullable=True)  # API endpoints
    auth_config = Column(JSON, nullable=True)  # Authentication configuration
    
    # State
    is_enabled = Column(Boolean, default=True)
    completion_rate = Column(Integer, default=0)  # Percentage of users who complete
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=False)
    
    def __repr__(self):
        return f"<IntegrationWizard(id={self.id}, name={self.wizard_name}, type={self.integration_type})>"

class AdminAction(Base):
    """Admin actions and operations"""
    __tablename__ = "admin_actions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Action metadata
    action_name = Column(String, nullable=False)
    action_type = Column(String, nullable=False)  # create, update, delete, bulk, etc.
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Action configuration
    endpoint = Column(String, nullable=False)  # API endpoint
    method = Column(String, nullable=False)  # HTTP method
    parameters = Column(JSON, nullable=True)  # Required parameters
    confirmation_required = Column(Boolean, default=False)
    
    # Access control
    required_roles = Column(JSON, nullable=True)
    required_capabilities = Column(JSON, nullable=True)
    
    # UI configuration
    button_style = Column(String, default="primary")  # primary, secondary, danger
    icon = Column(String, nullable=True)
    show_in_toolbar = Column(Boolean, default=True)
    
    # State
    is_enabled = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    
    # Relationships
    panel_id = Column(String, ForeignKey("admin_panels.id"), nullable=False)
    panel = relationship("AdminPanel", backref="actions")
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=False)
    
    def __repr__(self):
        return f"<AdminAction(id={self.id}, name={self.action_name}, type={self.action_type})>"

class AdminDashboard(Base):
    """Admin dashboard configuration"""
    __tablename__ = "admin_dashboards"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Dashboard metadata
    dashboard_name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Dashboard configuration
    layout = Column(JSON, nullable=True)  # Dashboard layout
    panels = Column(JSON, nullable=True)  # List of panel IDs
    theme = Column(String, default="default")
    
    # Access control
    tenant_id = Column(String, nullable=True)
    owner_id = Column(String, nullable=False)
    is_public = Column(Boolean, default=False)
    shared_with = Column(JSON, nullable=True)  # List of user/role IDs
    
    # State
    is_default = Column(Boolean, default=False)
    is_enabled = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<AdminDashboard(id={self.id}, name={self.dashboard_name})>"