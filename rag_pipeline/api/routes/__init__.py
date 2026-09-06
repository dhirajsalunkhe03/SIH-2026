#!/usr/bin/env python3
"""
API routes package initialization.
"""

from api.routes.health import router as health_router
from api.routes.chat import router as chat_router

# All routers to include in the main app
routers = [
    health_router,
    chat_router,
]