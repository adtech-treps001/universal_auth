"""
OPA Service

This module provides integration with Open Policy Agent (OPA) for
centralized policy evaluation and authorization decisions.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
import logging
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class PolicyResult(Enum):
    """Policy evaluation results"""
    ALLOW = "allow"
    DENY = "deny"
    ERROR = "error"

@dataclass
class PolicyInput:
    """Input data for policy evaluation"""
    user: Dict[str, Any]
    action: Optional[str] = None
    resource: Optional[str] = None
    tenant_id: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    ui_component: Optional[str] = None
    required_capability: Optional[str] = None
    rate_limit: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for OPA input"""
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class PolicyDecision:
    """Policy evaluation decision"""
    allow: bool
    reason: Optional[str] = None
    policy_version: Optional[str] = None
    evaluated_at: Optional[datetime] = None
    
    @classmethod
    def from_opa_response(cls, response: Dict[str, Any]) -> 'PolicyDecision':
        """Create PolicyDecision from OPA response"""
        return cls(
            allow=response.get('result', False),
            reason=response.get('reason'),
            policy_version=response.get('policy_version'),
            evaluated_at=datetime.utcnow()
        )

class OPAService:
    """Service for OPA policy evaluation"""
    
    def __init__(self, opa_url: str = "http://localhost:8181", timeout: int = 5):
        self.opa_url = opa_url.rstrip('/')
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self._policy_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_update = datetime.utcnow()
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is available"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
    
    async def evaluate_policy(self, package: str, policy_input: PolicyInput) -> PolicyDecision:
        """
        Evaluate a policy against input data
        
        Args:
            package: OPA package name (e.g., 'authz', 'tenant', 'api')
            policy_input: Input data for policy evaluation
            
        Returns:
            PolicyDecision with evaluation result
        """
        await self._ensure_session()
        
        url = f"{self.opa_url}/v1/data/{package}"
        input_data = {"input": policy_input.to_dict()}
        
        try:
            async with self.session.post(url, json=input_data) as response:
                if response.status == 200:
                    result = await response.json()
                    return PolicyDecision.from_opa_response(result)
                else:
                    logger.error(f"OPA evaluation failed: {response.status}")
                    return PolicyDecision(
                        allow=False,
                        reason=f"OPA evaluation failed with status {response.status}"
                    )
        except asyncio.TimeoutError:
            logger.error("OPA evaluation timeout")
            return PolicyDecision(allow=False, reason="Policy evaluation timeout")
        except Exception as e:
            logger.error(f"OPA evaluation error: {str(e)}")
            return PolicyDecision(allow=False, reason=f"Policy evaluation error: {str(e)}")
    
    async def check_authorization(self, policy_input: PolicyInput) -> PolicyDecision:
        """
        Check authorization using the authz package
        
        Args:
            policy_input: Input data for authorization check
            
        Returns:
            PolicyDecision with authorization result
        """
        return await self.evaluate_policy("authz", policy_input)
    
    async def check_tenant_access(self, user: Dict[str, Any], tenant_id: str) -> PolicyDecision:
        """
        Check tenant access authorization
        
        Args:
            user: User data with capabilities and tenant memberships
            tenant_id: Tenant ID to check access for
            
        Returns:
            PolicyDecision with tenant access result
        """
        policy_input = PolicyInput(
            user=user,
            tenant_id=tenant_id
        )
        return await self.evaluate_policy("tenant", policy_input)
    
    async def check_api_access(self, user: Dict[str, Any], method: str, path: str, 
                              rate_limit: Optional[Dict[str, Any]] = None) -> PolicyDecision:
        """
        Check API endpoint access authorization
        
        Args:
            user: User data with capabilities
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            rate_limit: Optional rate limiting data
            
        Returns:
            PolicyDecision with API access result
        """
        policy_input = PolicyInput(
            user=user,
            method=method,
            path=path,
            rate_limit=rate_limit
        )
        return await self.evaluate_policy("api", policy_input)
    
    async def check_ui_visibility(self, user: Dict[str, Any], ui_component: str) -> PolicyDecision:
        """
        Check UI component visibility authorization
        
        Args:
            user: User data with capabilities
            ui_component: UI component identifier
            
        Returns:
            PolicyDecision with UI visibility result
        """
        policy_input = PolicyInput(
            user=user,
            ui_component=ui_component
        )
        return await self.evaluate_policy("authz", policy_input)
    
    async def check_resource_access(self, user: Dict[str, Any], resource: str, 
                                   action: str, tenant_id: Optional[str] = None) -> PolicyDecision:
        """
        Check resource access authorization
        
        Args:
            user: User data with capabilities
            resource: Resource identifier
            action: Action to perform on resource
            tenant_id: Optional tenant context
            
        Returns:
            PolicyDecision with resource access result
        """
        policy_input = PolicyInput(
            user=user,
            resource=resource,
            action=action,
            tenant_id=tenant_id,
            required_capability=f"{resource}:{action}"
        )
        return await self.evaluate_policy("authz", policy_input)
    
    async def reload_policies(self) -> bool:
        """
        Reload OPA policies
        
        Returns:
            True if policies were reloaded successfully
        """
        await self._ensure_session()
        
        url = f"{self.opa_url}/v1/policies"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    policies = await response.json()
                    self._policy_cache = policies
                    self._last_cache_update = datetime.utcnow()
                    logger.info("OPA policies reloaded successfully")
                    return True
                else:
                    logger.error(f"Failed to reload policies: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error reloading policies: {str(e)}")
            return False
    
    async def get_policy_version(self) -> Optional[str]:
        """
        Get current policy version
        
        Returns:
            Policy version string or None if unavailable
        """
        await self._ensure_session()
        
        url = f"{self.opa_url}/v1/data/system/version"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('result', {}).get('version')
                else:
                    logger.error(f"Failed to get policy version: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting policy version: {str(e)}")
            return None
    
    async def health_check(self) -> bool:
        """
        Check OPA service health
        
        Returns:
            True if OPA service is healthy
        """
        await self._ensure_session()
        
        url = f"{self.opa_url}/health"
        
        try:
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"OPA health check failed: {str(e)}")
            return False
    
    async def batch_evaluate(self, evaluations: List[Dict[str, Any]]) -> List[PolicyDecision]:
        """
        Evaluate multiple policies in batch
        
        Args:
            evaluations: List of evaluation requests with 'package' and 'input' keys
            
        Returns:
            List of PolicyDecision results
        """
        await self._ensure_session()
        
        results = []
        
        # Process evaluations concurrently
        tasks = []
        for eval_request in evaluations:
            package = eval_request['package']
            policy_input = PolicyInput(**eval_request['input'])
            task = self.evaluate_policy(package, policy_input)
            tasks.append(task)
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert exceptions to deny decisions
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    processed_results.append(
                        PolicyDecision(allow=False, reason=f"Evaluation error: {str(result)}")
                    )
                else:
                    processed_results.append(result)
            
            return processed_results
        except Exception as e:
            logger.error(f"Batch evaluation error: {str(e)}")
            # Return deny decisions for all evaluations
            return [
                PolicyDecision(allow=False, reason="Batch evaluation failed")
                for _ in evaluations
            ]

# Global OPA service instance
opa_service = OPAService()

async def get_opa_service() -> OPAService:
    """Get OPA service instance"""
    return opa_service