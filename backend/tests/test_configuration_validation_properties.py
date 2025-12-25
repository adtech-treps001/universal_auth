"""
Property Tests for Configuration Validation

This module contains property-based tests for configuration validation
using Hypothesis to validate universal correctness properties.

**Feature: universal-auth, Property 25: Configuration Validation**
**Validates: Requirements 11.4**
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Dict, Any, List, Optional
import json
import yaml

# Configuration strategies
config_key_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_.-'))
config_value_strategy = st.one_of(
    st.text(min_size=0, max_size=100),
    st.integers(min_value=0, max_value=10000),
    st.booleans(),
    st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
)
config_dict_strategy = st.dictionaries(
    keys=config_key_strategy,
    values=config_value_strategy,
    min_size=0,
    max_size=10
)

# Provider configuration strategies
provider_name_strategy = st.sampled_from(['google', 'github', 'linkedin', 'apple', 'meta'])
provider_config_strategy = st.fixed_dictionaries({
    'client_id': st.text(min_size=10, max_size=100),
    'client_secret': st.text(min_size=20, max_size=200),
    'enabled': st.booleans(),
    'scopes': st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5)
})

# Theme configuration strategies
theme_property_strategy = st.sampled_from(['primary_color', 'secondary_color', 'font_family', 'border_radius', 'button_style'])
theme_value_strategy = st.one_of(
    st.text(min_size=1, max_size=50),  # Colors, fonts, etc.
    st.integers(min_value=0, max_value=50),  # Border radius, sizes
    st.sampled_from(['solid', 'outline', 'ghost'])  # Button styles
)

class ConfigurationValidator:
    """Core configuration validation logic"""
    
    # Define required configuration fields
    REQUIRED_FIELDS = {
        'oauth_providers': ['client_id', 'client_secret'],
        'database': ['host', 'port', 'name'],
        'redis': ['host', 'port'],
        'jwt': ['secret_key', 'algorithm'],
        'encryption': ['key'],
        'theme': ['primary_color']
    }
    
    # Define field validation rules
    VALIDATION_RULES = {
        'client_id': lambda x: isinstance(x, str) and len(x) >= 10,
        'client_secret': lambda x: isinstance(x, str) and len(x) >= 20,
        'host': lambda x: isinstance(x, str) and len(x) > 0,
        'port': lambda x: isinstance(x, int) and 1 <= x <= 65535,
        'secret_key': lambda x: isinstance(x, str) and len(x) >= 32,
        'algorithm': lambda x: isinstance(x, str) and x in ['HS256', 'HS512', 'RS256'],
        'primary_color': lambda x: isinstance(x, str) and (x.startswith('#') or x in ['red', 'blue', 'green']),
        'enabled': lambda x: isinstance(x, bool)
    }
    
    @staticmethod
    def validate_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration structure and values
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []
        valid_sections = []
        
        # Check for required sections
        for section, required_fields in ConfigurationValidator.REQUIRED_FIELDS.items():
            if section not in config:
                errors.append(f"Missing required section: {section}")
                continue
            
            section_config = config[section]
            if not isinstance(section_config, dict):
                errors.append(f"Section {section} must be a dictionary")
                continue
            
            # Check required fields in section
            section_errors = []
            for field in required_fields:
                if field not in section_config:
                    section_errors.append(f"Missing required field: {section}.{field}")
                else:
                    # Validate field value
                    value = section_config[field]
                    if field in ConfigurationValidator.VALIDATION_RULES:
                        validator = ConfigurationValidator.VALIDATION_RULES[field]
                        if not validator(value):
                            section_errors.append(f"Invalid value for {section}.{field}: {value}")
            
            if section_errors:
                errors.extend(section_errors)
            else:
                valid_sections.append(section)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'valid_sections': valid_sections
        }
    
    @staticmethod
    def validate_provider_configuration(provider: str, config: Dict[str, Any]) -> bool:
        """
        Validate OAuth provider configuration
        
        Args:
            provider: Provider name
            config: Provider configuration
            
        Returns:
            True if configuration is valid
        """
        if not isinstance(config, dict):
            return False
        
        # Check required fields
        required_fields = ['client_id', 'client_secret']
        for field in required_fields:
            if field not in config:
                return False
            
            value = config[field]
            if field in ConfigurationValidator.VALIDATION_RULES:
                validator = ConfigurationValidator.VALIDATION_RULES[field]
                if not validator(value):
                    return False
        
        # Check optional fields
        if 'enabled' in config:
            if not isinstance(config['enabled'], bool):
                return False
        
        if 'scopes' in config:
            if not isinstance(config['scopes'], list):
                return False
            if not all(isinstance(scope, str) for scope in config['scopes']):
                return False
        
        return True
    
    @staticmethod
    def validate_theme_configuration(theme_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate theme configuration
        
        Args:
            theme_config: Theme configuration dictionary
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Check for required theme properties
        if 'primary_color' not in theme_config:
            errors.append("Missing required theme property: primary_color")
        else:
            color = theme_config['primary_color']
            if not (isinstance(color, str) and (color.startswith('#') or color in ['red', 'blue', 'green', 'purple', 'orange'])):
                errors.append(f"Invalid primary_color format: {color}")
        
        # Validate optional properties
        for prop, value in theme_config.items():
            if prop == 'border_radius':
                if not isinstance(value, (int, float)) or value < 0:
                    errors.append(f"Invalid border_radius: {value}")
            elif prop == 'font_family':
                if not isinstance(value, str) or len(value) == 0:
                    errors.append(f"Invalid font_family: {value}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    @staticmethod
    def merge_configurations(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge configuration with override values
        
        Args:
            base_config: Base configuration
            override_config: Override configuration
            
        Returns:
            Merged configuration
        """
        merged = base_config.copy()
        
        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                merged[key] = ConfigurationValidator.merge_configurations(merged[key], value)
            else:
                # Override value
                merged[key] = value
        
        return merged

class TestConfigurationValidation:
    """Property tests for configuration validation"""
    
    @given(
        config=config_dict_strategy
    )
    @settings(max_examples=100)
    def test_property_25_configuration_validation(self, config):
        """
        Property 25: Configuration Validation
        
        For any configuration dictionary, validation should correctly identify
        missing required fields, invalid values, and structural issues.
        
        **Validates: Requirements 11.4**
        """
        # Test configuration validation
        result = ConfigurationValidator.validate_configuration(config)
        
        # Verify result structure
        assert 'valid' in result
        assert 'errors' in result
        assert 'warnings' in result
        assert 'valid_sections' in result
        
        # Verify result consistency
        has_errors = len(result['errors']) > 0
        assert result['valid'] == (not has_errors), "Valid flag should match absence of errors"
        
        # Verify all sections are accounted for
        expected_sections = set(ConfigurationValidator.REQUIRED_FIELDS.keys())
        present_sections = set(config.keys()) if isinstance(config, dict) else set()
        valid_sections = set(result['valid_sections'])
        
        # Valid sections should be a subset of present sections
        assert valid_sections.issubset(present_sections), "Valid sections should be present in config"
    
    @given(
        provider=provider_name_strategy,
        provider_config=provider_config_strategy
    )
    @settings(max_examples=50)
    def test_property_provider_configuration_validation(self, provider, provider_config):
        """
        Property: Provider Configuration Validation
        
        For any OAuth provider and configuration, validation should correctly
        identify valid and invalid provider configurations.
        
        **Validates: Requirements 11.4**
        """
        # Test provider configuration validation
        is_valid = ConfigurationValidator.validate_provider_configuration(provider, provider_config)
        
        # Determine expected result
        expected_valid = True
        
        # Check required fields
        required_fields = ['client_id', 'client_secret']
        for field in required_fields:
            if field not in provider_config:
                expected_valid = False
                break
            
            value = provider_config[field]
            if field == 'client_id' and (not isinstance(value, str) or len(value) < 10):
                expected_valid = False
                break
            elif field == 'client_secret' and (not isinstance(value, str) or len(value) < 20):
                expected_valid = False
                break
        
        # Check optional fields
        if expected_valid and 'enabled' in provider_config:
            if not isinstance(provider_config['enabled'], bool):
                expected_valid = False
        
        if expected_valid and 'scopes' in provider_config:
            scopes = provider_config['scopes']
            if not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
                expected_valid = False
        
        assert is_valid == expected_valid, (
            f"Provider validation failed: provider={provider}, "
            f"config={provider_config}, expected={expected_valid}, got={is_valid}"
        )
    
    @given(
        theme_config=st.dictionaries(
            keys=theme_property_strategy,
            values=theme_value_strategy,
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=60)
    def test_property_theme_configuration_validation(self, theme_config):
        """
        Property: Theme Configuration Validation
        
        For any theme configuration, validation should correctly identify
        valid theme properties and values.
        
        **Validates: Requirements 11.4**
        """
        # Test theme configuration validation
        result = ConfigurationValidator.validate_theme_configuration(theme_config)
        
        # Verify result structure
        assert 'valid' in result
        assert 'errors' in result
        assert 'warnings' in result
        
        # Determine expected validity
        expected_errors = []
        
        # Check for required primary_color
        if 'primary_color' not in theme_config:
            expected_errors.append("primary_color missing")
        else:
            color = theme_config['primary_color']
            if not (isinstance(color, str) and (color.startswith('#') or color in ['red', 'blue', 'green', 'purple', 'orange'])):
                expected_errors.append("invalid primary_color")
        
        # Check other properties
        for prop, value in theme_config.items():
            if prop == 'border_radius':
                if not isinstance(value, (int, float)) or value < 0:
                    expected_errors.append("invalid border_radius")
            elif prop == 'font_family':
                if not isinstance(value, str) or len(value) == 0:
                    expected_errors.append("invalid font_family")
        
        expected_valid = len(expected_errors) == 0
        assert result['valid'] == expected_valid, (
            f"Theme validation failed: config={theme_config}, "
            f"expected_valid={expected_valid}, got={result['valid']}, errors={result['errors']}"
        )
    
    @given(
        base_config=config_dict_strategy,
        override_config=config_dict_strategy
    )
    @settings(max_examples=40)
    def test_property_configuration_merging(self, base_config, override_config):
        """
        Property: Configuration Merging
        
        For any base configuration and override configuration, merging should
        preserve base values while applying overrides correctly.
        
        **Validates: Requirements 11.4**
        """
        # Test configuration merging
        merged = ConfigurationValidator.merge_configurations(base_config, override_config)
        
        # Verify merged configuration contains all base keys not overridden
        for key, value in base_config.items():
            if key not in override_config:
                assert key in merged, f"Base key {key} should be preserved"
                assert merged[key] == value, f"Base value for {key} should be preserved"
        
        # Verify merged configuration contains all override keys
        for key, value in override_config.items():
            assert key in merged, f"Override key {key} should be present"
            # For non-dict values, should be exactly the override value
            if not isinstance(value, dict):
                assert merged[key] == value, f"Override value for {key} should be applied"
    
    @given(
        valid_config=st.fixed_dictionaries({
            'oauth_providers': st.fixed_dictionaries({
                'google': provider_config_strategy
            }),
            'database': st.fixed_dictionaries({
                'host': st.just('localhost'),
                'port': st.integers(min_value=1000, max_value=9999),
                'name': st.just('test_db')
            }),
            'jwt': st.fixed_dictionaries({
                'secret_key': st.text(min_size=32, max_size=64),
                'algorithm': st.sampled_from(['HS256', 'HS512'])
            })
        })
    )
    @settings(max_examples=30)
    def test_property_valid_configuration_acceptance(self, valid_config):
        """
        Property: Valid Configuration Acceptance
        
        For any properly structured configuration with all required fields,
        validation should succeed.
        
        **Validates: Requirements 11.4**
        """
        # Test that valid configurations are accepted
        result = ConfigurationValidator.validate_configuration(valid_config)
        
        # Should be valid with no errors
        assert result['valid'] == True, f"Valid configuration should be accepted: {result['errors']}"
        assert len(result['errors']) == 0, "Valid configuration should have no errors"
        
        # Should have valid sections
        assert len(result['valid_sections']) > 0, "Valid configuration should have valid sections"
    
    @given(
        incomplete_config=st.dictionaries(
            keys=st.sampled_from(['oauth_providers', 'database', 'jwt']),
            values=st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=config_value_strategy,
                min_size=0,
                max_size=2  # Intentionally small to create incomplete configs
            ),
            min_size=1,
            max_size=2
        )
    )
    @settings(max_examples=30)
    def test_property_incomplete_configuration_rejection(self, incomplete_config):
        """
        Property: Incomplete Configuration Rejection
        
        For any configuration missing required fields, validation should
        identify the missing fields and mark the configuration as invalid.
        
        **Validates: Requirements 11.4**
        """
        # Test that incomplete configurations are rejected
        result = ConfigurationValidator.validate_configuration(incomplete_config)
        
        # Should have errors for missing required fields
        assert len(result['errors']) > 0, "Incomplete configuration should have errors"
        
        # Check that errors mention missing fields
        error_text = ' '.join(result['errors'])
        assert 'Missing' in error_text or 'required' in error_text, "Errors should mention missing required fields"
    
    @given(
        multiple_configs=st.lists(
            config_dict_strategy,
            min_size=2,
            max_size=5
        )
    )
    @settings(max_examples=20)
    def test_property_configuration_validation_consistency(self, multiple_configs):
        """
        Property: Configuration Validation Consistency
        
        For any configuration, validation should be consistent across
        multiple calls with the same input.
        
        **Validates: Requirements 11.4**
        """
        # Test validation consistency
        for config in multiple_configs:
            results = []
            for _ in range(3):  # Test consistency across multiple calls
                result = ConfigurationValidator.validate_configuration(config)
                results.append(result)
            
            # All results should be identical
            first_result = results[0]
            for i, result in enumerate(results[1:], 1):
                assert result['valid'] == first_result['valid'], f"Validation consistency failed at call {i}"
                assert result['errors'] == first_result['errors'], f"Error consistency failed at call {i}"
                assert set(result['valid_sections']) == set(first_result['valid_sections']), f"Valid sections consistency failed at call {i}"
    
    @given(
        config_with_nested=st.fixed_dictionaries({
            'oauth_providers': st.dictionaries(
                keys=provider_name_strategy,
                values=provider_config_strategy,
                min_size=1,
                max_size=3
            ),
            'theme': st.dictionaries(
                keys=theme_property_strategy,
                values=theme_value_strategy,
                min_size=1,
                max_size=4
            )
        })
    )
    @settings(max_examples=25)
    def test_property_nested_configuration_validation(self, config_with_nested):
        """
        Property: Nested Configuration Validation
        
        For any configuration with nested structures, validation should
        correctly validate both the structure and nested values.
        
        **Validates: Requirements 11.4**
        """
        # Test nested configuration validation
        result = ConfigurationValidator.validate_configuration(config_with_nested)
        
        # Verify nested validation works
        assert isinstance(result, dict), "Should return validation result"
        assert 'valid' in result, "Should have valid flag"
        
        # If oauth_providers section is present, validate individual providers
        if 'oauth_providers' in config_with_nested:
            providers = config_with_nested['oauth_providers']
            for provider_name, provider_config in providers.items():
                provider_valid = ConfigurationValidator.validate_provider_configuration(
                    provider_name, provider_config
                )
                # Provider validation should be consistent with overall validation
                if 'oauth_providers' in result['valid_sections']:
                    # If section is valid, individual providers should be valid too
                    assert provider_valid or len(result['errors']) > 0, (
                        f"Provider {provider_name} validation inconsistent with section validation"
                    )

if __name__ == "__main__":
    pytest.main([__file__, "-v"])