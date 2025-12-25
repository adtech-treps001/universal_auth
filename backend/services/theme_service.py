"""
Theme Service

This service handles theme configuration, CSS generation, and theme application
for project-specific UI customization.
"""

from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
import json
import re
import logging
from datetime import datetime

from models.project import Project, ProjectTheme
from services.template_service import TemplateService

logger = logging.getLogger(__name__)

class ThemeService:
    """Service for managing project themes and UI customization"""
    
    def __init__(self, db: Session):
        self.db = db
        self.template_service = TemplateService(db)
    
    def create_theme(self, project_id: str, theme_name: str, user_id: str,
                    theme_config: Dict[str, Any], is_default: bool = False) -> ProjectTheme:
        """
        Create a new theme for a project
        
        Args:
            project_id: Project ID
            theme_name: Theme name
            user_id: User creating the theme
            theme_config: Theme configuration dictionary
            is_default: Whether this should be the default theme
            
        Returns:
            Created theme
        """
        # Validate theme configuration
        validated_config = self._validate_theme_config(theme_config)
        
        # If setting as default, unset other defaults
        if is_default:
            self.db.query(ProjectTheme).filter(
                and_(
                    ProjectTheme.project_id == project_id,
                    ProjectTheme.is_default == True
                )
            ).update({ProjectTheme.is_default: False})
        
        # Create theme with validated configuration
        theme = ProjectTheme(
            project_id=project_id,
            theme_name=theme_name,
            is_default=is_default,
            created_by=user_id,
            **validated_config
        )
        
        self.db.add(theme)
        self.db.commit()
        
        logger.info(f"Created theme '{theme_name}' for project {project_id}")
        return theme
    
    def update_theme(self, theme_id: str, user_id: str, 
                    theme_config: Dict[str, Any]) -> Optional[ProjectTheme]:
        """
        Update an existing theme
        
        Args:
            theme_id: Theme ID
            user_id: User updating the theme
            theme_config: Updated theme configuration
            
        Returns:
            Updated theme or None if not found
        """
        theme = self.db.query(ProjectTheme).filter(ProjectTheme.id == theme_id).first()
        if not theme:
            return None
        
        # Validate theme configuration
        validated_config = self._validate_theme_config(theme_config)
        
        # Update theme fields
        for field, value in validated_config.items():
            if hasattr(theme, field):
                setattr(theme, field, value)
        
        theme.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Updated theme {theme_id}")
        return theme
    
    def get_theme(self, project_id: str, theme_name: str = None) -> Optional[ProjectTheme]:
        """
        Get theme by project and name (or default theme)
        
        Args:
            project_id: Project ID
            theme_name: Optional theme name (gets default if not specified)
            
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
    
    def get_project_themes(self, project_id: str) -> List[ProjectTheme]:
        """
        Get all themes for a project
        
        Args:
            project_id: Project ID
            
        Returns:
            List of themes
        """
        return self.db.query(ProjectTheme).filter(
            ProjectTheme.project_id == project_id,
            ProjectTheme.is_active == True
        ).order_by(ProjectTheme.is_default.desc(), ProjectTheme.theme_name).all()
    
    def generate_css(self, theme: ProjectTheme, include_responsive: bool = True) -> str:
        """
        Generate CSS from theme configuration
        
        Args:
            theme: Theme object
            include_responsive: Whether to include responsive breakpoints
            
        Returns:
            Generated CSS string
        """
        css_parts = []
        
        # CSS Custom Properties (CSS Variables)
        css_parts.append(":root {")
        
        # Color variables
        if theme.primary_color:
            css_parts.append(f"  --color-primary: {theme.primary_color};")
        if theme.secondary_color:
            css_parts.append(f"  --color-secondary: {theme.secondary_color};")
        if theme.accent_color:
            css_parts.append(f"  --color-accent: {theme.accent_color};")
        if theme.background_color:
            css_parts.append(f"  --color-background: {theme.background_color};")
        if theme.text_color:
            css_parts.append(f"  --color-text: {theme.text_color};")
        
        # Typography variables
        if theme.font_family:
            css_parts.append(f"  --font-family: {theme.font_family};")
        if theme.font_size_base:
            css_parts.append(f"  --font-size-base: {theme.font_size_base};")
        if theme.font_weight_normal:
            css_parts.append(f"  --font-weight-normal: {theme.font_weight_normal};")
        if theme.font_weight_bold:
            css_parts.append(f"  --font-weight-bold: {theme.font_weight_bold};")
        
        # Layout variables
        if theme.border_radius:
            css_parts.append(f"  --border-radius: {theme.border_radius};")
        if theme.spacing_unit:
            css_parts.append(f"  --spacing-unit: {theme.spacing_unit};")
        if theme.container_max_width:
            css_parts.append(f"  --container-max-width: {theme.container_max_width};")
        
        # Custom CSS variables
        if theme.css_variables:
            for var_name, var_value in theme.css_variables.items():
                css_parts.append(f"  {var_name}: {var_value};")
        
        css_parts.append("}")
        css_parts.append("")
        
        # Base styles
        css_parts.extend(self._generate_base_styles(theme))
        
        # Component styles
        css_parts.extend(self._generate_component_styles(theme))
        
        # Responsive styles
        if include_responsive and theme.breakpoints:
            css_parts.extend(self._generate_responsive_styles(theme))
        
        # Custom CSS
        if theme.custom_css:
            css_parts.append("/* Custom CSS */")
            css_parts.append(theme.custom_css)
        
        return "\n".join(css_parts)
    
    def generate_theme_preview(self, theme_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate theme preview data for UI
        
        Args:
            theme_config: Theme configuration
            
        Returns:
            Preview data with color swatches, typography samples, etc.
        """
        preview = {
            "colors": {},
            "typography": {},
            "layout": {},
            "components": {}
        }
        
        # Color preview
        color_fields = ['primary_color', 'secondary_color', 'accent_color', 
                       'background_color', 'text_color']
        for field in color_fields:
            if field in theme_config and theme_config[field]:
                preview["colors"][field] = {
                    "value": theme_config[field],
                    "contrast_ratio": self._calculate_contrast_ratio(
                        theme_config[field], theme_config.get('background_color', '#FFFFFF')
                    )
                }
        
        # Typography preview
        typography_fields = ['font_family', 'font_size_base', 'font_weight_normal', 'font_weight_bold']
        for field in typography_fields:
            if field in theme_config and theme_config[field]:
                preview["typography"][field] = theme_config[field]
        
        # Layout preview
        layout_fields = ['border_radius', 'spacing_unit', 'container_max_width']
        for field in layout_fields:
            if field in theme_config and theme_config[field]:
                preview["layout"][field] = theme_config[field]
        
        # Component preview samples
        preview["components"] = {
            "button_primary": self._generate_button_preview(theme_config, "primary"),
            "button_secondary": self._generate_button_preview(theme_config, "secondary"),
            "input_field": self._generate_input_preview(theme_config),
            "card": self._generate_card_preview(theme_config)
        }
        
        return preview
    
    def apply_theme_template(self, project_id: str, template_name: str, user_id: str) -> ProjectTheme:
        """
        Apply a theme template to create a new theme
        
        Args:
            project_id: Project ID
            template_name: Theme template name
            user_id: User applying the template
            
        Returns:
            Created theme
        """
        # Get theme template from template service
        theme_template = self.template_service.get_theme_template(template_name)
        if not theme_template:
            raise ValueError(f"Theme template '{template_name}' not found")
        
        # Create theme from template
        return self.create_theme(
            project_id=project_id,
            theme_name=theme_template["theme_name"],
            user_id=user_id,
            theme_config=theme_template,
            is_default=True
        )
    
    def validate_theme_accessibility(self, theme: ProjectTheme) -> Dict[str, Any]:
        """
        Validate theme for accessibility compliance
        
        Args:
            theme: Theme to validate
            
        Returns:
            Validation results with issues and recommendations
        """
        issues = []
        recommendations = []
        
        # Check color contrast ratios
        if theme.primary_color and theme.background_color:
            contrast = self._calculate_contrast_ratio(theme.primary_color, theme.background_color)
            if contrast < 4.5:
                issues.append({
                    "type": "contrast",
                    "severity": "high",
                    "message": f"Primary color contrast ratio ({contrast:.2f}) is below WCAG AA standard (4.5:1)",
                    "colors": [theme.primary_color, theme.background_color]
                })
        
        if theme.text_color and theme.background_color:
            contrast = self._calculate_contrast_ratio(theme.text_color, theme.background_color)
            if contrast < 4.5:
                issues.append({
                    "type": "contrast",
                    "severity": "high",
                    "message": f"Text color contrast ratio ({contrast:.2f}) is below WCAG AA standard (4.5:1)",
                    "colors": [theme.text_color, theme.background_color]
                })
        
        # Check font size
        if theme.font_size_base:
            size_value = self._extract_numeric_value(theme.font_size_base)
            if size_value and size_value < 14:
                issues.append({
                    "type": "typography",
                    "severity": "medium",
                    "message": f"Base font size ({theme.font_size_base}) may be too small for accessibility",
                    "recommendation": "Consider using at least 14px for better readability"
                })
        
        # Check touch target sizes (for mobile)
        if theme.mobile_config:
            mobile_config = theme.mobile_config
            if "button_min_height" in mobile_config:
                height = self._extract_numeric_value(mobile_config["button_min_height"])
                if height and height < 44:
                    issues.append({
                        "type": "touch_target",
                        "severity": "medium",
                        "message": f"Button height ({mobile_config['button_min_height']}) is below recommended 44px minimum",
                        "recommendation": "Use at least 44px height for touch targets"
                    })
        
        return {
            "is_accessible": len([i for i in issues if i["severity"] == "high"]) == 0,
            "issues": issues,
            "recommendations": recommendations,
            "score": max(0, 100 - (len([i for i in issues if i["severity"] == "high"]) * 30) - 
                        (len([i for i in issues if i["severity"] == "medium"]) * 15))
        }
    
    def _validate_theme_config(self, theme_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize theme configuration"""
        validated = {}
        
        # Color fields
        color_fields = ['primary_color', 'secondary_color', 'accent_color', 
                       'background_color', 'text_color']
        for field in color_fields:
            if field in theme_config:
                color = self._validate_color(theme_config[field])
                if color:
                    validated[field] = color
        
        # Typography fields
        typography_fields = ['font_family', 'font_size_base', 'font_weight_normal', 'font_weight_bold']
        for field in typography_fields:
            if field in theme_config and theme_config[field]:
                validated[field] = str(theme_config[field])
        
        # Layout fields
        layout_fields = ['border_radius', 'spacing_unit', 'container_max_width']
        for field in layout_fields:
            if field in theme_config and theme_config[field]:
                validated[field] = str(theme_config[field])
        
        # Branding fields
        branding_fields = ['logo_url', 'favicon_url', 'brand_name']
        for field in branding_fields:
            if field in theme_config and theme_config[field]:
                validated[field] = str(theme_config[field])
        
        # JSON fields
        json_fields = ['css_variables', 'breakpoints', 'mobile_config']
        for field in json_fields:
            if field in theme_config and theme_config[field]:
                validated[field] = theme_config[field]
        
        # Custom CSS
        if 'custom_css' in theme_config and theme_config['custom_css']:
            validated['custom_css'] = self._sanitize_css(theme_config['custom_css'])
        
        return validated
    
    def _validate_color(self, color: str) -> Optional[str]:
        """Validate color format (hex, rgb, hsl)"""
        if not color:
            return None
        
        color = color.strip()
        
        # Hex color
        if re.match(r'^#[0-9A-Fa-f]{6}$', color):
            return color.upper()
        
        # RGB/RGBA color
        if re.match(r'^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*[\d.]+)?\s*\)$', color):
            return color
        
        # HSL/HSLA color
        if re.match(r'^hsla?\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*(,\s*[\d.]+)?\s*\)$', color):
            return color
        
        # Named colors (basic validation)
        named_colors = ['red', 'blue', 'green', 'black', 'white', 'gray', 'yellow', 'orange', 'purple']
        if color.lower() in named_colors:
            return color.lower()
        
        return None
    
    def _sanitize_css(self, css: str) -> str:
        """Sanitize custom CSS to prevent XSS"""
        # Remove potentially dangerous CSS
        dangerous_patterns = [
            r'javascript:',
            r'expression\s*\(',
            r'@import',
            r'behavior\s*:',
            r'-moz-binding',
            r'vbscript:'
        ]
        
        sanitized = css
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def _generate_base_styles(self, theme: ProjectTheme) -> List[str]:
        """Generate base CSS styles"""
        styles = []
        
        # Body styles
        body_styles = ["body {"]
        if theme.font_family:
            body_styles.append(f"  font-family: var(--font-family, {theme.font_family});")
        if theme.font_size_base:
            body_styles.append(f"  font-size: var(--font-size-base, {theme.font_size_base});")
        if theme.text_color:
            body_styles.append(f"  color: var(--color-text, {theme.text_color});")
        if theme.background_color:
            body_styles.append(f"  background-color: var(--color-background, {theme.background_color});")
        body_styles.append("}")
        styles.extend(body_styles)
        styles.append("")
        
        return styles
    
    def _generate_component_styles(self, theme: ProjectTheme) -> List[str]:
        """Generate component-specific CSS styles"""
        styles = []
        
        # Button styles
        styles.extend([
            "/* Button Styles */",
            ".btn {",
            f"  border-radius: var(--border-radius, {theme.border_radius or '4px'});",
            f"  padding: calc(var(--spacing-unit, {theme.spacing_unit or '8px'}) * 1.5) calc(var(--spacing-unit, {theme.spacing_unit or '8px'}) * 2);",
            "  border: none;",
            "  cursor: pointer;",
            "  transition: all 0.2s ease;",
            "}",
            "",
            ".btn-primary {",
            f"  background-color: var(--color-primary, {theme.primary_color or '#007bff'});",
            "  color: white;",
            "}",
            "",
            ".btn-secondary {",
            f"  background-color: var(--color-secondary, {theme.secondary_color or '#6c757d'});",
            "  color: white;",
            "}",
            ""
        ])
        
        # Input styles
        styles.extend([
            "/* Input Styles */",
            ".form-input {",
            f"  border-radius: var(--border-radius, {theme.border_radius or '4px'});",
            f"  padding: calc(var(--spacing-unit, {theme.spacing_unit or '8px'}) * 1.5);",
            "  border: 1px solid #ddd;",
            f"  font-family: var(--font-family, {theme.font_family or 'inherit'});",
            "}",
            "",
            ".form-input:focus {",
            f"  border-color: var(--color-primary, {theme.primary_color or '#007bff'});",
            "  outline: none;",
            "  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);",
            "}",
            ""
        ])
        
        # Card styles
        styles.extend([
            "/* Card Styles */",
            ".card {",
            f"  border-radius: var(--border-radius, {theme.border_radius or '4px'});",
            f"  padding: calc(var(--spacing-unit, {theme.spacing_unit or '8px'}) * 2);",
            "  background: white;",
            "  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);",
            "}",
            ""
        ])
        
        return styles
    
    def _generate_responsive_styles(self, theme: ProjectTheme) -> List[str]:
        """Generate responsive CSS styles"""
        styles = []
        
        if not theme.breakpoints:
            return styles
        
        breakpoints = theme.breakpoints
        
        # Mobile styles
        if 'mobile' in breakpoints:
            mobile_bp = breakpoints['mobile']
            styles.extend([
                f"@media (max-width: {mobile_bp}) {{",
                "  .container {",
                "    padding: 1rem;",
                "  }",
                "  .btn {",
                "    width: 100%;",
                "    margin-bottom: 0.5rem;",
                "  }",
                "}"
            ])
        
        # Tablet styles
        if 'tablet' in breakpoints:
            tablet_bp = breakpoints['tablet']
            styles.extend([
                f"@media (max-width: {tablet_bp}) {{",
                "  .container {",
                "    max-width: 768px;",
                "  }",
                "}"
            ])
        
        return styles
    
    def _calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """Calculate WCAG contrast ratio between two colors"""
        try:
            # Convert colors to RGB
            rgb1 = self._hex_to_rgb(color1)
            rgb2 = self._hex_to_rgb(color2)
            
            if not rgb1 or not rgb2:
                return 1.0
            
            # Calculate relative luminance
            lum1 = self._get_luminance(rgb1)
            lum2 = self._get_luminance(rgb2)
            
            # Calculate contrast ratio
            lighter = max(lum1, lum2)
            darker = min(lum1, lum2)
            
            return (lighter + 0.05) / (darker + 0.05)
        except:
            return 1.0
    
    def _hex_to_rgb(self, hex_color: str) -> Optional[Tuple[int, int, int]]:
        """Convert hex color to RGB tuple"""
        if not hex_color or not hex_color.startswith('#'):
            return None
        
        try:
            hex_color = hex_color[1:]  # Remove #
            if len(hex_color) == 6:
                return (
                    int(hex_color[0:2], 16),
                    int(hex_color[2:4], 16),
                    int(hex_color[4:6], 16)
                )
        except ValueError:
            pass
        
        return None
    
    def _get_luminance(self, rgb: Tuple[int, int, int]) -> float:
        """Calculate relative luminance of RGB color"""
        def normalize(c):
            c = c / 255.0
            if c <= 0.03928:
                return c / 12.92
            else:
                return pow((c + 0.055) / 1.055, 2.4)
        
        r, g, b = rgb
        return 0.2126 * normalize(r) + 0.7152 * normalize(g) + 0.0722 * normalize(b)
    
    def _extract_numeric_value(self, value: str) -> Optional[float]:
        """Extract numeric value from CSS value (e.g., '16px' -> 16)"""
        if not value:
            return None
        
        match = re.match(r'^(\d+(?:\.\d+)?)', str(value))
        if match:
            return float(match.group(1))
        
        return None
    
    def _generate_button_preview(self, theme_config: Dict[str, Any], button_type: str) -> Dict[str, str]:
        """Generate button preview styles"""
        color_key = f"{button_type}_color"
        bg_color = theme_config.get(color_key, '#007bff' if button_type == 'primary' else '#6c757d')
        
        return {
            "background_color": bg_color,
            "color": "white",
            "border_radius": theme_config.get('border_radius', '4px'),
            "font_family": theme_config.get('font_family', 'system-ui'),
            "padding": "12px 24px"
        }
    
    def _generate_input_preview(self, theme_config: Dict[str, Any]) -> Dict[str, str]:
        """Generate input field preview styles"""
        return {
            "border_color": "#ddd",
            "border_radius": theme_config.get('border_radius', '4px'),
            "font_family": theme_config.get('font_family', 'system-ui'),
            "font_size": theme_config.get('font_size_base', '16px'),
            "padding": "12px"
        }
    
    def _generate_card_preview(self, theme_config: Dict[str, Any]) -> Dict[str, str]:
        """Generate card preview styles"""
        return {
            "background_color": theme_config.get('background_color', 'white'),
            "border_radius": theme_config.get('border_radius', '4px'),
            "box_shadow": "0 2px 4px rgba(0, 0, 0, 0.1)",
            "padding": "24px"
        }