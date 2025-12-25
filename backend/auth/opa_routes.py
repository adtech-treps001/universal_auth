"""
OPA Policy Evaluation Routes

This module provides API endpoints for OPA policy evaluation,
policy management, and scope version tracking.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.opa_service import OPAService, PolicyInput, PolicyDecision, get_opa_service
from services.policy_manager import PolicyManager, get_policy_manager
from auth.middleware import get_current_user, require_capability
from auth.opa_middleware import get_opa_middleware, OPAMiddleware
from database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/opa", tags=["OPA Policy Evaluation"])

# Request/Response models
class PolicyEvaluationRequest(BaseModel):
    """Request model for policy evaluation"""
    package: str
    input_data: Dict[str, Any]

class PolicyEvaluationResponse(BaseModel):
    """Response model for policy evaluation"""
    allow: bool
    reason: Optional[str] = None
    policy_version: Optional[str] = None
    evaluated_at: str

class BatchEvaluationRequest(BaseModel):
    """Request model for batch policy evaluation"""
    evaluations: List[Dict[str, Any]]

class BatchEvaluationResponse(BaseModel):
    """Response model for batch policy evaluation"""
    results: List[PolicyEvaluationResponse]

class UIVisibilityRequest(BaseModel):
    """Request model for UI visibility check"""
    ui_component: str

class ResourceAccessRequest(BaseModel):
    """Request model for resource access check"""
    resource: str
    action: str
    tenant_id: Optional[str] = None

class TenantAccessRequest(BaseModel):
    """Request model for tenant access check"""
    tenant_id: str

class PolicyBundleResponse(BaseModel):
    """Response model for policy bundle information"""
    version: str
    policies: Dict[str, str]
    metadata: Dict[str, Any]
    created_at: str
    checksum: str

class PolicyStatsResponse(BaseModel):
    """Response model for policy statistics"""
    total_policies: int
    policy_files: List[str]
    total_bundles: int
    current_bundle_version: Optional[str]
    policy_directory: str
    bundle_directory: str
    total_policy_lines: int

# Policy evaluation endpoints
@router.post("/evaluate", response_model=PolicyEvaluationResponse)
async def evaluate_policy(
    request: PolicyEvaluationRequest,
    current_user: dict = Depends(require_capability("opa:evaluate")),
    opa_service: OPAService = Depends(get_opa_service)
):
    """
    Evaluate a specific policy with input data
    
    Requires: opa:evaluate capability
    """
    try:
        policy_input = PolicyInput(**request.input_data)
        decision = await opa_service.evaluate_policy(request.package, policy_input)
        
        return PolicyEvaluationResponse(
            allow=decision.allow,
            reason=decision.reason,
            policy_version=decision.policy_version,
            evaluated_at=decision.evaluated_at.isoformat() if decision.evaluated_at else ""
        )
    except Exception as e:
        logger.error(f"Policy evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Policy evaluation failed: {str(e)}")

@router.post("/evaluate/batch", response_model=BatchEvaluationResponse)
async def evaluate_policies_batch(
    request: BatchEvaluationRequest,
    current_user: dict = Depends(require_capability("opa:evaluate")),
    opa_service: OPAService = Depends(get_opa_service)
):
    """
    Evaluate multiple policies in batch
    
    Requires: opa:evaluate capability
    """
    try:
        decisions = await opa_service.batch_evaluate(request.evaluations)
        
        results = []
        for decision in decisions:
            results.append(PolicyEvaluationResponse(
                allow=decision.allow,
                reason=decision.reason,
                policy_version=decision.policy_version,
                evaluated_at=decision.evaluated_at.isoformat() if decision.evaluated_at else ""
            ))
        
        return BatchEvaluationResponse(results=results)
    except Exception as e:
        logger.error(f"Batch policy evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch evaluation failed: {str(e)}")

@router.post("/check/authorization", response_model=PolicyEvaluationResponse)
async def check_authorization(
    http_request: Request,
    current_user: dict = Depends(get_current_user),
    opa_middleware: OPAMiddleware = Depends(get_opa_middleware)
):
    """
    Check authorization for current user and request
    
    No additional capability required - uses current user context
    """
    try:
        decision = await opa_middleware.evaluate_authorization(current_user, http_request)
        
        return PolicyEvaluationResponse(
            allow=decision.allow,
            reason=decision.reason,
            policy_version=decision.policy_version,
            evaluated_at=decision.evaluated_at.isoformat() if decision.evaluated_at else ""
        )
    except Exception as e:
        logger.error(f"Authorization check error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authorization check failed: {str(e)}")

@router.post("/check/ui-visibility", response_model=PolicyEvaluationResponse)
async def check_ui_visibility(
    request: UIVisibilityRequest,
    current_user: dict = Depends(get_current_user),
    opa_middleware: OPAMiddleware = Depends(get_opa_middleware)
):
    """
    Check UI component visibility for current user
    
    No additional capability required - uses current user context
    """
    try:
        decision = await opa_middleware.evaluate_ui_visibility(
            current_user, request.ui_component
        )
        
        return PolicyEvaluationResponse(
            allow=decision.allow,
            reason=decision.reason,
            policy_version=decision.policy_version,
            evaluated_at=decision.evaluated_at.isoformat() if decision.evaluated_at else ""
        )
    except Exception as e:
        logger.error(f"UI visibility check error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"UI visibility check failed: {str(e)}")

@router.post("/check/resource-access", response_model=PolicyEvaluationResponse)
async def check_resource_access(
    request: ResourceAccessRequest,
    current_user: dict = Depends(get_current_user),
    opa_middleware: OPAMiddleware = Depends(get_opa_middleware)
):
    """
    Check resource access for current user
    
    No additional capability required - uses current user context
    """
    try:
        decision = await opa_middleware.evaluate_resource_access(
            current_user, request.resource, request.action, request.tenant_id
        )
        
        return PolicyEvaluationResponse(
            allow=decision.allow,
            reason=decision.reason,
            policy_version=decision.policy_version,
            evaluated_at=decision.evaluated_at.isoformat() if decision.evaluated_at else ""
        )
    except Exception as e:
        logger.error(f"Resource access check error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Resource access check failed: {str(e)}")

@router.post("/check/tenant-access", response_model=PolicyEvaluationResponse)
async def check_tenant_access(
    request: TenantAccessRequest,
    current_user: dict = Depends(get_current_user),
    opa_middleware: OPAMiddleware = Depends(get_opa_middleware)
):
    """
    Check tenant access for current user
    
    No additional capability required - uses current user context
    """
    try:
        decision = await opa_middleware.evaluate_tenant_access(
            current_user, request.tenant_id
        )
        
        return PolicyEvaluationResponse(
            allow=decision.allow,
            reason=decision.reason,
            policy_version=decision.policy_version,
            evaluated_at=decision.evaluated_at.isoformat() if decision.evaluated_at else ""
        )
    except Exception as e:
        logger.error(f"Tenant access check error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Tenant access check failed: {str(e)}")

# Policy management endpoints
@router.get("/policies/current", response_model=PolicyBundleResponse)
async def get_current_policy_bundle(
    current_user: dict = Depends(require_capability("opa:manage_policies")),
    policy_manager: PolicyManager = Depends(get_policy_manager)
):
    """
    Get current active policy bundle
    
    Requires: opa:manage_policies capability
    """
    try:
        bundle = await policy_manager.get_current_bundle()
        if not bundle:
            raise HTTPException(status_code=404, detail="No policy bundle found")
        
        return PolicyBundleResponse(
            version=bundle.version,
            policies=bundle.policies,
            metadata=bundle.metadata,
            created_at=bundle.created_at.isoformat(),
            checksum=bundle.checksum
        )
    except Exception as e:
        logger.error(f"Error getting current policy bundle: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get policy bundle: {str(e)}")

@router.get("/policies/versions")
async def list_policy_versions(
    current_user: dict = Depends(require_capability("opa:manage_policies")),
    policy_manager: PolicyManager = Depends(get_policy_manager)
):
    """
    List all available policy bundle versions
    
    Requires: opa:manage_policies capability
    """
    try:
        versions = await policy_manager.list_bundles()
        return {"versions": versions}
    except Exception as e:
        logger.error(f"Error listing policy versions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list versions: {str(e)}")

@router.post("/policies/create")
async def create_policy_bundle(
    metadata: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(require_capability("opa:manage_policies")),
    policy_manager: PolicyManager = Depends(get_policy_manager)
):
    """
    Create new policy bundle from current policies
    
    Requires: opa:manage_policies capability
    """
    try:
        bundle = await policy_manager.create_bundle(metadata)
        
        return {
            "version": bundle.version,
            "checksum": bundle.checksum,
            "created_at": bundle.created_at.isoformat(),
            "policies_count": len(bundle.policies)
        }
    except Exception as e:
        logger.error(f"Error creating policy bundle: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create bundle: {str(e)}")

@router.post("/policies/reload")
async def reload_policies(
    current_user: dict = Depends(require_capability("opa:manage_policies")),
    opa_service: OPAService = Depends(get_opa_service)
):
    """
    Reload OPA policies
    
    Requires: opa:manage_policies capability
    """
    try:
        success = await opa_service.reload_policies()
        if success:
            return {"message": "Policies reloaded successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reload policies")
    except Exception as e:
        logger.error(f"Error reloading policies: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reload policies: {str(e)}")

@router.get("/policies/validate")
async def validate_policies(
    current_user: dict = Depends(require_capability("opa:manage_policies")),
    policy_manager: PolicyManager = Depends(get_policy_manager)
):
    """
    Validate current policy syntax and structure
    
    Requires: opa:manage_policies capability
    """
    try:
        results = await policy_manager.validate_policies()
        return results
    except Exception as e:
        logger.error(f"Error validating policies: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to validate policies: {str(e)}")

@router.get("/policies/stats", response_model=PolicyStatsResponse)
async def get_policy_statistics(
    current_user: dict = Depends(require_capability("opa:manage_policies")),
    policy_manager: PolicyManager = Depends(get_policy_manager)
):
    """
    Get policy statistics and information
    
    Requires: opa:manage_policies capability
    """
    try:
        stats = await policy_manager.get_policy_statistics()
        return PolicyStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting policy statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

# Health and status endpoints
@router.get("/health")
async def opa_health_check(
    opa_service: OPAService = Depends(get_opa_service)
):
    """
    Check OPA service health
    
    No authentication required - public health check
    """
    try:
        healthy = await opa_service.health_check()
        if healthy:
            return {"status": "healthy", "opa_available": True}
        else:
            return {"status": "unhealthy", "opa_available": False}
    except Exception as e:
        logger.error(f"OPA health check error: {str(e)}")
        return {"status": "error", "opa_available": False, "error": str(e)}

@router.get("/version")
async def get_policy_version(
    opa_service: OPAService = Depends(get_opa_service)
):
    """
    Get current policy version
    
    No authentication required - public version info
    """
    try:
        version = await opa_service.get_policy_version()
        return {"policy_version": version}
    except Exception as e:
        logger.error(f"Error getting policy version: {str(e)}")
        return {"policy_version": None, "error": str(e)}