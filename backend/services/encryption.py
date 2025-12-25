"""
Encryption Service

This module provides encryption/decryption functionality for sensitive data
like OAuth tokens, API keys, and other user credentials.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional

class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self):
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption with key from environment"""
        # Get encryption key from environment or generate one
        encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if not encryption_key:
            # In production, this should be set in environment variables
            # For development, we'll generate a key (not recommended for production)
            print("WARNING: No ENCRYPTION_KEY found in environment. Generating temporary key.")
            encryption_key = Fernet.generate_key().decode()
            print(f"Generated encryption key: {encryption_key}")
            print("Set this as ENCRYPTION_KEY environment variable for production")
        
        # If key is a string, encode it
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        # Derive key if needed
        if len(encryption_key) != 44:  # Fernet key should be 44 bytes when base64 encoded
            # Derive key from password using PBKDF2
            salt = b'universal_auth_salt'  # In production, use random salt per installation
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(encryption_key))
        else:
            key = encryption_key
        
        self._fernet = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        if not data:
            return ""
        
        encrypted_data = self._fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted plain text data
        """
        if not encrypted_data:
            return ""
        
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {str(e)}")
    
    def encrypt_dict(self, data: dict) -> dict:
        """
        Encrypt sensitive fields in a dictionary
        
        Args:
            data: Dictionary with sensitive fields
            
        Returns:
            Dictionary with encrypted sensitive fields
        """
        sensitive_fields = [
            'access_token', 'refresh_token', 'api_key', 'secret', 
            'password', 'private_key', 'client_secret'
        ]
        
        encrypted_data = data.copy()
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict) -> dict:
        """
        Decrypt sensitive fields in a dictionary
        
        Args:
            data: Dictionary with encrypted sensitive fields
            
        Returns:
            Dictionary with decrypted sensitive fields
        """
        sensitive_fields = [
            'access_token', 'refresh_token', 'api_key', 'secret',
            'password', 'private_key', 'client_secret'
        ]
        
        decrypted_data = data.copy()
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt(str(decrypted_data[field]))
                except ValueError:
                    # Field might not be encrypted (backward compatibility)
                    pass
        
        return decrypted_data

# Global encryption service instance
encryption_service = EncryptionService()