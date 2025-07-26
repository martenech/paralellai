from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.db import init_db
from app.api import conversations, messages, insights

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing database...")
    init_db()
    print("Database initialized!")
    yield
    # Shutdown
    print("Shutting down...")

app = FastAPI(
    title="LLM Memory API",
    description="API for managing LLM conversations with persistent memory",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])

@app.get("/")
def read_root():
    return {"message": "LLM Memory API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)