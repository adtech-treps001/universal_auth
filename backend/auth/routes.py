
from fastapi import APIRouter
from .schemas import WorkflowResponse, TokenResponse

router = APIRouter()

@router.get("/workflow", response_model=WorkflowResponse)
def get_workflow():
    return {"workflow": "2_EMAIL_SOCIAL_GOOGLE"}

@router.post("/login", response_model=TokenResponse)
def login():
    return {"access_token": "jwt-token", "role": "user"}
