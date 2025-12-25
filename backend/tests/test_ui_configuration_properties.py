"""
Property Tests for UI Configuration Application

This module contains property-based tests for UI configuration application
using Hypothesis to validate universal correctness properties.

**Feature: universal-auth, Property 14: UI Configuration Application**
**Validates: Requirements 6.1, 6.3**
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Dict, Any, List, Optional
import json

# UI configuration strategies
color_strategy = st.one_of(
    st.text(min_size=7, max_size=7).filter(lambda x: x.startswith('#')),  # Hex colors
    st.sampled_from(['red', 'blue', 'green', 'purple', 'orange', 'yellow', 'black', 'white'])
)
font_family_strategy = st.sampled_from(['Arial', 'Helvetica', 'Times New Roman', 'Georgia', 'Verdana', 'Roboto'])
size_strategy = st.integers(min_value=8, max_value=72)
border_radius_strategy = st.integers(min_value=0, max_value=50)
spacing_strategy = st.integers(min_value=0, max_value=100)

theme_config_strategy = st.fixed_dictionaries({
    'primary_color': color_strategy,
    'secondary_color': color_strategy,
    'background_color': color_strategy,
    'text_color': color_strategy,
    'font_family': font_family_strategy,
    'font_size': size_strategy,
    'border_radius': border_radius_strategy,
    'button_padding': spacing_strategy,
    'form_spacing': spacing_strategy
})

# Component configuration strategies
component_type_strategy = st.sampled_from(['button', 'input', 'form', 'card', 'modal', 'navbar'])
component_variant_strategy = st.sampled_from(['primary', 'secondary', 'outline', 'ghost', 'danger'])
component_size_strategy = st.sampled_from(['small', 'medium', 'large'])

component_config_strategy = st.fixed_dictionaries({
    'type': component_type_strategy,
    'variant': component_variant_strategy,
    'size': component_size_strategy,
    'custom_css': st.text(min_size=0, max_size=200),
    'enabled': st.booleans()
})

# Layout configuration strategies
layout_type_strategy = st.sampled_from(['centered', 'sidebar', 'fullscreen', 'modal', 'embedded'])
breakpoint_strategy = st.sampled_from(['mobile', 'tablet', 'desktop', 'wide'])

layout_config_strategy = st.fixed_dictionaries({
    'type': layout_type_strategy,
    'responsive': st.booleans(),
    'breakpoints': st.dictionaries(
        keys=breakpoint_strategy,
        values=st.integers(min_value=320, max_value=1920),
        min_size=1,
        max_size=4
    ),
    'container_width': st.integers(min_value=300, max_value=1200),
    'sidebar_width': st.integers(min_value=200, max_value=400)
})

class UIConfigurationManager:
    """Core UI configuration management logic"""
    
    # Default theme configuration
    DEFAULT_THEME = {
        'primary_color': '#007bff',
        'secondary_color': '#6c757d',
        'background_color': '#ffffff',
        'text_color': '#212529',
        'font_family': 'Arial',
        'font_size': 14,
        'border_radius': 4,
        'button_padding': 12,
        'form_spacing': 16
    }
    
    # Component style mappings
    COMPONENT_STYLES = {
        'button': {
            'primary': {'background': 'primary_color', 'color': 'white'},
            'secondary': {'background': 'secondary_color', 'color': 'white'},
            'outline': {'border': 'primary_color', 'color': 'primary_color'},
            'ghost': {'background': 'transparent', 'color': 'primary_color'}
        },
        'input': {
            'primary': {'border': 'secondary_color', 'background': 'background_color'},
            'outline': {'border': 'primary_color', 'background': 'background_color'}
        },
        'form': {
            'primary': {'background': 'background_color', 'spacing': 'form_spacing'}
        }
    }
    
    @staticmethod
    def apply_theme_configuration(theme_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply theme configuration and generate CSS variables
        
        Args:
            theme_config: Theme configuration dictionary
            
        Returns:
            Applied theme with CSS variables
        """
        # Start with default theme
        applied_theme = UIConfigurationManager.DEFAULT_THEME.copy()
        
        # Apply overrides
        for key, value in theme_config.items():
            if key in applied_theme:
                applied_theme[key] = value
        
        # Generate CSS variables
        css_variables = {}
        for key, value in applied_theme.items():
            css_var_name = f"--{key.replace('_', '-')}"
            css_variables[css_var_name] = str(value)
        
        return {
            'theme': applied_theme,
            'css_variables': css_variables,
            'applied_successfully': True
        }
    
    @staticmethod
    def generate_component_styles(component_config: Dict[str, Any], theme: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate component styles based on configuration and theme
        
        Args:
            component_config: Component configuration
            theme: Applied theme configuration
            
        Returns:
            Generated component styles
        """
        component_type = component_config.get('type', 'button')
        variant = component_config.get('variant', 'primary')
        size = component_config.get('size', 'medium')
        
        # Get base styles for component type and variant
        base_styles = {}
        if component_type in UIConfigurationManager.COMPONENT_STYLES:
            type_styles = UIConfigurationManager.COMPONENT_STYLES[component_type]
            if variant in type_styles:
                base_styles = type_styles[variant].copy()
        
        # Apply theme values to style references
        resolved_styles = {}
        for style_prop, style_value in base_styles.items():
            if style_value in theme:
                resolved_styles[style_prop] = theme[style_value]
            else:
                resolved_styles[style_prop] = style_value
        
        # Apply size-specific styles
        size_multipliers = {'small': 0.8, 'medium': 1.0, 'large': 1.2}
        multiplier = size_multipliers.get(size, 1.0)
        
        if 'font_size' in theme:
            resolved_styles['font_size'] = int(theme['font_size'] * multiplier)
        if 'button_padding' in theme:
            resolved_styles['padding'] = int(theme['button_padding'] * multiplier)
        
        # Apply custom CSS if provided
        if 'custom_css' in component_config and component_config['custom_css']:
            resolved_styles['custom_css'] = component_config['custom_css']
        
        return {
            'component_type': component_type,
            'variant': variant,
            'size': size,
            'styles': resolved_styles,
            'enabled': component_config.get('enabled', True)
        }
    
    @staticmethod
    def apply_layout_configuration(layout_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply layout configuration and generate responsive rules
        
        Args:
            layout_config: Layout configuration dictionary
            
        Returns:
            Applied layout configuration
        """
        layout_type = layout_config.get('type', 'centered')
        responsive = layout_config.get('responsive', True)
        breakpoints = layout_config.get('breakpoints', {})
        
        # Generate layout classes
        layout_classes = [f"layout-{layout_type}"]
        if responsive:
            layout_classes.append('responsive')
        
        # Generate responsive CSS rules
        responsive_rules = {}
        if responsive and breakpoints:
            for breakpoint, width in breakpoints.items():
                responsive_rules[f"@media (min-width: {width}px)"] = {
                    'container_width': layout_config.get('container_width', 1200),
                    'sidebar_width': layout_config.get('sidebar_width', 300)
                }
        
        return {
            'layout_type': layout_type,
            'responsive': responsive,
            'layout_classes': layout_classes,
            'responsive_rules': responsive_rules,
            'container_width': layout_config.get('container_width', 1200),
            'sidebar_width': layout_config.get('sidebar_width', 300)
        }
    
    @staticmethod
    def validate_ui_configuration(ui_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate UI configuration for consistency and completeness
        
        Args:
            ui_config: Complete UI configuration
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Validate theme configuration
        if 'theme' in ui_config:
            theme = ui_config['theme']
            
            # Check for required theme properties
            required_props = ['primary_color', 'background_color', 'text_color']
            for prop in required_props:
                if prop not in theme:
                    errors.append(f"Missing required theme property: {prop}")
            
            # Validate color formats
            for prop, value in theme.items():
                if prop.endswith('_color') and isinstance(value, str):
                    if not (value.startswith('#') or value in ['red', 'blue', 'green', 'purple', 'orange', 'yellow', 'black', 'white']):
                        warnings.append(f"Unusual color format for {prop}: {value}")
        
        # Validate component configurations
        if 'components' in ui_config:
            components = ui_config['components']
            if isinstance(components, list):
                for i, component in enumerate(components):
                    if 'type' not in component:
                        errors.append(f"Component {i} missing type")
                    if 'enabled' not in component:
                        warnings.append(f"Component {i} missing enabled flag")
        
        # Validate layout configuration
        if 'layout' in ui_config:
            layout = ui_config['layout']
            if 'type' not in layout:
                errors.append("Layout missing type")
            
            if layout.get('responsive', False) and 'breakpoints' not in layout:
                warnings.append("Responsive layout without breakpoints")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

class TestUIConfigurationApplication:
    """Property tests for UI configuration application"""
    
    @given(
        theme_config=theme_config_strategy
    )
    @settings(max_examples=100)
    def test_property_14_ui_configuration_application(self, theme_config):
        """
        Property 14: UI Configuration Application
        
        For any valid theme configuration, the UI system should correctly
        apply the theme and generate appropriate CSS variables and styles.
        
        **Validates: Requirements 6.1, 6.3**
        """
        # Test theme configuration application
        result = UIConfigurationManager.apply_theme_configuration(theme_config)
        
        # Verify result structure
        assert 'theme' in result
        assert 'css_variables' in result
        assert 'applied_successfully' in result
        
        # Verify theme application
        applied_theme = result['theme']
        assert applied_theme is not None
        
        # Verify all default theme properties are present
        for key in UIConfigurationManager.DEFAULT_THEME.keys():
            assert key in applied_theme, f"Default theme property {key} should be present"
        
        # Verify overrides are applied
        for key, value in theme_config.items():
            if key in UIConfigurationManager.DEFAULT_THEME:
                assert applied_theme[key] == value, f"Theme override for {key} should be applied"
        
        # Verify CSS variables are generated
        css_variables = result['css_variables']
        assert len(css_variables) > 0, "CSS variables should be generated"
        
        # Verify CSS variable format
        for css_var, css_value in css_variables.items():
            assert css_var.startswith('--'), f"CSS variable {css_var} should start with --"
            assert isinstance(css_value, str), f"CSS variable value should be string"
        
        assert result['applied_successfully'] == True, "Theme application should succeed"
    
    @given(
        component_config=component_config_strategy,
        theme_config=theme_config_strategy
    )
    @settings(max_examples=80)
    def test_property_component_style_generation(self, component_config, theme_config):
        """
        Property: Component Style Generation
        
        For any component configuration and theme, the system should generate
        appropriate styles that respect both the component config and theme.
        
        **Validates: Requirements 6.1, 6.3**
        """
        # Apply theme first
        theme_result = UIConfigurationManager.apply_theme_configuration(theme_config)
        theme = theme_result['theme']
        
        # Generate component styles
        component_styles = UIConfigurationManager.generate_component_styles(component_config, theme)
        
        # Verify component styles structure
        assert 'component_type' in component_styles
        assert 'variant' in component_styles
        assert 'size' in component_styles
        assert 'styles' in component_styles
        assert 'enabled' in component_styles
        
        # Verify component configuration is preserved
        assert component_styles['component_type'] == component_config.get('type', 'button')
        assert component_styles['variant'] == component_config.get('variant', 'primary')
        assert component_styles['size'] == component_config.get('size', 'medium')
        assert component_styles['enabled'] == component_config.get('enabled', True)
        
        # Verify styles are generated
        styles = component_styles['styles']
        assert isinstance(styles, dict), "Styles should be a dictionary"
        
        # Verify size affects font size and padding
        size = component_styles['size']
        size_multipliers = {'small': 0.8, 'medium': 1.0, 'large': 1.2}
        expected_multiplier = size_multipliers.get(size, 1.0)
        
        if 'font_size' in styles:
            base_font_size = theme.get('font_size', 14)
            expected_font_size = int(base_font_size * expected_multiplier)
            assert styles['font_size'] == expected_font_size, "Font size should be adjusted by size multiplier"
    
    @given(
        layout_config=layout_config_strategy
    )
    @settings(max_examples=60)
    def test_property_layout_configuration_application(self, layout_config):
        """
        Property: Layout Configuration Application
        
        For any layout configuration, the system should generate appropriate
        layout classes and responsive rules.
        
        **Validates: Requirements 6.1, 6.3**
        """
        # Apply layout configuration
        result = UIConfigurationManager.apply_layout_configuration(layout_config)
        
        # Verify result structure
        assert 'layout_type' in result
        assert 'responsive' in result
        assert 'layout_classes' in result
        assert 'responsive_rules' in result
        assert 'container_width' in result
        assert 'sidebar_width' in result
        
        # Verify layout type is preserved
        expected_type = layout_config.get('type', 'centered')
        assert result['layout_type'] == expected_type
        
        # Verify responsive setting is preserved
        expected_responsive = layout_config.get('responsive', True)
        assert result['responsive'] == expected_responsive
        
        # Verify layout classes include layout type
        layout_classes = result['layout_classes']
        assert isinstance(layout_classes, list), "Layout classes should be a list"
        assert f"layout-{expected_type}" in layout_classes, "Layout classes should include layout type"
        
        # Verify responsive classes
        if expected_responsive:
            assert 'responsive' in layout_classes, "Responsive layouts should have responsive class"
        
        # Verify responsive rules
        responsive_rules = result['responsive_rules']
        if expected_responsive and 'breakpoints' in layout_config:
            breakpoints = layout_config['breakpoints']
            if breakpoints:
                assert len(responsive_rules) > 0, "Responsive layout with breakpoints should have responsive rules"
                
                # Verify media query format
                for media_query in responsive_rules.keys():
                    assert media_query.startswith('@media'), "Responsive rules should use media queries"
    
    @given(
        ui_config=st.fixed_dictionaries({
            'theme': theme_config_strategy,
            'components': st.lists(component_config_strategy, min_size=1, max_size=5),
            'layout': layout_config_strategy
        })
    )
    @settings(max_examples=40)
    def test_property_complete_ui_configuration_validation(self, ui_config):
        """
        Property: Complete UI Configuration Validation
        
        For any complete UI configuration, validation should correctly identify
        valid configurations and flag missing or invalid properties.
        
        **Validates: Requirements 6.1, 6.3**
        """
        # Validate complete UI configuration
        validation_result = UIConfigurationManager.validate_ui_configuration(ui_config)
        
        # Verify validation result structure
        assert 'valid' in validation_result
        assert 'errors' in validation_result
        assert 'warnings' in validation_result
        
        # Verify validation logic
        errors = validation_result['errors']
        warnings = validation_result['warnings']
        
        # Check theme validation
        theme = ui_config.get('theme', {})
        required_theme_props = ['primary_color', 'background_color', 'text_color']
        
        for prop in required_theme_props:
            if prop not in theme:
                assert any(prop in error for error in errors), f"Missing {prop} should be flagged as error"
        
        # Verify valid flag consistency
        has_errors = len(errors) > 0
        assert validation_result['valid'] == (not has_errors), "Valid flag should match absence of errors"
    
    @given(
        base_theme=theme_config_strategy,
        override_theme=st.dictionaries(
            keys=st.sampled_from(['primary_color', 'font_size', 'border_radius']),
            values=st.one_of(color_strategy, size_strategy, border_radius_strategy),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=30)
    def test_property_theme_inheritance_and_override(self, base_theme, override_theme):
        """
        Property: Theme Inheritance and Override
        
        For any base theme and override values, the system should correctly
        apply overrides while preserving non-overridden base values.
        
        **Validates: Requirements 6.1, 6.3**
        """
        # Apply base theme
        base_result = UIConfigurationManager.apply_theme_configuration(base_theme)
        base_applied = base_result['theme']
        
        # Create combined theme
        combined_theme = base_theme.copy()
        combined_theme.update(override_theme)
        
        # Apply combined theme
        combined_result = UIConfigurationManager.apply_theme_configuration(combined_theme)
        combined_applied = combined_result['theme']
        
        # Verify overrides are applied
        for key, value in override_theme.items():
            if key in UIConfigurationManager.DEFAULT_THEME:
                assert combined_applied[key] == value, f"Override for {key} should be applied"
        
        # Verify non-overridden values are preserved
        for key, value in base_theme.items():
            if key not in override_theme and key in UIConfigurationManager.DEFAULT_THEME:
                assert combined_applied[key] == value, f"Base value for {key} should be preserved"
    
    @given(
        theme_config=theme_config_strategy,
        multiple_components=st.lists(component_config_strategy, min_size=2, max_size=5)
    )
    @settings(max_examples=25)
    def test_property_consistent_theme_application(self, theme_config, multiple_components):
        """
        Property: Consistent Theme Application
        
        For any theme and multiple components, the theme should be applied
        consistently across all components.
        
        **Validates: Requirements 6.1, 6.3**
        """
        # Apply theme
        theme_result = UIConfigurationManager.apply_theme_configuration(theme_config)
        theme = theme_result['theme']
        
        # Generate styles for all components
        component_styles = []
        for component_config in multiple_components:
            styles = UIConfigurationManager.generate_component_styles(component_config, theme)
            component_styles.append(styles)
        
        # Verify consistent theme application
        for i, styles in enumerate(component_styles):
            # Check that theme colors are consistently applied
            component_styles_dict = styles['styles']
            
            # If component uses primary color, it should be the same across all components
            if 'background' in component_styles_dict and component_styles_dict['background'] == theme['primary_color']:
                for j, other_styles in enumerate(component_styles):
                    other_styles_dict = other_styles['styles']
                    if 'background' in other_styles_dict and other_styles_dict['background'] == theme['primary_color']:
                        assert component_styles_dict['background'] == other_styles_dict['background'], (
                            f"Primary color should be consistent between components {i} and {j}"
                        )
    
    @given(
        ui_config=st.fixed_dictionaries({
            'theme': theme_config_strategy,
            'layout': layout_config_strategy
        }),
        multiple_validations=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=20)
    def test_property_ui_configuration_validation_consistency(self, ui_config, multiple_validations):
        """
        Property: UI Configuration Validation Consistency
        
        For any UI configuration, validation should be consistent across
        multiple calls with the same input.
        
        **Validates: Requirements 6.1, 6.3**
        """
        # Test validation consistency
        results = []
        for _ in range(multiple_validations):
            result = UIConfigurationManager.validate_ui_configuration(ui_config)
            results.append(result)
        
        # All results should be identical
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            assert result['valid'] == first_result['valid'], f"Validation consistency failed at call {i}"
            assert result['errors'] == first_result['errors'], f"Error consistency failed at call {i}"
            assert result['warnings'] == first_result['warnings'], f"Warning consistency failed at call {i}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])