"""
API Key Encryption Service

This service handles secure encryption and decryption of API keys
using industry-standard encryption methods.
"""

import os
import base64
import hashlib
import secrets
from typing import Tuple, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)

class APIKeyEncryption:
    """Service for encrypting and decrypting API keys"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service
        
        Args:
            master_key: Master encryption key (from environment if not provided)
        """
        self.master_key = master_key or os.getenv("API_KEY_MASTER_KEY")
        if not self.master_key:
            raise ValueError("API_KEY_MASTER_KEY environment variable must be set")
        
        # Derive encryption key from master key
        self.encryption_key = self._derive_key(self.master_key.encode())
        self.fernet = Fernet(self.encryption_key)
    
    def _derive_key(self, password: bytes, salt: Optional[bytes] = None) -> bytes:
        """
        Derive encryption key from password using PBKDF2
        
        Args:
            password: Master password
            salt: Salt for key derivation (generated if not provided)
            
        Returns:
            Derived encryption key
        """
        if salt is None:
            # Use a fixed salt for consistent key derivation
            # In production, consider using per-key salts stored with the encrypted data
            salt = b"universal_auth_api_keys_salt_v1"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt_api_key(self, api_key: str) -> Tuple[bytes, str]:
        """
        Encrypt an API key
        
        Args:
            api_key: Plain text API key
            
        Returns:
            Tuple of (encrypted_key_bytes, key_hash)
        """
        if not api_key:
            raise ValueError("API key cannot be empty")
        
        try:
            # Encrypt the API key
            encrypted_key = self.fernet.encrypt(api_key.encode())
            
            # Generate hash for verification (not for decryption)
            key_hash = self._generate_key_hash(api_key)
            
            logger.info("API key encrypted successfully")
            return encrypted_key, key_hash
            
        except Exception as e:
            logger.error(f"Failed to encrypt API key: {e}")
            raise
    
    def decrypt_api_key(self, encrypted_key: bytes) -> str:
        """
        Decrypt an API key
        
        Args:
            encrypted_key: Encrypted API key bytes
            
        Returns:
            Plain text API key
        """
        if not encrypted_key:
            raise ValueError("Encrypted key cannot be empty")
        
        try:
            # Decrypt the API key
            decrypted_key = self.fernet.decrypt(encrypted_key)
            
            logger.info("API key decrypted successfully")
            return decrypted_key.decode()
            
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise
    
    def _generate_key_hash(self, api_key: str) -> str:
        """
        Generate a hash of the API key for verification
        
        Args:
            api_key: Plain text API key
            
        Returns:
            SHA-256 hash of the API key
        """
        # Add salt to prevent rainbow table attacks
        salt = "universal_auth_key_hash_salt_v1"
        salted_key = f"{salt}{api_key}{salt}"
        
        hash_obj = hashlib.sha256(salted_key.encode())
        return hash_obj.hexdigest()
    
    def verify_api_key(self, api_key: str, stored_hash: str) -> bool:
        """
        Verify an API key against its stored hash
        
        Args:
            api_key: Plain text API key to verify
            stored_hash: Stored hash to verify against
            
        Returns:
            True if the key matches the hash
        """
        try:
            computed_hash = self._generate_key_hash(api_key)
            return secrets.compare_digest(computed_hash, stored_hash)
        except Exception as e:
            logger.error(f"Failed to verify API key: {e}")
            return False
    
    def rotate_encryption_key(self, old_master_key: str, new_master_key: str, 
                            encrypted_data: bytes) -> bytes:
        """
        Rotate encryption key by re-encrypting data with new key
        
        Args:
            old_master_key: Previous master key
            new_master_key: New master key
            encrypted_data: Data encrypted with old key
            
        Returns:
            Data encrypted with new key
        """
        try:
            # Create old encryption instance
            old_key = self._derive_key(old_master_key.encode())
            old_fernet = Fernet(old_key)
            
            # Decrypt with old key
            plain_data = old_fernet.decrypt(encrypted_data)
            
            # Create new encryption instance
            new_key = self._derive_key(new_master_key.encode())
            new_fernet = Fernet(new_key)
            
            # Encrypt with new key
            new_encrypted_data = new_fernet.encrypt(plain_data)
            
            logger.info("Encryption key rotated successfully")
            return new_encrypted_data
            
        except Exception as e:
            logger.error(f"Failed to rotate encryption key: {e}")
            raise
    
    def generate_secure_key(self, length: int = 32) -> str:
        """
        Generate a cryptographically secure random key
        
        Args:
            length: Length of the key in bytes
            
        Returns:
            Base64-encoded random key
        """
        random_bytes = secrets.token_bytes(length)
        return base64.urlsafe_b64encode(random_bytes).decode()
    
    def mask_api_key(self, api_key: str, visible_chars: int = 4) -> str:
        """
        Mask an API key for display purposes
        
        Args:
            api_key: Plain text API key
            visible_chars: Number of characters to show at the end
            
        Returns:
            Masked API key (e.g., "sk-...xyz123")
        """
        if not api_key or len(api_key) <= visible_chars:
            return "***"
        
        prefix = api_key[:2] if api_key.startswith(('sk-', 'pk-', 'ak-')) else ""
        suffix = api_key[-visible_chars:]
        
        if prefix:
            return f"{prefix}...{suffix}"
        else:
            return f"...{suffix}"
    
    def validate_key_format(self, api_key: str, provider: str) -> bool:
        """
        Validate API key format for specific providers
        
        Args:
            api_key: API key to validate
            provider: Provider name (openai, gemini, etc.)
            
        Returns:
            True if the key format is valid
        """
        if not api_key:
            return False
        
        # Provider-specific validation
        if provider.lower() == "openai":
            return api_key.startswith("sk-") and len(api_key) >= 20
        elif provider.lower() == "gemini":
            return len(api_key) >= 20  # Gemini keys are typically long strings
        elif provider.lower() == "anthropic":
            return api_key.startswith("sk-ant-") and len(api_key) >= 20
        elif provider.lower() == "azure_openai":
            return len(api_key) >= 20  # Azure keys are typically 32 chars
        else:
            # Generic validation for custom providers
            return len(api_key) >= 8
    
    def estimate_key_strength(self, api_key: str) -> dict:
        """
        Estimate the strength of an API key
        
        Args:
            api_key: API key to analyze
            
        Returns:
            Dictionary with strength metrics
        """
        if not api_key:
            return {"strength": "invalid", "score": 0}
        
        score = 0
        issues = []
        
        # Length check
        if len(api_key) >= 32:
            score += 30
        elif len(api_key) >= 20:
            score += 20
        else:
            issues.append("Key is too short")
        
        # Character diversity
        has_upper = any(c.isupper() for c in api_key)
        has_lower = any(c.islower() for c in api_key)
        has_digit = any(c.isdigit() for c in api_key)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in api_key)
        
        char_types = sum([has_upper, has_lower, has_digit, has_special])
        score += char_types * 15
        
        if char_types < 3:
            issues.append("Key lacks character diversity")
        
        # Entropy estimation (simplified)
        unique_chars = len(set(api_key))
        if unique_chars > len(api_key) * 0.7:
            score += 20
        elif unique_chars < len(api_key) * 0.3:
            issues.append("Key has low entropy")
        
        # Determine strength level
        if score >= 80:
            strength = "strong"
        elif score >= 60:
            strength = "moderate"
        elif score >= 40:
            strength = "weak"
        else:
            strength = "very_weak"
        
        return {
            "strength": strength,
            "score": min(score, 100),
            "issues": issues,
            "length": len(api_key),
            "character_types": char_types,
            "unique_characters": unique_chars
        }

# Utility functions for key management
def generate_master_key() -> str:
    """Generate a new master key for encryption"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

def validate_master_key(master_key: str) -> bool:
    """Validate master key format"""
    try:
        decoded = base64.urlsafe_b64decode(master_key.encode())
        return len(decoded) >= 32
    except Exception:
        return False