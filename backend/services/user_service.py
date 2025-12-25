"""
User Service

This module provides user management functionality including user creation,
profile management, and progressive profiling logic.
"""

from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from models.user import User, UserProfile, ProviderAccount, TenantMembership
from services.encryption import encryption_service
import uuid

class ProgressiveProfilingConfig:
    """Configuration for progressive profiling"""
    
    # Required fields for basic profile
    REQUIRED_FIELDS = ["first_name", "email"]
    
    # Fields to collect based on session count
    PROGRESSIVE_FIELDS = {
        1: [],  # First session - only required fields
        2: ["last_name"],  # Second session
        3: ["company", "job_title"],  # Third session
        5: ["location", "timezone"],  # Fifth session
        10: ["website", "bio"]  # Tenth session
    }
    
    # All possible profile fields with weights for completion calculation
    ALL_FIELDS = {
        "first_name": 15,  # Required - high weight
        "last_name": 10,
        "email": 15,  # Required - high weight
        "company": 8,
        "job_title": 8,
        "location": 5,
        "timezone": 3,
        "website": 5,
        "bio": 3,
        "avatar_url": 8,
        "phone": 10
    }

class UserService:
    """Service for user management and progressive profiling"""
    
    def __init__(self, db: Session):
        self.db = db
        self.profiling_config = ProgressiveProfilingConfig()
    
    def create_user(self, email: Optional[str] = None, phone: Optional[str] = None, 
                   provider_data: Optional[Dict[str, Any]] = None) -> User:
        """
        Create a new user with basic profile
        
        Args:
            email: User email address
            phone: User phone number
            provider_data: Data from OAuth provider
            
        Returns:
            Created user instance
        """
        # Create user
        user = User(
            email=email,
            phone=phone,
            is_verified=bool(provider_data),  # OAuth users are pre-verified
            session_count=0
        )
        
        self.db.add(user)
        self.db.flush()  # Get user ID
        
        # Create basic profile
        profile_data = {}
        if provider_data:
            profile_data.update({
                "first_name": provider_data.get("first_name"),
                "last_name": provider_data.get("last_name"),
                "display_name": provider_data.get("name"),
                "avatar_url": provider_data.get("avatar_url")
            })
        
        profile = UserProfile(
            user_id=user.id,
            **profile_data
        )
        
        self.db.add(profile)
        
        # Calculate initial completion percentage
        self._update_profile_completion(profile)
        
        self.db.commit()
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """Get user by phone number"""
        return self.db.query(User).filter(User.phone == phone).first()
    
    def get_user_by_provider(self, provider: str, provider_user_id: str) -> Optional[User]:
        """Get user by OAuth provider account"""
        provider_account = self.db.query(ProviderAccount).filter(
            and_(
                ProviderAccount.provider == provider,
                ProviderAccount.provider_user_id == provider_user_id
            )
        ).first()
        
        if provider_account:
            return self.get_user_by_id(provider_account.user_id)
        return None
    
    def create_or_update_provider_account(self, user_id: str, provider: str, 
                                        provider_data: Dict[str, Any]) -> ProviderAccount:
        """
        Create or update OAuth provider account
        
        Args:
            user_id: User ID
            provider: Provider name (google, github, etc.)
            provider_data: Provider account data
            
        Returns:
            Provider account instance
        """
        # Check if provider account exists
        existing_account = self.db.query(ProviderAccount).filter(
            and_(
                ProviderAccount.user_id == user_id,
                ProviderAccount.provider == provider
            )
        ).first()
        
        if existing_account:
            # Update existing account
            existing_account.provider_user_id = provider_data.get("provider_user_id")
            existing_account.provider_username = provider_data.get("username")
            existing_account.provider_email = provider_data.get("email")
            existing_account.access_token = provider_data.get("access_token")
            existing_account.refresh_token = provider_data.get("refresh_token")
            existing_account.token_expires_at = provider_data.get("expires_at")
            existing_account.provider_data = provider_data.get("raw_data", {})
            existing_account.last_used = datetime.utcnow()
            existing_account.updated_at = datetime.utcnow()
            
            self.db.commit()
            return existing_account
        else:
            # Create new provider account
            account = ProviderAccount(
                user_id=user_id,
                provider=provider,
                provider_user_id=provider_data.get("provider_user_id"),
                provider_username=provider_data.get("username"),
                provider_email=provider_data.get("email"),
                access_token=provider_data.get("access_token"),
                refresh_token=provider_data.get("refresh_token"),
                token_expires_at=provider_data.get("expires_at"),
                provider_data=provider_data.get("raw_data", {}),
                last_used=datetime.utcnow()
            )
            
            self.db.add(account)
            self.db.commit()
            return account
    
    def update_user_profile(self, user_id: str, profile_updates: Dict[str, Any]) -> UserProfile:
        """
        Update user profile with progressive profiling logic
        
        Args:
            user_id: User ID
            profile_updates: Profile field updates
            
        Returns:
            Updated profile instance
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        profile = user.profile
        if not profile:
            # Create profile if it doesn't exist
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
        
        # Update profile fields
        for field, value in profile_updates.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        
        profile.updated_at = datetime.utcnow()
        
        # Update completion percentage
        self._update_profile_completion(profile)
        
        self.db.commit()
        return profile
    
    def get_progressive_profiling_fields(self, user_id: str) -> List[str]:
        """
        Get fields that should be collected based on user's session count
        
        Args:
            user_id: User ID
            
        Returns:
            List of field names to collect
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return []
        
        session_count = user.session_count
        fields_to_collect = []
        
        # Get fields based on session count
        for session_threshold, fields in self.profiling_config.PROGRESSIVE_FIELDS.items():
            if session_count >= session_threshold:
                fields_to_collect.extend(fields)
        
        # Filter out fields that are already filled
        profile = user.profile
        if profile:
            filled_fields = []
            for field in fields_to_collect:
                if hasattr(profile, field) and getattr(profile, field):
                    filled_fields.append(field)
            
            # Remove already filled fields
            fields_to_collect = [f for f in fields_to_collect if f not in filled_fields]
        
        return fields_to_collect
    
    def increment_session_count(self, user_id: str) -> int:
        """
        Increment user session count for progressive profiling
        
        Args:
            user_id: User ID
            
        Returns:
            New session count
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        user.session_count += 1
        user.last_login = datetime.utcnow()
        
        self.db.commit()
        return user.session_count
    
    def _update_profile_completion(self, profile: UserProfile) -> None:
        """
        Calculate and update profile completion percentage
        
        Args:
            profile: User profile instance
        """
        total_weight = sum(self.profiling_config.ALL_FIELDS.values())
        completed_weight = 0
        
        # Get user if not loaded
        user = profile.user if profile.user else self.get_user_by_id(profile.user_id)
        
        # Check each field
        for field, weight in self.profiling_config.ALL_FIELDS.items():
            if field == "email":
                # Check email from user record
                if user and user.email:
                    completed_weight += weight
            elif field == "phone":
                # Check phone from user record
                if user and user.phone:
                    completed_weight += weight
            else:
                # Check profile field
                if hasattr(profile, field) and getattr(profile, field):
                    completed_weight += weight
        
        # Calculate percentage
        completion_percentage = int((completed_weight / total_weight) * 100)
        profile.completion_percentage = completion_percentage
        
        # Check if required fields are completed
        required_completed = True
        for field in self.profiling_config.REQUIRED_FIELDS:
            if field == "email":
                if not (user and user.email):
                    required_completed = False
                    break
            else:
                if not (hasattr(profile, field) and getattr(profile, field)):
                    required_completed = False
                    break
        
        profile.required_fields_completed = required_completed
    
    def get_profile_completion_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed profile completion status
        
        Args:
            user_id: User ID
            
        Returns:
            Profile completion status
        """
        user = self.get_user_by_id(user_id)
        if not user or not user.profile:
            return {
                "completion_percentage": 0,
                "required_fields_completed": False,
                "missing_required_fields": self.profiling_config.REQUIRED_FIELDS,
                "next_progressive_fields": [],
                "session_count": user.session_count if user else 0
            }
        
        profile = user.profile
        
        # Find missing required fields
        missing_required = []
        for field in self.profiling_config.REQUIRED_FIELDS:
            if field == "email":
                if not user.email:
                    missing_required.append(field)
            else:
                if not (hasattr(profile, field) and getattr(profile, field)):
                    missing_required.append(field)
        
        # Get next progressive fields
        next_fields = self.get_progressive_profiling_fields(user_id)
        
        return {
            "completion_percentage": profile.completion_percentage,
            "required_fields_completed": profile.required_fields_completed,
            "missing_required_fields": missing_required,
            "next_progressive_fields": next_fields,
            "session_count": user.session_count,
            "total_possible_fields": list(self.profiling_config.ALL_FIELDS.keys())
        }
    
    def search_users(self, query: str, limit: int = 10) -> List[User]:
        """
        Search users by email, phone, or name
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching users
        """
        return self.db.query(User).join(UserProfile).filter(
            or_(
                User.email.ilike(f"%{query}%"),
                User.phone.ilike(f"%{query}%"),
                UserProfile.first_name.ilike(f"%{query}%"),
                UserProfile.last_name.ilike(f"%{query}%"),
                UserProfile.display_name.ilike(f"%{query}%")
            )
        ).limit(limit).all()
    
    def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate user account
        
        Args:
            user_id: User ID
            
        Returns:
            Success status
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    def reactivate_user(self, user_id: str) -> bool:
        """
        Reactivate user account
        
        Args:
            user_id: User ID
            
        Returns:
            Success status
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = True
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True