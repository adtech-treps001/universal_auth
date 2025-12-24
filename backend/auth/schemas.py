
from pydantic import BaseModel

class WorkflowResponse(BaseModel):
    workflow: str

class TokenResponse(BaseModel):
    access_token: str
    role: str
