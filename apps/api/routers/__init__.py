"""FastAPI routers."""

from apps.api.routers.auth import router as auth_router
from apps.api.routers.calls import router as calls_router
from apps.api.routers.knowledge import router as knowledge_router
from apps.api.routers.metrics import router as metrics_router
from apps.api.routers.traces import router as traces_router

__all__ = [
    "auth_router",
    "calls_router",
    "knowledge_router",
    "metrics_router",
    "traces_router",
]
