
from fastapi import FastAPI
from auth.routes import router as auth_router

app = FastAPI(title="Unified Auth API")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "universal-auth-backend"}

app.include_router(auth_router, prefix="/auth")
