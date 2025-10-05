"""FastAPI application for Databricks App Template."""

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.routers import router
from server.lib.distributed_tracing import set_correlation_id, get_correlation_id
from server.lib.structured_logger import log_request


# Load environment variables from .env.local if it exists
def load_env_file(filepath: str) -> None:
  """Load environment variables from a file."""
  if Path(filepath).exists():
    with open(filepath) as f:
      for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
          key, _, value = line.partition('=')
          if key and value:
            os.environ[key] = value


# Load .env files
load_env_file('.env')
load_env_file('.env.local')


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Manage application lifespan."""
  yield


app = FastAPI(
  title='Databricks App API',
  description='Modern FastAPI application template for Databricks Apps with React frontend',
  version='0.1.0',
  lifespan=lifespan,
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
  """Inject correlation ID into request context and response headers.
  
  - Extracts X-Request-ID header or generates new UUID
  - Sets correlation ID in context for logging
  - Adds X-Request-ID to response headers
  - Logs request with performance metrics
  """
  # Extract from header or generate new UUID
  request_id = request.headers.get('X-Request-ID', str(uuid4()))
  set_correlation_id(request_id)
  
  # Track request start time
  start_time = time.time()
  
  # Process request
  response = await call_next(request)
  
  # Calculate duration
  duration_ms = (time.time() - start_time) * 1000
  
  # Add correlation ID to response headers
  response.headers['X-Request-ID'] = request_id
  
  # Log request with metrics (skip health check to reduce noise)
  if request.url.path != '/health':
    log_request(
      endpoint=request.url.path,
      method=request.method,
      status_code=response.status_code,
      duration_ms=duration_ms
    )
  
  return response


app.include_router(router, prefix='/api', tags=['api'])


@app.get('/health')
async def health():
  """Health check endpoint."""
  return {'status': 'healthy'}


# ============================================================================
# SERVE STATIC FILES FROM CLIENT BUILD DIRECTORY (MUST BE LAST!)
# ============================================================================
# This static file mount MUST be the last route registered!
# It catches all unmatched requests and serves the React app.
# Any routes added after this will be unreachable!
if os.path.exists('client/build'):
  app.mount('/', StaticFiles(directory='client/build', html=True), name='static')
