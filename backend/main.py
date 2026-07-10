"""FastAPI 后端入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.deps import close_services, create_services
from backend.routers import chat, export, models, presets, search, sessions, users
from src.utils.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化服务，关闭时释放存储资源。"""
    setup_logging("logging.yaml")
    app.state.services = await create_services()
    try:
        yield
    finally:
        await close_services(app.state.services)


app = FastAPI(
    title="LangChain Chat API",
    description="LangChain Chat 前后端分离 WebUI 的 FastAPI 后端。",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(presets.router)
app.include_router(models.router)
app.include_router(search.router)
app.include_router(export.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """健康检查接口。"""
    return {"status": "ok"}
