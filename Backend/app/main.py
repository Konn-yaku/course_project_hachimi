# app/main.py
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

from app.api.v1 import files as files_router
from app.api.v1 import media as media_router
from app.api.v1 import auth as auth_router

app = FastAPI(title="Home Cloud API")

# --- 2. 配置 CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. 自动创建媒体目录 ---
os.makedirs(settings.MEDIA_ROOT_PATH, exist_ok=True)
print(f"媒体文件将存储在: {settings.MEDIA_ROOT_PATH.resolve()}")

# --- 4. 挂载静态文件目录 ---
app.mount(
    "/static_media",
    StaticFiles(directory=settings.MEDIA_ROOT_PATH),
    name="static_media"
)

# --- 5. 你的路由 ---
@app.get("/")
async def root():
    return {"message": "欢迎来到 Home Cloud API!"}

@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

# (我们将在这里添加新的API路由)
app.include_router(
    files_router.router,
    prefix="/api/v1/files", # 所有这个路由下的端点都会自动加上 /api/v1/files 前缀
    tags=["Files"]          # 在 /docs 页面中进行分组
)

app.include_router(
    media_router.router,  # <-- 2. 包含新路由
    prefix="/api/v1/media",
    tags=["Media Library"] # <-- 在 /docs 中显示为 "Media Library"
)

app.include_router(
    auth_router.router,
    prefix="/api/v1/auth",
    tags=["Auth"]
)