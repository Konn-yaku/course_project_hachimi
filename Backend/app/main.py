import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Import API routers
from app.api.v1 import files as files_router
from app.api.v1 import media as media_router

# Initialize the FastAPI application
app = FastAPI(title="Home Cloud API")

# Configure CORS (Cross-Origin Resource Sharing)
# This allows the frontend (running on a different port/domain) to communicate with this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins for development. Restrict this in production.
    allow_credentials=True,
    allow_methods=["*"],          # Allow all HTTP methods (GET, POST, DELETE, etc.)
    allow_headers=["*"],          # Allow all HTTP headers
)

# Auto-create Media Directory
# Ensure the root directory for storing media files exists on the server.
os.makedirs(settings.MEDIA_ROOT_PATH, exist_ok=True)
print(f"Media files will be stored at: {settings.MEDIA_ROOT_PATH.resolve()}")

# Mount Static File Directory
# This mounts the physical media directory to a virtual URL path.
# It allows the frontend to access images/videos via http://host:port/static_media/...
app.mount(
    "/static_media",
    StaticFiles(directory=settings.MEDIA_ROOT_PATH),
    name="static_media"
)

# Basic Routes

@app.get("/")
async def root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Welcome to Home Cloud API!"}

@app.get("/hello/{name}")
async def say_hello(name: str):
    """
    A simple test endpoint that echoes back the name.
    """
    return {"message": f"Hello {name}"}

# Include API Routers

# Register the File Manager routes
app.include_router(
    files_router.router,
    prefix="/api/v1/files",  # All endpoints in this router will be prefixed with /api/v1/files
    tags=["Files"]           # Grouping label for the /docs Swagger UI
)

# Register the Media Library routes
app.include_router(
    media_router.router,
    prefix="/api/v1/media",
    tags=["Media Library"]   # Grouping label for the /docs Swagger UI
)