from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, chat, health, materials, tasks, vendors
from app.services import auth_service, chat_service, material_service, vendor_service

app = FastAPI(
    title="ReWritter-Agent API",
    version="0.1.0",
    description="自动化内容创作与发布系统后端服务",
)


@app.on_event("startup")
async def setup_storage() -> None:
    auth_service.ensure_storage()
    vendor_service.ensure_storage()
    chat_service.ensure_storage()
    material_service.ensure_storage()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(vendors.router)
app.include_router(chat.router)
app.include_router(materials.router)
