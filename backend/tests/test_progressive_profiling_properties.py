"""
Property-Based Tests for Progressive Profiling

This module contains property-based tests that validate universal correctness
properties for the progressive profiling system using Hypothesis.

Feature: universal-auth, Properties 9, 10: Progressive profiling functionality
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hypothesis import given, strategies as st, assume, settings
from models.user import Base, User, UserProfile
from services.user_service import UserService, ProgressiveProfilingConfig
from datetime import datetime


def create_test_user_service():
    """Create user service with in-memory database for property testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    return UserService(session), session


class TestProgressiveProfilingProperties:
    """Property-based tests for Progressive Profiling correctness"""
    
    # Strategy for generating valid email addresses
    valid_emails = st.emails()
    
    # Strategy for generating valid phone numbers
    valid_phones = st.integers(min_value=6000000000, max_value=9999999999).map(lambda x: f"+91{x}")
    
    # Strategy for generating session counts
    session_counts = st.integers(min_value=0, max_value=20)
    
    # Strategy for generating profile field values
    profile_field_values = st.one_of(
        st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd'))),
        st.none()
    )
    
    # Strategy for generating profile data
    profile_data_strategy = st.fixed_dictionaries({
        'first_name': profile_field_values,
        'last_name': profile_field_values,
        'company': profile_field_values,
        'job_title': profile_field_values,
        'location': profile_field_values,
        'website': profile_field_values,
        'bio': profile_field_values,
        'timezone': profile_field_values
    })
    
    @given(email=valid_emails)
    @settings(max_examples=20, deadline=3000)
    def test_progressive_profiling_field_requirements_property(self, email):
        """
        Property 9: Progressive Profiling Field Requirements
        
        For any new user registration, the system should collect only the 
        minimal required fields initially, deferring optional fields to 
        subsequent sessions based on configuration.
        
        **Feature: universal-auth, Property 9: Progressive Profiling Field Requirements**
        **Validates: Requirements 3.1**
        """
        user_service, session = create_test_user_service()
        
        try:
            # Create new user
            user = user_service.create_user(email=email)
            
            # New user should have session count 0
            assert user.session_count == 0
            
            # Get progressive fields for new user (session 0)
            fields = user_service.get_progressive_profiling_fields(user.id)
            
            # New user should not be asked for any progressive fields initially
            assert fields == [], f"New user should not have progressive fields, got: {fields}"
            
            # Test session count 1 - should still have no progressive fields
            user.session_count = 1
            session.commit()
            fields = user_service.get_progressive_profiling_fields(user.id)
            assert fields == [], f"Session 1 should not have progressive fields, got: {fields}"
            
            # Test session count 2 - should ask for last_name
            user.session_count = 2
            session.commit()
            fields = user_service.get_progressive_profiling_fields(user.id)
            assert "last_name" in fields, f"Session 2 should include last_name, got: {fields}"
            
            # Fill last_name and check it's removed from progressive fields
            user_service.update_user_profile(user.id, {"last_name": "TestLastName"})
            fields = user_service.get_progressive_profiling_fields(user.id)
            assert "last_name" not in fields, f"Filled last_name should be removed from progressive fields"
            
            # Test session count 3 - should ask for company and job_title
            user.session_count = 3
            session.commit()
            fields = user_service.get_progressive_profiling_fields(user.id)
            assert "company" in fields, f"Session 3 should include company, got: {fields}"
            assert "job_title" in fields, f"Session 3 should include job_title, got: {fields}"
            
            # Test session count 5 - should ask for location and timezone
            user.session_count = 5
            session.commit()
            fields = user_service.get_progressive_profiling_fields(user.id)
            expected_fields = {"company", "job_title", "location", "timezone"}
            actual_fields = set(fields)
            assert expected_fields.issubset(actual_fields), f"Session 5 should include {expected_fields}, got: {actual_fields}"
            
        finally:
            session.close()
    
    @given(
        email=valid_emails,
        session_count=session_counts
    )
    @settings(max_examples=30, deadline=3000)
    def test_progressive_fields_based_on_session_count(self, email, session_count):
        """
        Property: Progressive fields should be determined by session count
        
        For any user and session count, the progressive fields should match
        the configuration thresholds and exclude already filled fields.
        
        **Feature: universal-auth, Property 9: Progressive Profiling Field Requirements**
        **Validates: Requirements 3.1**
        """
        user_service, session = create_test_user_service()
        
        try:
            # Create user
            user = user_service.create_user(email=email)
            user.session_count = session_count
            session.commit()
            
            # Get progressive fields
            fields = user_service.get_progressive_profiling_fields(user.id)
            
            # Calculate expected fields based on configuration
            config = ProgressiveProfilingConfig()
            expected_fields = []
            
            for threshold, threshold_fields in config.PROGRESSIVE_FIELDS.items():
                if session_count >= threshold:
                    expected_fields.extend(threshold_fields)
            
            # All returned fields should be in expected fields
            for field in fields:
                assert field in expected_fields, f"Field {field} not expected for session count {session_count}"
            
            # Fields should not include already filled fields
            profile = user.profile
            for field in expected_fields:
                if hasattr(profile, field) and getattr(profile, field):
                    assert field not in fields, f"Filled field {field} should not be in progressive fields"
            
        finally:
            session.close()
    
    @given(
        email=valid_emails,
        profile_data=profile_data_strategy
    )
    @settings(max_examples=25, deadline=3000)
    def test_profile_completion_calculation_property(self, email, profile_data):
        """
        Property 10: Profile Completion Calculation
        
        For any user profile state, the system should accurately calculate 
        completion percentage based on filled required and optional fields 
        according to the configured schema.
        
        **Feature: universal-auth, Property 10: Profile Completion Calculation**
        **Validates: Requirements 3.4**
        """
        user_service, session = create_test_user_service()
        
        try:
            # Create user
            user = user_service.create_user(email=email)
            initial_completion = user.profile.completion_percentage
            
            # Update profile with test data
            # Filter out None values to only update fields with actual values
            update_data = {k: v for k, v in profile_data.items() if v is not None}
            
            if update_data:
                user_service.update_user_profile(user.id, update_data)
                updated_user = user_service.get_user_by_id(user.id)
                updated_completion = updated_user.profile.completion_percentage
                
                # Completion should increase when fields are added
                assert updated_completion >= initial_completion, \
                    f"Completion should not decrease: {initial_completion} -> {updated_completion}"
                
                # If we added fields, completion should increase (unless all fields were already at max weight)
                if len(update_data) > 0 and initial_completion < 100:
                    assert updated_completion > initial_completion, \
                        f"Adding fields should increase completion: {initial_completion} -> {updated_completion}"
            
            # Test completion calculation accuracy
            config = ProgressiveProfilingConfig()
            total_weight = sum(config.ALL_FIELDS.values())
            
            # Calculate expected completion manually
            expected_weight = 0
            profile = user.profile if not update_data else updated_user.profile
            user_obj = user if not update_data else updated_user
            
            for field, weight in config.ALL_FIELDS.items():
                if field == "email":
                    if user_obj.email:
                        expected_weight += weight
                elif field == "phone":
                    if user_obj.phone:
                        expected_weight += weight
                else:
                    if hasattr(profile, field) and getattr(profile, field):
                        expected_weight += weight
            
            expected_completion = int((expected_weight / total_weight) * 100)
            actual_completion = profile.completion_percentage
            
            assert actual_completion == expected_completion, \
                f"Completion calculation mismatch: expected {expected_completion}%, got {actual_completion}%"
            
        finally:
            session.close()
    
    @given(
        email=valid_emails,
        phone=st.one_of(valid_phones, st.none())
    )
    @settings(max_examples=20, deadline=3000)
    def test_required_fields_completion_property(self, email, phone):
        """
        Property: Required fields completion should be tracked correctly
        
        For any user, the required_fields_completed flag should accurately
        reflect whether all required fields are filled.
        
        **Feature: universal-auth, Property 10: Profile Completion Calculation**
        **Validates: Requirements 3.4**
        """
        user_service, session = create_test_user_service()
        
        try:
            # Create user
            user = user_service.create_user(email=email, phone=phone)
            
            config = ProgressiveProfilingConfig()
            
            # Check required fields completion
            profile = user.profile
            all_required_filled = True
            
            for field in config.REQUIRED_FIELDS:
                if field == "email":
                    if not user.email:
                        all_required_filled = False
                        break
                else:
                    if not (hasattr(profile, field) and getattr(profile, field)):
                        all_required_filled = False
                        break
            
            assert profile.required_fields_completed == all_required_filled, \
                f"Required fields completion mismatch: expected {all_required_filled}, got {profile.required_fields_completed}"
            
            # If not all required fields are filled, add them and test again
            if not all_required_filled:
                updates = {}
                for field in config.REQUIRED_FIELDS:
                    if field == "first_name" and not profile.first_name:
                        updates["first_name"] = "TestFirstName"
                
                if updates:
                    user_service.update_user_profile(user.id, updates)
                    updated_user = user_service.get_user_by_id(user.id)
                    
                    # Check if completion status changed appropriately
                    new_all_required_filled = True
                    for field in config.REQUIRED_FIELDS:
                        if field == "email":
                            if not updated_user.email:
                                new_all_required_filled = False
                                break
                        else:
                            if not (hasattr(updated_user.profile, field) and getattr(updated_user.profile, field)):
                                new_all_required_filled = False
                                break
                    
                    assert updated_user.profile.required_fields_completed == new_all_required_filled, \
                        f"Updated required fields completion mismatch: expected {new_all_required_filled}, got {updated_user.profile.required_fields_completed}"
            
        finally:
            session.close()
    
    @given(
        email=valid_emails,
        session_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=15, deadline=3000)
    def test_session_increment_affects_progressive_fields(self, email, session_count):
        """
        Property: Session count increments should affect progressive field availability
        
        For any user, incrementing session count should potentially unlock
        new progressive fields based on configuration thresholds.
        
        **Feature: universal-auth, Property 9: Progressive Profiling Field Requirements**
        **Validates: Requirements 3.1**
        """
        user_service, session = create_test_user_service()
        
        try:
            # Create user
            user = user_service.create_user(email=email)
            
            # Track fields at different session counts
            fields_by_session = {}
            
            for i in range(session_count + 1):
                user.session_count = i
                session.commit()
                fields = user_service.get_progressive_profiling_fields(user.id)
                fields_by_session[i] = set(fields)
            
            # Fields should generally increase or stay the same as session count increases
            # (unless fields are filled, which would remove them)
            config = ProgressiveProfilingConfig()
            
            for i in range(1, session_count + 1):
                prev_session = i - 1
                current_session = i
                
                # Check if new fields are unlocked at threshold sessions
                for threshold, threshold_fields in config.PROGRESSIVE_FIELDS.items():
                    if current_session >= threshold and prev_session < threshold:
                        # New fields should be available (unless already filled)
                        for field in threshold_fields:
                            # Check if field is already filled
                            profile = user.profile
                            field_filled = hasattr(profile, field) and getattr(profile, field)
                            
                            if not field_filled:
                                assert field in fields_by_session[current_session], \
                                    f"Field {field} should be available at session {current_session} (threshold {threshold})"
            
        finally:
            session.close()
    
    @given(email=valid_emails)
    @settings(max_examples=15, deadline=3000)
    def test_profile_completion_monotonic_property(self, email):
        """
        Property: Profile completion should be monotonic (never decrease)
        
        For any user, adding profile information should never decrease
        the completion percentage.
        
        **Feature: universal-auth, Property 10: Profile Completion Calculation**
        **Validates: Requirements 3.4**
        """
        user_service, session = create_test_user_service()
        
        try:
            # Create user
            user = user_service.create_user(email=email)
            initial_completion = user.profile.completion_percentage
            
            # Add fields one by one and ensure completion never decreases
            fields_to_add = [
                ("first_name", "John"),
                ("last_name", "Doe"),
                ("company", "Test Corp"),
                ("job_title", "Developer"),
                ("location", "Test City")
            ]
            
            prev_completion = initial_completion
            
            for field_name, field_value in fields_to_add:
                user_service.update_user_profile(user.id, {field_name: field_value})
                updated_user = user_service.get_user_by_id(user.id)
                new_completion = updated_user.profile.completion_percentage
                
                assert new_completion >= prev_completion, \
                    f"Completion decreased after adding {field_name}: {prev_completion}% -> {new_completion}%"
                
                prev_completion = new_completion
            
        finally:
            session.close()
    
    @given(
        email=valid_emails,
        profile_updates=st.lists(
            st.tuples(
                st.sampled_from(["first_name", "last_name", "company", "job_title", "location"]),
                st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
            ),
            min_size=0,
            max_size=5,
            unique_by=lambda x: x[0]  # Unique field names
        )
    )
    @settings(max_examples=20, deadline=3000)
    def test_profile_completion_status_consistency(self, email, profile_updates):
        """
        Property: Profile completion status should be consistent
        
        For any user and profile updates, the completion status returned
        by get_profile_completion_status should match the actual profile state.
        
        **Feature: universal-auth, Property 10: Profile Completion Calculation**
        **Validates: Requirements 3.4**
        """
        user_service, session = create_test_user_service()
        
        try:
            # Create user
            user = user_service.create_user(email=email)
            
            # Apply profile updates
            if profile_updates:
                update_dict = dict(profile_updates)
                user_service.update_user_profile(user.id, update_dict)
            
            # Get completion status
            status = user_service.get_profile_completion_status(user.id)
            updated_user = user_service.get_user_by_id(user.id)
            
            # Verify status consistency
            assert status["completion_percentage"] == updated_user.profile.completion_percentage, \
                "Completion percentage mismatch between status and profile"
            
            assert status["required_fields_completed"] == updated_user.profile.required_fields_completed, \
                "Required fields completion mismatch between status and profile"
            
            assert status["session_count"] == updated_user.session_count, \
                "Session count mismatch between status and user"
            
            # Verify missing required fields are actually missing
            config = ProgressiveProfilingConfig()
            for field in status["missing_required_fields"]:
                if field == "email":
                    assert not updated_user.email, f"Email should be missing but is present: {updated_user.email}"
                else:
                    field_value = getattr(updated_user.profile, field, None)
                    assert not field_value, f"Field {field} should be missing but has value: {field_value}"
            
            # Verify next progressive fields are appropriate for session count
            expected_progressive = user_service.get_progressive_profiling_fields(user.id)
            assert set(status["next_progressive_fields"]) == set(expected_progressive), \
                f"Progressive fields mismatch: expected {expected_progressive}, got {status['next_progressive_fields']}"
            
        finally:
            session.close()


class TestProgressiveProfilingConfiguration:
    """Property-based tests for Progressive Profiling Configuration"""
    
    def test_configuration_consistency(self):
        """
        Property: Progressive profiling configuration should be consistent
        
        The configuration should have valid structure and all referenced
        fields should exist in the ALL_FIELDS mapping.
        """
        config = ProgressiveProfilingConfig()
        
        # All progressive fields should be in ALL_FIELDS
        for session_count, fields in config.PROGRESSIVE_FIELDS.items():
            for field in fields:
                assert field in config.ALL_FIELDS, \
                    f"Progressive field {field} not found in ALL_FIELDS"
        
        # Required fields should be in ALL_FIELDS
        for field in config.REQUIRED_FIELDS:
            assert field in config.ALL_FIELDS, \
                f"Required field {field} not found in ALL_FIELDS"
        
        # Session thresholds should be positive integers
        for session_count in config.PROGRESSIVE_FIELDS.keys():
            assert isinstance(session_count, int), \
                f"Session count {session_count} should be integer"
            assert session_count >= 0, \
                f"Session count {session_count} should be non-negative"
        
        # Field weights should be positive
        for field, weight in config.ALL_FIELDS.items():
            assert isinstance(weight, int), \
                f"Weight for {field} should be integer"
            assert weight > 0, \
                f"Weight for {field} should be positive"