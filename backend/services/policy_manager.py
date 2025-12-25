"""
Policy Manager

This module manages OPA policy bundles, distribution, and versioning
for the Universal Auth System.
"""

import os
import json
import yaml
import asyncio
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import aiofiles
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class PolicyBundle:
    """Policy bundle metadata"""
    version: str
    policies: Dict[str, str]  # filename -> content
    metadata: Dict[str, Any]
    created_at: datetime
    checksum: str
    
    @classmethod
    def create(cls, policies: Dict[str, str], metadata: Optional[Dict[str, Any]] = None) -> 'PolicyBundle':
        """Create a new policy bundle"""
        content = json.dumps(policies, sort_keys=True)
        checksum = hashlib.sha256(content.encode()).hexdigest()
        version = f"v{int(datetime.utcnow().timestamp())}"
        
        return cls(
            version=version,
            policies=policies,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            checksum=checksum
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "version": self.version,
            "policies": self.policies,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "checksum": self.checksum
        }

class PolicyManager:
    """Manages OPA policy bundles and distribution"""
    
    def __init__(self, policy_dir: str = "./policy", bundle_dir: str = "./policy/bundles"):
        self.policy_dir = Path(policy_dir)
        self.bundle_dir = Path(bundle_dir)
        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        self._current_bundle: Optional[PolicyBundle] = None
        self._watchers: List[asyncio.Task] = []
    
    async def load_policies_from_directory(self) -> Dict[str, str]:
        """
        Load all .rego policy files from the policy directory
        
        Returns:
            Dictionary mapping filenames to policy content
        """
        policies = {}
        
        if not self.policy_dir.exists():
            logger.warning(f"Policy directory {self.policy_dir} does not exist")
            return policies
        
        for policy_file in self.policy_dir.glob("*.rego"):
            try:
                async with aiofiles.open(policy_file, 'r') as f:
                    content = await f.read()
                    policies[policy_file.name] = content
                    logger.info(f"Loaded policy: {policy_file.name}")
            except Exception as e:
                logger.error(f"Failed to load policy {policy_file}: {str(e)}")
        
        return policies
    
    async def create_bundle(self, metadata: Optional[Dict[str, Any]] = None) -> PolicyBundle:
        """
        Create a new policy bundle from current policies
        
        Args:
            metadata: Optional metadata to include in bundle
            
        Returns:
            Created PolicyBundle
        """
        policies = await self.load_policies_from_directory()
        
        if not policies:
            raise ValueError("No policies found to create bundle")
        
        bundle = PolicyBundle.create(policies, metadata)
        
        # Save bundle to disk
        bundle_file = self.bundle_dir / f"bundle-{bundle.version}.json"
        async with aiofiles.open(bundle_file, 'w') as f:
            await f.write(json.dumps(bundle.to_dict(), indent=2))
        
        self._current_bundle = bundle
        logger.info(f"Created policy bundle {bundle.version} with {len(policies)} policies")
        
        return bundle
    
    async def load_bundle(self, version: str) -> Optional[PolicyBundle]:
        """
        Load a specific policy bundle version
        
        Args:
            version: Bundle version to load
            
        Returns:
            PolicyBundle if found, None otherwise
        """
        bundle_file = self.bundle_dir / f"bundle-{version}.json"
        
        if not bundle_file.exists():
            logger.error(f"Bundle {version} not found")
            return None
        
        try:
            async with aiofiles.open(bundle_file, 'r') as f:
                data = json.loads(await f.read())
                
                bundle = PolicyBundle(
                    version=data['version'],
                    policies=data['policies'],
                    metadata=data['metadata'],
                    created_at=datetime.fromisoformat(data['created_at']),
                    checksum=data['checksum']
                )
                
                logger.info(f"Loaded policy bundle {version}")
                return bundle
        except Exception as e:
            logger.error(f"Failed to load bundle {version}: {str(e)}")
            return None
    
    async def list_bundles(self) -> List[str]:
        """
        List all available policy bundle versions
        
        Returns:
            List of bundle version strings
        """
        versions = []
        
        for bundle_file in self.bundle_dir.glob("bundle-*.json"):
            version = bundle_file.stem.replace("bundle-", "")
            versions.append(version)
        
        return sorted(versions, reverse=True)  # Most recent first
    
    async def get_current_bundle(self) -> Optional[PolicyBundle]:
        """
        Get the current active policy bundle
        
        Returns:
            Current PolicyBundle or None
        """
        if self._current_bundle:
            return self._current_bundle
        
        # Load the most recent bundle
        versions = await self.list_bundles()
        if versions:
            return await self.load_bundle(versions[0])
        
        return None
    
    async def distribute_bundle(self, bundle: PolicyBundle, opa_endpoints: List[str]) -> Dict[str, bool]:
        """
        Distribute policy bundle to OPA endpoints
        
        Args:
            bundle: PolicyBundle to distribute
            opa_endpoints: List of OPA endpoint URLs
            
        Returns:
            Dictionary mapping endpoints to success status
        """
        results = {}
        
        # Create bundle data for OPA
        bundle_data = {
            "bundles": {
                "authz": {
                    "resource": f"/bundles/authz-{bundle.version}.tar.gz"
                }
            }
        }
        
        # Distribute to each endpoint
        for endpoint in opa_endpoints:
            try:
                success = await self._upload_bundle_to_opa(endpoint, bundle)
                results[endpoint] = success
                logger.info(f"Bundle distribution to {endpoint}: {'success' if success else 'failed'}")
            except Exception as e:
                logger.error(f"Failed to distribute bundle to {endpoint}: {str(e)}")
                results[endpoint] = False
        
        return results
    
    async def _upload_bundle_to_opa(self, opa_url: str, bundle: PolicyBundle) -> bool:
        """
        Upload policy bundle to a specific OPA instance
        
        Args:
            opa_url: OPA endpoint URL
            bundle: PolicyBundle to upload
            
        Returns:
            True if upload successful
        """
        import aiohttp
        
        # Upload each policy individually
        async with aiohttp.ClientSession() as session:
            for filename, content in bundle.policies.items():
                policy_name = filename.replace('.rego', '')
                url = f"{opa_url.rstrip('/')}/v1/policies/{policy_name}"
                
                try:
                    async with session.put(url, data=content, headers={'Content-Type': 'text/plain'}) as response:
                        if response.status not in [200, 201]:
                            logger.error(f"Failed to upload policy {policy_name} to {opa_url}: {response.status}")
                            return False
                except Exception as e:
                    logger.error(f"Error uploading policy {policy_name} to {opa_url}: {str(e)}")
                    return False
        
        return True
    
    async def watch_policy_changes(self, callback: callable) -> None:
        """
        Watch for policy file changes and trigger callback
        
        Args:
            callback: Function to call when policies change
        """
        try:
            import watchdog.observers
            import watchdog.events
            
            class PolicyChangeHandler(watchdog.events.FileSystemEventHandler):
                def __init__(self, callback_func):
                    self.callback = callback_func
                
                def on_modified(self, event):
                    if event.is_directory:
                        return
                    
                    if event.src_path.endswith('.rego'):
                        logger.info(f"Policy file changed: {event.src_path}")
                        asyncio.create_task(self.callback())
            
            observer = watchdog.observers.Observer()
            handler = PolicyChangeHandler(callback)
            observer.schedule(handler, str(self.policy_dir), recursive=False)
            observer.start()
            
            logger.info(f"Started watching policy directory: {self.policy_dir}")
            
            # Keep the watcher running
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                observer.stop()
                observer.join()
                
        except ImportError:
            logger.warning("watchdog not available, policy watching disabled")
        except Exception as e:
            logger.error(f"Error setting up policy watcher: {str(e)}")
    
    async def validate_policies(self, policies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Validate policy syntax and structure
        
        Args:
            policies: Optional policies to validate, defaults to current policies
            
        Returns:
            Validation results with errors and warnings
        """
        if policies is None:
            policies = await self.load_policies_from_directory()
        
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "policies_checked": len(policies)
        }
        
        for filename, content in policies.items():
            try:
                # Basic syntax validation
                if not content.strip():
                    results["errors"].append(f"{filename}: Empty policy file")
                    results["valid"] = False
                    continue
                
                if not content.startswith("package "):
                    results["errors"].append(f"{filename}: Missing package declaration")
                    results["valid"] = False
                
                # Check for common patterns
                if "default allow := false" not in content and "default deny := true" not in content:
                    results["warnings"].append(f"{filename}: No explicit default policy found")
                
                # Check for import statement
                if "import rego.v1" not in content:
                    results["warnings"].append(f"{filename}: Missing rego.v1 import")
                
            except Exception as e:
                results["errors"].append(f"{filename}: Validation error - {str(e)}")
                results["valid"] = False
        
        return results
    
    async def get_policy_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about current policies
        
        Returns:
            Dictionary with policy statistics
        """
        policies = await self.load_policies_from_directory()
        bundles = await self.list_bundles()
        current_bundle = await self.get_current_bundle()
        
        stats = {
            "total_policies": len(policies),
            "policy_files": list(policies.keys()),
            "total_bundles": len(bundles),
            "current_bundle_version": current_bundle.version if current_bundle else None,
            "policy_directory": str(self.policy_dir),
            "bundle_directory": str(self.bundle_dir)
        }
        
        # Calculate total lines of policy code
        total_lines = sum(len(content.splitlines()) for content in policies.values())
        stats["total_policy_lines"] = total_lines
        
        return stats

# Global policy manager instance
policy_manager = PolicyManager()

async def get_policy_manager() -> PolicyManager:
    """Get policy manager instance"""
    return policy_manager