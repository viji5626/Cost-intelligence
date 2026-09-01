"""
API v1 Router Aggregator
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    auth,
    discovery,
    governance,
    health,
    hierarchy,
    ideathon,
    ingestion,
    openai_compat,
    opex,
    opportunity,
    retrieval,
    system,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(system.router)
api_router.include_router(hierarchy.router)
api_router.include_router(ingestion.router)
api_router.include_router(opex.router)
api_router.include_router(ideathon.router)
api_router.include_router(retrieval.router)
api_router.include_router(discovery.router)
api_router.include_router(opportunity.router)
api_router.include_router(governance.router)
api_router.include_router(openai_compat.router, prefix="/openai")
