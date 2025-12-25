"""
Template Service

This service manages configuration templates, workflow templates,
and theme templates for project setup.
"""

import yaml
import os
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models.project import ConfigurationTemplate
import logging

logger = logging.getLogger(__name__)

class TemplateService:
    """Service for managing project templates"""
    
    def __init__(self, db: Session, templates_path: str = None):
        self.db = db
        if templates_path is None:
            templates_path = os.path.join(
                os.path.dirname(__file__), 
                '../../config/project/templates.yaml'
            )
        self.templates_path = templates_path
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from YAML file"""
        try:
            with open(self.templates_path, 'r') as f:
                self.template_data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Templates file not found: {self.templates_path}")
            self.template_data = {"templates": {}, "workflow_templates": {}, "theme_templates": {}}
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            self.template_data = {"templates": {}, "workflow_templates": {}, "theme_templates": {}}
    
    def sync_templates_to_database(self):
        """Sync YAML templates to database"""
        templates_synced = 0
        
        # Sync main configuration templates
        for template_id, template_config in self.template_data.get("templates", {}).items():
            existing = self.db.query(ConfigurationTemplate).filter(
                ConfigurationTemplate.template_name == template_config["template_name"]
            ).first()
            
            if existing:
                # Update existing template
                existing.template_config = template_config["template_config"]
                existing.description = template_config.get("description")
                existing.version = template_config.get("version", "1.0")
                existing.template_category = template_config.get("template_category")
                existing.is_featured = template_config.get("is_featured", False)
            else:
                # Create new template
                template = ConfigurationTemplate(
                    template_name=template_config["template_name"],
                    template_type=template_config["template_type"],
                    template_category=template_config.get("template_category"),
                    template_config=template_config["template_config"],
                    description=template_config.get("description"),
                    version=template_config.get("version", "1.0"),
                    is_featured=template_config.get("is_featured", False),
                    is_public=True
                )
                self.db.add(template)
            
            templates_synced += 1
        
        # Sync workflow templates
        for workflow_id, workflow_config in self.template_data.get("workflow_templates", {}).items():
            template_name = f"Workflow: {workflow_config['workflow_name']}"
            
            existing = self.db.query(ConfigurationTemplate).filter(
                ConfigurationTemplate.template_name == template_name
            ).first()
            
            workflow_template_config = {
                "workflow": {
                    workflow_config["workflow_type"]: {
                        "name": workflow_config["workflow_name"],
                        "steps": workflow_config["workflow_steps"],
                        "description": workflow_config.get("description", "")
                    }
                }
            }
            
            if existing:
                existing.template_config = workflow_template_config
                existing.description = workflow_config.get("description")
            else:
                template = ConfigurationTemplate(
                    template_name=template_name,
                    template_type="workflow",
                    template_category="workflow",
                    template_config=workflow_template_config,
                    description=workflow_config.get("description"),
                    version="1.0",
                    is_public=True
                )
                self.db.add(template)
            
            templates_synced += 1
        
        # Sync theme templates
        for theme_id, theme_config in self.template_data.get("theme_templates", {}).items():
            template_name = f"Theme: {theme_config['theme_name']}"
            
            existing = self.db.query(ConfigurationTemplate).filter(
                ConfigurationTemplate.template_name == template_name
            ).first()
            
            theme_template_config = {
                "theme": {
                    "default": theme_config
                }
            }
            
            if existing:
                existing.template_config = theme_template_config
                existing.description = theme_config.get("description")
            else:
                template = ConfigurationTemplate(
                    template_name=template_name,
                    template_type="theme",
                    template_category="theme",
                    template_config=theme_template_config,
                    description=theme_config.get("description"),
                    version="1.0",
                    is_public=True
                )
                self.db.add(template)
            
            templates_synced += 1
        
        self.db.commit()
        logger.info(f"Synced {templates_synced} templates to database")
        return templates_synced
    
    def get_template_by_name(self, template_name: str) -> Optional[ConfigurationTemplate]:
        """Get template by name"""
        return self.db.query(ConfigurationTemplate).filter(
            ConfigurationTemplate.template_name == template_name
        ).first()
    
    def get_templates_by_type(self, template_type: str) -> List[ConfigurationTemplate]:
        """Get templates by type"""
        return self.db.query(ConfigurationTemplate).filter(
            ConfigurationTemplate.template_type == template_type,
            ConfigurationTemplate.is_public == True
        ).order_by(
            ConfigurationTemplate.is_featured.desc(),
            ConfigurationTemplate.usage_count.desc()
        ).all()
    
    def get_templates_by_category(self, category: str) -> List[ConfigurationTemplate]:
        """Get templates by category"""
        return self.db.query(ConfigurationTemplate).filter(
            ConfigurationTemplate.template_category == category,
            ConfigurationTemplate.is_public == True
        ).order_by(
            ConfigurationTemplate.is_featured.desc(),
            ConfigurationTemplate.usage_count.desc()
        ).all()
    
    def get_featured_templates(self) -> List[ConfigurationTemplate]:
        """Get featured templates"""
        return self.db.query(ConfigurationTemplate).filter(
            ConfigurationTemplate.is_featured == True,
            ConfigurationTemplate.is_public == True
        ).order_by(ConfigurationTemplate.usage_count.desc()).all()
    
    def create_custom_template(self, template_name: str, template_type: str,
                             template_config: Dict[str, Any], user_id: str,
                             description: str = None, category: str = None,
                             is_public: bool = False) -> ConfigurationTemplate:
        """Create custom template"""
        template = ConfigurationTemplate(
            template_name=template_name,
            template_type=template_type,
            template_category=category,
            template_config=template_config,
            description=description,
            version="1.0",
            is_public=is_public,
            created_by=user_id
        )
        
        self.db.add(template)
        self.db.commit()
        
        logger.info(f"Created custom template '{template_name}' by user {user_id}")
        return template
    
    def get_workflow_templates(self) -> Dict[str, Any]:
        """Get workflow templates from YAML"""
        return self.template_data.get("workflow_templates", {})
    
    def get_theme_templates(self) -> Dict[str, Any]:
        """Get theme templates from YAML"""
        return self.template_data.get("theme_templates", {})
    
    def get_theme_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get specific theme template by name
        
        Args:
            template_name: Name of the theme template
            
        Returns:
            Theme template configuration or None if not found
        """
        theme_templates = self.get_theme_templates()
        return theme_templates.get(template_name)
    
    def list_theme_template_names(self) -> List[str]:
        """
        Get list of available theme template names
        
        Returns:
            List of theme template names
        """
        theme_templates = self.get_theme_templates()
        return list(theme_templates.keys())
    
    def get_workflow_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get specific workflow template by name
        
        Args:
            template_name: Name of the workflow template
            
        Returns:
            Workflow template configuration or None if not found
        """
        workflow_templates = self.get_workflow_templates()
        return workflow_templates.get(template_name)
    
    def get_template_preview(self, template_id: str) -> Dict[str, Any]:
        """Get template preview data"""
        template = self.db.query(ConfigurationTemplate).filter(
            ConfigurationTemplate.id == template_id
        ).first()
        
        if not template:
            return None
        
        preview = {
            "id": template.id,
            "name": template.template_name,
            "type": template.template_type,
            "category": template.template_category,
            "description": template.description,
            "version": template.version,
            "is_featured": template.is_featured,
            "usage_count": template.usage_count,
            "configuration_preview": self._generate_config_preview(template.template_config)
        }
        
        return preview
    
    def _generate_config_preview(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a preview of template configuration"""
        preview = {}
        
        for section, section_config in config.items():
            if isinstance(section_config, dict):
                preview[section] = {
                    "keys": list(section_config.keys()),
                    "count": len(section_config)
                }
            else:
                preview[section] = {"value": str(section_config)[:100]}
        
        return preview
    
    def validate_template_config(self, template_config: Dict[str, Any], 
                                template_type: str) -> Dict[str, Any]:
        """Validate template configuration"""
        errors = []
        warnings = []
        
        # Basic validation
        if not isinstance(template_config, dict):
            errors.append("Template configuration must be a dictionary")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Type-specific validation
        if template_type == "full":
            required_sections = ["auth", "ui", "workflow"]
            for section in required_sections:
                if section not in template_config:
                    warnings.append(f"Missing recommended section: {section}")
        
        elif template_type == "workflow":
            if "workflow" not in template_config:
                errors.append("Workflow templates must have a 'workflow' section")
        
        elif template_type == "theme":
            if "theme" not in template_config:
                errors.append("Theme templates must have a 'theme' section")
        
        # Validate auth section if present
        if "auth" in template_config:
            auth_config = template_config["auth"]
            if "oauth_providers" in auth_config:
                valid_providers = ["google", "github", "facebook", "microsoft", "apple", "linkedin"]
                for provider in auth_config["oauth_providers"]:
                    if provider not in valid_providers:
                        warnings.append(f"Unknown OAuth provider: {provider}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def export_template(self, template_id: str) -> Dict[str, Any]:
        """Export template as portable configuration"""
        template = self.db.query(ConfigurationTemplate).filter(
            ConfigurationTemplate.id == template_id
        ).first()
        
        if not template:
            return None
        
        return {
            "template_name": template.template_name,
            "template_type": template.template_type,
            "template_category": template.template_category,
            "description": template.description,
            "version": template.version,
            "template_config": template.template_config,
            "exported_at": template.updated_at.isoformat(),
            "export_version": "1.0"
        }
    
    def import_template(self, template_data: Dict[str, Any], user_id: str,
                       is_public: bool = False) -> ConfigurationTemplate:
        """Import template from exported data"""
        # Validate import data
        required_fields = ["template_name", "template_type", "template_config"]
        for field in required_fields:
            if field not in template_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate configuration
        validation = self.validate_template_config(
            template_data["template_config"],
            template_data["template_type"]
        )
        
        if not validation["valid"]:
            raise ValueError(f"Invalid template configuration: {validation['errors']}")
        
        # Create template
        template = ConfigurationTemplate(
            template_name=template_data["template_name"],
            template_type=template_data["template_type"],
            template_category=template_data.get("template_category"),
            template_config=template_data["template_config"],
            description=template_data.get("description"),
            version=template_data.get("version", "1.0"),
            is_public=is_public,
            created_by=user_id
        )
        
        self.db.add(template)
        self.db.commit()
        
        logger.info(f"Imported template '{template.template_name}' by user {user_id}")
        return template
    
    def get_templates_by_region(self, region: str) -> List[Dict[str, Any]]:
        """Get templates filtered by region"""
        templates = []
        
        for template_id, template_config in self.template_data.get("templates", {}).items():
            template_region = template_config.get("region", "global")
            if template_region == region or template_region == "global":
                templates.append({
                    "id": template_id,
                    "name": template_config["template_name"],
                    "type": template_config["template_type"],
                    "category": template_config.get("template_category"),
                    "description": template_config.get("description"),
                    "region": template_region,
                    "is_featured": template_config.get("is_featured", False),
                    "config": template_config["template_config"]
                })
        
        # Sort by featured first, then by name
        templates.sort(key=lambda x: (not x["is_featured"], x["name"]))
        return templates
    
    def get_indian_templates(self) -> List[Dict[str, Any]]:
        """Get templates specifically designed for Indian market"""
        return self.get_templates_by_region("india")
    
    def get_global_templates(self) -> List[Dict[str, Any]]:
        """Get global templates (non-region specific)"""
        templates = []
        
        for template_id, template_config in self.template_data.get("templates", {}).items():
            template_region = template_config.get("region", "global")
            if template_region == "global":
                templates.append({
                    "id": template_id,
                    "name": template_config["template_name"],
                    "type": template_config["template_type"],
                    "category": template_config.get("template_category"),
                    "description": template_config.get("description"),
                    "region": template_region,
                    "is_featured": template_config.get("is_featured", False),
                    "config": template_config["template_config"]
                })
        
        # Sort by featured first, then by name
        templates.sort(key=lambda x: (not x["is_featured"], x["name"]))
        return templates
    
    def get_templates_by_category_and_region(self, category: str, region: str = None) -> List[Dict[str, Any]]:
        """Get templates filtered by category and optionally by region"""
        templates = []
        
        for template_id, template_config in self.template_data.get("templates", {}).items():
            template_category = template_config.get("template_category")
            template_region = template_config.get("region", "global")
            
            # Check category match
            if template_category != category:
                continue
            
            # Check region match if specified
            if region and template_region != region and template_region != "global":
                continue
            
            templates.append({
                "id": template_id,
                "name": template_config["template_name"],
                "type": template_config["template_type"],
                "category": template_category,
                "description": template_config.get("description"),
                "region": template_region,
                "is_featured": template_config.get("is_featured", False),
                "config": template_config["template_config"]
            })
        
        # Sort by featured first, then by name
        templates.sort(key=lambda x: (not x["is_featured"], x["name"]))
        return templates
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get specific template by ID from YAML configuration"""
        template_config = self.template_data.get("templates", {}).get(template_id)
        
        if not template_config:
            return None
        
        return {
            "id": template_id,
            "name": template_config["template_name"],
            "type": template_config["template_type"],
            "category": template_config.get("template_category"),
            "description": template_config.get("description"),
            "region": template_config.get("region", "global"),
            "is_featured": template_config.get("is_featured", False),
            "version": template_config.get("version", "1.0"),
            "config": template_config["template_config"]
        }
    
    def get_available_regions(self) -> List[str]:
        """Get list of available regions from templates"""
        regions = set()
        
        for template_config in self.template_data.get("templates", {}).values():
            region = template_config.get("region", "global")
            regions.add(region)
        
        # Sort with global first, then alphabetically
        sorted_regions = sorted(regions, key=lambda x: (x != "global", x))
        return sorted_regions
    
    def get_available_categories_by_region(self, region: str = None) -> List[str]:
        """Get available categories, optionally filtered by region"""
        categories = set()
        
        for template_config in self.template_data.get("templates", {}).values():
            template_region = template_config.get("region", "global")
            template_category = template_config.get("template_category")
            
            # Check region match if specified
            if region and template_region != region and template_region != "global":
                continue
            
            if template_category:
                categories.add(template_category)
        
        return sorted(categories)