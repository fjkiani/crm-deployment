"""
Analytics API — Phase 10 Observability
===========================================
Provides endpoints for pipeline health, conversion funnels, and A/B metrics.
"""

import logging
from fastapi import APIRouter
from eaia.mcp_client import FrappeMCPClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/health")
async def get_pipeline_health():
    """
    Get pipeline health, coverage, and funnel metrics.
    Calls the Frappe CRM MCP tool `get_pipeline_analytics`.
    """
    client = FrappeMCPClient()
    try:
        data = await client.get_pipeline_analytics()
        if "error" in data:
            return {"status": "error", "error": data["error"]}
        
        return {
            "status": "success",
            "data": data,
        }
    except Exception as e:
        logger.error(f"Analytics endpoint error: {e}")
        return {"status": "error", "error": str(e)}
