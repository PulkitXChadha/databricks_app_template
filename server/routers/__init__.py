# Generic router module for the Databricks app template
# Add your FastAPI routes here

from fastapi import APIRouter

from .user import router as user_router
from .unity_catalog import router as unity_catalog_router
from .lakebase import router as lakebase_router
from .model_serving import router as model_serving_router

router = APIRouter()
router.include_router(user_router, prefix='/user', tags=['user'])
router.include_router(unity_catalog_router, prefix='/unity-catalog', tags=['unity-catalog'])
router.include_router(lakebase_router, tags=['lakebase'])  # No prefix - tests expect /api/preferences directly
router.include_router(model_serving_router, prefix='/model-serving', tags=['model-serving'])
