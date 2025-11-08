from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from session.routes import router as session_router
from admin.routes import router as admin_router

settings = get_settings()

app = FastAPI(title="MeetingPolice API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router, prefix="/api/session", tags=["session"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
