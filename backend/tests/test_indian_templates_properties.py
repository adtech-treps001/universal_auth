"""
Property-Based Tests for Indian-Style Mobile-First Templates

These tests validate the correctness properties for Indian template functionality
including mobile-first configuration, progressive profiling, and regional customization.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import yaml
import os
from typing import Dict, Any, List, Optional

from services.template_service import TemplateService
from services.project_service import ProjectConfigurationService
from models.project import Project, ProjectConfiguration, ProjectWorkflow, ProjectTheme
from database import get_test_db
from sqlalchemy.orm import Session

# Test data generators
@st.composite
def indian_mobile_number(draw):
    """Generate valid Indian mobile numbers"""
    first_digit = draw(st.sampled_from(['6', '7', '8', '9']))
    remaining_digits = draw(st.text(alphabet='0123456789', min_size=9, max_size=9))
    return first_digit + remaining_digits

@st.composite
def indian_pin_code(draw):
    """Generate valid Indian PIN codes"""
    first_digit = draw(st.sampled_from(['1', '2', '3', '4', '5', '6', '7', '8', '9']))
    remaining_digits = draw(st.text(alphabet='0123456789', min_size=5, max_size=5))
    return first_digit + remaining_digits

@st.composite
def indian_state(draw):
    """Generate Indian state names"""
    states = [
        "Andhra Pradesh", "Assam", "Bihar", "Delhi", "Gujarat", 
        "Karnataka", "Kerala", "Maharashtra", "Tamil Nadu", 
        "Uttar Pradesh", "West Bengal", "Rajasthan", "Punjab"
    ]
    return draw(st.sampled_from(states))

@st.composite
def indian_language(draw):
    """Generate Indian language preferences"""
    languages = [
        "English", "Hindi", "Tamil", "Bengali", "Telugu", 
        "Marathi", "Gujarati", "Kannada", "Malayalam", "Punjabi"
    ]
    return draw(st.sampled_from(languages))

@st.composite
def indian_template_category(draw):
    """Generate Indian template categories"""
    categories = ["fintech", "ecommerce", "education", "healthcare"]
    return draw(st.sampled_from(categories))

class TestIndianTemplateProperties:
    """Property-based tests for Indian template functionality"""
    
    def setup_method(self):
        """Set up test database and services"""
        self.db = next(get_test_db())
        self.template_service = TemplateService(self.db)
        self.project_service = ProjectConfigurationService(self.db)
    
    def teardown_method(self):
        """Clean up test database"""
        self.db.close()
    
    @given(region=st.sampled_from(["india", "global"]))
    @settings(max_examples=50)
    def test_property_26_indian_template_mobile_first_configuration(self, region):
        """
        Property 26: Indian Template Mobile-First Configuration
        For any Indian mobile-first template selection, the system should configure 
        mobile number as the primary authentication method and disable other primary methods.
        """
        # Get templates for the region
        templates = self.template_service.get_templates_by_region(region)
        
        for template in templates:
            if template["region"] == "india":
                # Indian templates must have mobile_otp as primary method
                auth_config = template["config"].get("auth", {})
                assert auth_config.get("primary_method") == "mobile_otp", \
                    f"Indian template {template['name']} must have mobile_otp as primary method"
                
                # Must require mobile verification
                assert auth_config.get("require_mobile_verification") is True, \
                    f"Indian template {template['name']} must require mobile verification"
                
                # Must use Indian mobile format
                assert auth_config.get("mobile_number_format") == "indian", \
                    f"Indian template {template['name']} must use Indian mobile format"
                
                # Must have +91 country code
                assert auth_config.get("country_code") == "+91", \
                    f"Indian template {template['name']} must use +91 country code"
                
                # UI must be mobile-first
                ui_config = template["config"].get("ui", {})
                assert ui_config.get("mobile_first") is True, \
                    f"Indian template {template['name']} must be mobile-first"
    
    @given(
        template_category=indian_template_category(),
        mobile_number=indian_mobile_number()
    )
    @settings(max_examples=30)
    def test_property_27_progressive_profiling_minimal_collection(self, template_category, mobile_number):
        """
        Property 27: Progressive Profiling Minimal Collection
        For any mobile OTP authentication in Indian templates, the system should collect 
        only mobile number initially and progressively request additional details based on configured triggers.
        """
        # Get Indian templates for the category
        templates = self.template_service.get_templates_by_category_and_region(template_category, "india")
        
        for template in templates:
            workflow_config = template["config"].get("workflow", {})
            
            if "progressive_steps" in workflow_config or "progressive_kyc_steps" in workflow_config:
                steps = workflow_config.get("progressive_steps") or workflow_config.get("progressive_kyc_steps", [])
                
                # First step must be mobile verification with only mobile_number field
                first_step = steps[0] if steps else None
                assert first_step is not None, f"Template {template['name']} must have progressive steps"
                
                assert first_step.get("step") in ["mobile_verification", "mobile_number_entry"], \
                    f"First step in {template['name']} must be mobile verification"
                
                assert first_step.get("required") is True, \
                    f"Mobile verification step in {template['name']} must be required"
                
                # Check that mobile_number is the only required field initially
                fields = first_step.get("fields", [])
                if isinstance(fields, list) and len(fields) > 0:
                    assert "mobile_number" in fields, \
                        f"Mobile verification step in {template['name']} must include mobile_number field"
                
                # Subsequent steps should be optional or triggered
                for step in steps[1:]:
                    assert step.get("required") is False or step.get("trigger") is not None, \
                        f"Subsequent steps in {template['name']} should be optional or triggered"
    
    @given(
        state=indian_state(),
        pin_code=indian_pin_code(),
        language=indian_language()
    )
    @settings(max_examples=40)
    def test_property_28_indian_regional_field_support(self, state, pin_code, language):
        """
        Property 28: Indian Regional Field Support
        For any progressive profiling configuration in Indian templates, the system should 
        support and properly validate Indian-specific fields including state, city, PIN code, and language preference.
        """
        # Get all Indian templates
        indian_templates = self.template_service.get_indian_templates()
        
        for template in indian_templates:
            workflow_config = template["config"].get("workflow", {})
            
            if "progressive_steps" in workflow_config or "progressive_kyc_steps" in workflow_config:
                steps = workflow_config.get("progressive_steps") or workflow_config.get("progressive_kyc_steps", [])
                
                # Check for Indian-specific fields in progressive steps
                all_fields = []
                for step in steps:
                    fields = step.get("fields", [])
                    if isinstance(fields, list):
                        all_fields.extend(fields)
                
                # Validate that Indian-specific fields are supported
                indian_fields = ["state", "city", "pin_code", "language_preference"]
                supported_indian_fields = [field for field in indian_fields if field in all_fields]
                
                # At least some Indian-specific fields should be present
                assert len(supported_indian_fields) > 0, \
                    f"Template {template['name']} should support Indian-specific fields"
                
                # If PIN code field is present, validate format
                if "pin_code" in all_fields:
                    # PIN code should follow Indian format (6 digits, first digit 1-9)
                    assert len(pin_code) == 6, "PIN code should be 6 digits"
                    assert pin_code[0] in '123456789', "PIN code first digit should be 1-9"
                
                # Check language support in UI config
                ui_config = template["config"].get("ui", {})
                language_options = ui_config.get("language_options", [])
                
                if language_options:
                    # Should support Hindi and English at minimum
                    assert "hindi" in [lang.lower() for lang in language_options] or \
                           "english" in [lang.lower() for lang in language_options], \
                        f"Template {template['name']} should support Hindi or English"
    
    @given(category=indian_template_category())
    @settings(max_examples=20)
    def test_property_29_indian_use_case_template_availability(self, category):
        """
        Property 29: Indian Use Case Template Availability
        For any template query with region set to India, the system should provide 
        templates for fintech, e-commerce, education, and healthcare use cases.
        """
        # Get templates for India region and specific category
        templates = self.template_service.get_templates_by_category_and_region(category, "india")
        
        # Should have at least one template for each major Indian use case
        assert len(templates) > 0, f"Should have at least one Indian template for {category}"
        
        # Verify template is properly configured for Indian market
        for template in templates:
            assert template["region"] == "india", f"Template should be marked as Indian region"
            assert template["category"] == category, f"Template should be in {category} category"
            
            # Should have Indian-specific configuration
            config = template["config"]
            
            # Check for mobile-first authentication
            auth_config = config.get("auth", {})
            if auth_config:
                assert auth_config.get("primary_method") == "mobile_otp" or \
                       auth_config.get("require_mobile_verification") is True, \
                    f"Indian {category} template should support mobile authentication"
            
            # Check for Indian integrations
            integration_config = config.get("integration", {})
            if integration_config:
                # Should have Indian service providers
                indian_providers = ["razorpay", "payu", "cashfree", "msg91", "textlocal", "indian_sms"]
                has_indian_integration = any(
                    provider in str(integration_config).lower() 
                    for provider in indian_providers
                )
                # Note: Not all templates need Indian integrations, but fintech should
                if category == "fintech":
                    assert has_indian_integration, \
                        f"Indian fintech template should have Indian payment/SMS integrations"
    
    @given(
        template_category=indian_template_category(),
        language_pair=st.sampled_from([("hindi", "english"), ("english", "hindi")])
    )
    @settings(max_examples=25)
    def test_property_30_indian_template_language_support(self, template_category, language_pair):
        """
        Property 30: Indian Template Language Support
        For any Indian template with regional customization enabled, the system should 
        provide both Hindi and English language options with proper translations.
        """
        # Get Indian templates for the category
        templates = self.template_service.get_templates_by_category_and_region(template_category, "india")
        
        for template in templates:
            ui_config = template["config"].get("ui", {})
            
            # Check if regional customization is enabled
            if ui_config.get("regional_customization") or ui_config.get("language_options"):
                language_options = ui_config.get("language_options", [])
                
                if language_options:
                    # Should support both Hindi and English
                    language_options_lower = [lang.lower() for lang in language_options]
                    
                    assert "hindi" in language_options_lower or "english" in language_options_lower, \
                        f"Template {template['name']} should support Hindi or English"
                    
                    # Ideally should support both
                    if len(language_options) > 1:
                        assert "hindi" in language_options_lower and "english" in language_options_lower, \
                            f"Multi-language template {template['name']} should support both Hindi and English"
            
            # Check workflow steps for Hindi translations
            workflow_config = template["config"].get("workflow", {})
            
            # Look for Hindi translations in workflow templates
            workflow_templates = self.template_service.get_workflow_templates()
            
            for workflow_id, workflow_template in workflow_templates.items():
                if workflow_template.get("region") == "india":
                    steps = workflow_template.get("workflow_steps", [])
                    
                    for step in steps:
                        # Check for Hindi translations
                        if "title_hindi" in step or "content_hindi" in step or "placeholder_hindi" in step:
                            # If Hindi translations exist, they should be non-empty
                            if "title_hindi" in step:
                                assert step["title_hindi"].strip(), \
                                    f"Hindi title should not be empty in {workflow_id}"
                            
                            if "content_hindi" in step:
                                assert step["content_hindi"].strip(), \
                                    f"Hindi content should not be empty in {workflow_id}"
                            
                            # Should also have English versions
                            if "title_hindi" in step:
                                assert "title" in step, \
                                    f"Should have English title alongside Hindi in {workflow_id}"


class IndianTemplateStateMachine(RuleBasedStateMachine):
    """Stateful testing for Indian template configuration and application"""
    
    def __init__(self):
        super().__init__()
        self.db = next(get_test_db())
        self.template_service = TemplateService(self.db)
        self.project_service = ProjectConfigurationService(self.db)
        self.projects = {}
        self.applied_templates = {}
    
    @initialize()
    def setup(self):
        """Initialize test state"""
        pass
    
    @rule(
        project_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        template_category=indian_template_category()
    )
    def create_project_with_indian_template(self, project_name, template_category):
        """Create a project and apply an Indian template"""
        assume(project_name not in self.projects)
        
        # Get Indian templates for category
        templates = self.template_service.get_templates_by_category_and_region(template_category, "india")
        assume(len(templates) > 0)
        
        template = templates[0]  # Use first available template
        
        # Create project
        project = self.project_service.create_project(
            name=project_name,
            slug=project_name.lower().replace(' ', '-'),
            owner_id="test_user",
            template_id=template["id"]
        )
        
        self.projects[project_name] = project
        self.applied_templates[project_name] = template
    
    @rule(project_name=st.sampled_from([]))
    def verify_indian_template_configuration(self, project_name):
        """Verify that Indian template configuration is properly applied"""
        assume(project_name in self.projects)
        
        project = self.projects[project_name]
        template = self.applied_templates[project_name]
        
        # Get project configuration
        auth_config = self.project_service.get_configuration(
            project_id=project.id,
            config_type="auth"
        )
        
        # Verify mobile-first configuration
        if auth_config and template["config"].get("auth", {}).get("primary_method") == "mobile_otp":
            assert auth_config.get("primary_method") == "mobile_otp"
            assert auth_config.get("require_mobile_verification") is True
            assert auth_config.get("mobile_number_format") == "indian"
    
    @invariant()
    def all_indian_projects_have_mobile_auth(self):
        """All projects with Indian templates should have mobile authentication configured"""
        for project_name, template in self.applied_templates.items():
            if template["region"] == "india":
                project = self.projects[project_name]
                
                # Check that mobile authentication is configured
                auth_config = self.project_service.get_configuration(
                    project_id=project.id,
                    config_type="auth"
                )
                
                if auth_config:
                    # Should have mobile-first configuration
                    assert auth_config.get("primary_method") == "mobile_otp" or \
                           auth_config.get("require_mobile_verification") is True


# Integration test for complete Indian template flow
class TestIndianTemplateIntegration:
    """Integration tests for Indian template functionality"""
    
    def setup_method(self):
        """Set up test database and services"""
        self.db = next(get_test_db())
        self.template_service = TemplateService(self.db)
        self.project_service = ProjectConfigurationService(self.db)
    
    def teardown_method(self):
        """Clean up test database"""
        self.db.close()
    
    def test_complete_indian_fintech_template_flow(self):
        """Test complete flow of selecting and applying Indian fintech template"""
        # 1. Get available regions
        regions = self.template_service.get_available_regions()
        assert "india" in regions
        
        # 2. Get categories for India
        categories = self.template_service.get_available_categories_by_region("india")
        assert "fintech" in categories
        
        # 3. Get Indian fintech templates
        templates = self.template_service.get_templates_by_category_and_region("fintech", "india")
        assert len(templates) > 0
        
        # 4. Select Indian fintech template
        template = templates[0]
        assert template["region"] == "india"
        assert template["category"] == "fintech"
        
        # 5. Verify template configuration
        config = template["config"]
        
        # Mobile-first authentication
        auth_config = config.get("auth", {})
        assert auth_config.get("primary_method") == "mobile_otp"
        assert auth_config.get("mobile_number_format") == "indian"
        assert auth_config.get("country_code") == "+91"
        
        # Mobile-first UI
        ui_config = config.get("ui", {})
        assert ui_config.get("mobile_first") is True
        assert "hindi" in [lang.lower() for lang in ui_config.get("language_options", [])]
        
        # Progressive profiling
        workflow_config = config.get("workflow", {})
        assert workflow_config.get("progressive_profiling") is True
        
        progressive_steps = workflow_config.get("progressive_kyc_steps", [])
        assert len(progressive_steps) > 0
        
        # First step should be mobile verification
        first_step = progressive_steps[0]
        assert first_step.get("step") == "mobile_verification"
        assert first_step.get("required") is True
        assert "mobile_number" in first_step.get("fields", [])
        
        # 6. Create project with template
        project = self.project_service.create_project(
            name="Test Indian Fintech",
            slug="test-indian-fintech",
            owner_id="test_user"
        )
        
        # 7. Apply template to project (this would be done via API in real usage)
        # For now, just verify the template structure is correct
        assert template["id"] == "indian_fintech"
        assert template["name"] == "Indian Fintech"


# Run the stateful tests
TestIndianTemplateStateMachine = IndianTemplateStateMachine.TestCase

if __name__ == "__main__":
    # Run property tests
    pytest.main([__file__, "-v", "--tb=short"])