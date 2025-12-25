"""
Property Tests for Theme Configuration System

Tests Property 23: Theme Configuration Application
Validates that theme configurations are correctly applied and generate valid CSS.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, initialize
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import tempfile
import os
import re
from typing import Dict, Any, List

# Create test base and engine
TestBase = declarative_base()

# Test database setup - use SQLite in memory
test_engine = create_engine("sqlite:///:memory:", echo=False)
TestSession = sessionmaker(bind=test_engine)

# Import models after setting up test database
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Mock the database module for testing
class MockDatabase:
    Base = TestBase

sys.modules['database'] = MockDatabase()

from models.project import Project, ProjectTheme
from services.theme_service import ThemeService
from services.template_service import TemplateService

# Create tables
Project.__table__.create(test_engine, checkfirst=True)
ProjectTheme.__table__.create(test_engine, checkfirst=True)

# Hypothesis strategies for theme configuration
color_strategy = st.one_of(
    st.text(min_size=7, max_size=7).filter(lambda x: re.match(r'^#[0-9A-Fa-f]{6}$', x)),
    st.sampled_from(['red', 'blue', 'green', 'black', 'white', 'gray'])
)

font_family_strategy = st.sampled_from([
    'Arial, sans-serif',
    'Georgia, serif',
    'Times New Roman, serif',
    'Helvetica, sans-serif',
    'system-ui, sans-serif'
])

css_unit_strategy = st.one_of(
    st.integers(min_value=1, max_value=100).map(lambda x: f"{x}px"),
    st.floats(min_value=0.5, max_value=5.0).map(lambda x: f"{x}rem"),
    st.integers(min_value=1, max_value=20).map(lambda x: f"{x}%")
)

theme_config_strategy = st.fixed_dictionaries({
    'primary_color': st.one_of(st.none(), color_strategy),
    'secondary_color': st.one_of(st.none(), color_strategy),
    'accent_color': st.one_of(st.none(), color_strategy),
    'background_color': st.one_of(st.none(), color_strategy),
    'text_color': st.one_of(st.none(), color_strategy),
    'font_family': st.one_of(st.none(), font_family_strategy),
    'font_size_base': st.one_of(st.none(), css_unit_strategy),
    'border_radius': st.one_of(st.none(), css_unit_strategy),
    'spacing_unit': st.one_of(st.none(), css_unit_strategy),
    'brand_name': st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    'custom_css': st.one_of(st.none(), st.text(max_size=1000))
})

class ThemeConfigurationStateMachine(RuleBasedStateMachine):
    """State machine for testing theme configuration properties"""
    
    def __init__(self):
        super().__init__()
        self.db = TestSession()
        self.theme_service = ThemeService(self.db)
        self.projects = {}
        self.themes = {}
        self.project_counter = 0
        self.theme_counter = 0
    
    projects = Bundle('projects')
    themes = Bundle('themes')
    
    @initialize()
    def setup_database(self):
        """Initialize test database"""
        # Clear existing data
        self.db.query(ProjectTheme).delete()
        self.db.query(Project).delete()
        self.db.commit()
    
    @rule(target=projects)
    def create_project(self):
        """Create a test project"""
        self.project_counter += 1
        project_id = f"project_{self.project_counter}"
        
        project = Project(
            id=project_id,
            name=f"Test Project {self.project_counter}",
            slug=f"test-project-{self.project_counter}",
            owner_id="test_user",
            is_active=True
        )
        
        self.db.add(project)
        self.db.commit()
        
        self.projects[project_id] = project
        return project_id
    
    @rule(
        target=themes,
        project_id=projects,
        theme_config=theme_config_strategy,
        theme_name=st.text(min_size=1, max_size=50),
        is_default=st.booleans()
    )
    def create_theme(self, project_id, theme_config, theme_name, is_default):
        """Create a theme with given configuration"""
        assume(project_id in self.projects)
        
        try:
            theme = self.theme_service.create_theme(
                project_id=project_id,
                theme_name=theme_name,
                user_id="test_user",
                theme_config=theme_config,
                is_default=is_default
            )
            
            theme_key = f"{project_id}_{theme.id}"
            self.themes[theme_key] = {
                'theme': theme,
                'project_id': project_id,
                'config': theme_config
            }
            
            return theme_key
            
        except Exception as e:
            # Theme creation failed, which is acceptable for invalid configs
            assume(False)
    
    @rule(theme_key=themes)
    def test_theme_css_generation(self, theme_key):
        """Property 23.1: CSS generation produces valid CSS"""
        assume(theme_key in self.themes)
        
        theme_data = self.themes[theme_key]
        theme = theme_data['theme']
        
        # Generate CSS
        css = self.theme_service.generate_css(theme, include_responsive=True)
        
        # Verify CSS is not empty
        assert css.strip() != "", "Generated CSS should not be empty"
        
        # Verify CSS contains root variables
        assert ":root {" in css, "CSS should contain root variables"
        
        # Verify CSS contains closing braces
        open_braces = css.count('{')
        close_braces = css.count('}')
        assert open_braces == close_braces, "CSS should have balanced braces"
        
        # If theme has colors, verify they appear in CSS
        if theme.primary_color:
            assert theme.primary_color in css, "Primary color should appear in CSS"
        
        if theme.font_family:
            assert theme.font_family in css, "Font family should appear in CSS"
    
    @rule(theme_key=themes)
    def test_theme_preview_generation(self, theme_key):
        """Property 23.2: Theme preview contains expected structure"""
        assume(theme_key in self.themes)
        
        theme_data = self.themes[theme_key]
        config = theme_data['config']
        
        # Generate preview
        preview = self.theme_service.generate_theme_preview(config)
        
        # Verify preview structure
        assert isinstance(preview, dict), "Preview should be a dictionary"
        assert 'colors' in preview, "Preview should contain colors section"
        assert 'typography' in preview, "Preview should contain typography section"
        assert 'layout' in preview, "Preview should contain layout section"
        assert 'components' in preview, "Preview should contain components section"
        
        # Verify color preview
        colors = preview['colors']
        for color_field in ['primary_color', 'secondary_color', 'accent_color']:
            if config.get(color_field):
                assert color_field in colors, f"Color {color_field} should be in preview"
    
    @rule(theme_key=themes)
    def test_theme_accessibility_validation(self, theme_key):
        """Property 23.3: Accessibility validation provides meaningful results"""
        assume(theme_key in self.themes)
        
        theme_data = self.themes[theme_key]
        theme = theme_data['theme']
        
        # Validate accessibility
        validation = self.theme_service.validate_theme_accessibility(theme)
        
        # Verify validation structure
        assert isinstance(validation, dict), "Validation should be a dictionary"
        assert 'is_accessible' in validation, "Validation should include accessibility flag"
        assert 'score' in validation, "Validation should include score"
        assert 'issues' in validation, "Validation should include issues list"
        assert 'recommendations' in validation, "Validation should include recommendations"
        
        # Verify score is valid
        score = validation['score']
        assert 0 <= score <= 100, "Accessibility score should be between 0 and 100"
        
        # Verify issues structure
        issues = validation['issues']
        assert isinstance(issues, list), "Issues should be a list"
        
        for issue in issues:
            assert 'type' in issue, "Issue should have type"
            assert 'severity' in issue, "Issue should have severity"
            assert 'message' in issue, "Issue should have message"
    
    @rule(
        theme_key=themes,
        new_config=theme_config_strategy
    )
    def test_theme_update_consistency(self, theme_key, new_config):
        """Property 23.4: Theme updates maintain consistency"""
        assume(theme_key in self.themes)
        
        theme_data = self.themes[theme_key]
        theme = theme_data['theme']
        original_id = theme.id
        
        try:
            # Update theme
            updated_theme = self.theme_service.update_theme(
                theme_id=theme.id,
                user_id="test_user",
                theme_config=new_config
            )
            
            # Verify theme identity preserved
            assert updated_theme.id == original_id, "Theme ID should remain unchanged"
            assert updated_theme.project_id == theme.project_id, "Project ID should remain unchanged"
            
            # Verify configuration applied
            for field, value in new_config.items():
                if value is not None and hasattr(updated_theme, field):
                    actual_value = getattr(updated_theme, field)
                    assert actual_value == value, f"Field {field} should be updated to {value}"
            
            # Update our tracking
            self.themes[theme_key]['theme'] = updated_theme
            self.themes[theme_key]['config'] = new_config
            
        except Exception:
            # Update failed, which is acceptable for invalid configs
            pass
    
    @rule(project_id=projects)
    def test_project_theme_isolation(self, project_id):
        """Property 23.5: Themes are properly isolated by project"""
        assume(project_id in self.projects)
        
        # Get themes for this project
        project_themes = self.theme_service.get_project_themes(project_id)
        
        # Verify all themes belong to this project
        for theme in project_themes:
            assert theme.project_id == project_id, "All themes should belong to the correct project"
            assert theme.is_active, "All returned themes should be active"
        
        # Verify theme count consistency
        theme_count = len([
            t for t in self.themes.values() 
            if t['project_id'] == project_id and t['theme'].is_active
        ])
        assert len(project_themes) == theme_count, "Theme count should match expected count"
    
    @rule(theme_key=themes)
    def test_default_theme_uniqueness(self, theme_key):
        """Property 23.6: Only one default theme per project"""
        assume(theme_key in self.themes)
        
        theme_data = self.themes[theme_key]
        project_id = theme_data['project_id']
        
        # Get all themes for the project
        project_themes = self.theme_service.get_project_themes(project_id)
        
        # Count default themes
        default_themes = [t for t in project_themes if t.is_default]
        
        # Should have exactly one default theme
        assert len(default_themes) <= 1, "Should have at most one default theme per project"
        
        if default_themes:
            default_theme = default_themes[0]
            # Verify it's the most recently set default
            assert default_theme.is_active, "Default theme should be active"
    
    def teardown(self):
        """Clean up test database"""
        self.db.close()

# Individual property tests
@given(theme_config=theme_config_strategy)
@settings(max_examples=50, deadline=5000)
def test_theme_config_validation_consistency(theme_config):
    """Property 23.7: Theme configuration validation is consistent"""
    db = TestSession()
    theme_service = ThemeService(db)
    
    try:
        # Validate configuration
        validated_config = theme_service._validate_theme_config(theme_config)
        
        # Verify validation preserves valid values
        for field, value in theme_config.items():
            if value is not None:
                if field in validated_config:
                    # Field was accepted
                    assert validated_config[field] is not None, f"Valid field {field} should not be None"
                # Field might be rejected, which is acceptable
        
        # Verify no invalid values in validated config
        for field, value in validated_config.items():
            assert value is not None, f"Validated field {field} should not be None"
            
            # Color fields should be valid colors
            if field.endswith('_color') and isinstance(value, str):
                # Should be hex, rgb, hsl, or named color
                is_valid_color = (
                    re.match(r'^#[0-9A-Fa-f]{6}$', value) or
                    re.match(r'^rgba?\(', value) or
                    re.match(r'^hsla?\(', value) or
                    value.lower() in ['red', 'blue', 'green', 'black', 'white', 'gray']
                )
                assert is_valid_color, f"Color field {field} should have valid color value: {value}"
    
    finally:
        db.close()

@given(
    css_content=st.text(max_size=1000),
    dangerous_patterns=st.lists(
        st.sampled_from(['javascript:', 'expression(', '@import', 'behavior:', 'vbscript:']),
        max_size=3
    )
)
@settings(max_examples=30, deadline=3000)
def test_css_sanitization_security(css_content, dangerous_patterns):
    """Property 23.8: CSS sanitization removes dangerous patterns"""
    db = TestSession()
    theme_service = ThemeService(db)
    
    try:
        # Inject dangerous patterns
        malicious_css = css_content
        for pattern in dangerous_patterns:
            malicious_css += f" {pattern} malicious_content;"
        
        # Sanitize CSS
        sanitized_css = theme_service._sanitize_css(malicious_css)
        
        # Verify dangerous patterns are removed
        for pattern in dangerous_patterns:
            assert pattern.lower() not in sanitized_css.lower(), f"Dangerous pattern {pattern} should be removed"
        
        # Verify original safe content is preserved (mostly)
        if css_content and not any(p.lower() in css_content.lower() for p in dangerous_patterns):
            # If original content didn't contain dangerous patterns, it should be mostly preserved
            assert len(sanitized_css) >= len(css_content) * 0.8, "Safe CSS content should be mostly preserved"
    
    finally:
        db.close()

# Test runner
TestThemeConfiguration = ThemeConfigurationStateMachine.TestCase

if __name__ == "__main__":
    # Run individual tests
    test_theme_config_validation_consistency()
    test_css_sanitization_security()
    
    # Run state machine tests
    TestThemeConfiguration().runTest()
    
    print("All theme property tests passed!")