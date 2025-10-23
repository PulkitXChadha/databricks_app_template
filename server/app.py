"""FastAPI application for Databricks App Template."""

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.lib.distributed_tracing import set_correlation_id
from server.lib.metrics import record_auth_overhead, record_auth_request, record_request_duration
from server.lib.metrics_middleware import metrics_collection_middleware
from server.lib.structured_logger import log_request
from server.routers import metrics as metrics_router
from server.routers import router


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
  allow_origins=[
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
  ],
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)


@app.middleware('http')
async def add_correlation_id(request: Request, call_next):
  """Inject correlation ID and authentication context into request.

  - Extracts X-Correlation-ID header or generates new UUID
  - Sets correlation ID in context for logging
  - Adds X-Correlation-ID to response headers
  - Extracts user access token for OBO authentication
  - Sets authentication mode and state
  - Logs request with performance metrics
  """
  # Extract correlation ID from X-Correlation-ID header or generate new UUID
  correlation_id = request.headers.get('X-Correlation-ID', str(uuid4()))
  set_correlation_id(correlation_id)

  # Store correlation ID in request state for access in endpoints
  request.state.correlation_id = correlation_id

  # Extract user access token from Databricks Apps header
  # This enables On-Behalf-Of (OBO) authentication
  # Try multiple header variations for robustness
  user_token = request.headers.get('X-Forwarded-Access-Token') or request.headers.get(
    'x-forwarded-access-token'
  )

  # DEBUG: Log all request headers for diagnosis (only for /api/ paths)
  if request.url.path.startswith('/api/') and not request.url.path.startswith('/api/health'):
    from server.lib.structured_logger import StructuredLogger

    debug_logger = StructuredLogger(__name__)
    header_keys = list(request.headers.keys())
    has_token = user_token is not None
    debug_logger.info(
      'Token extraction debug',
      path=request.url.path,
      has_token=has_token,
      header_count=len(header_keys),
      header_keys=header_keys[:10] if len(header_keys) > 10 else header_keys,
    )

  # Set authentication context in request state
  request.state.user_token = user_token

  # Set auth mode based on token presence
  # OBO: user token is present, service_principal: no user token
  if user_token:
    request.state.auth_mode = 'obo'
    request.state.has_user_token = True
  else:
    request.state.auth_mode = 'service_principal'
    request.state.has_user_token = False

  # Track request start time
  start_time = time.time()
  auth_start_time = time.time()

  # Authentication overhead is minimal at middleware level (just token extraction)
  auth_overhead = time.time() - auth_start_time

  # Process request
  response = await call_next(request)

  # Calculate duration
  duration_seconds = time.time() - start_time
  duration_ms = duration_seconds * 1000

  # Add correlation ID to response headers
  response.headers['X-Correlation-ID'] = correlation_id

  # Record metrics (skip health and metrics endpoints to reduce noise)
  if request.url.path not in ['/health', '/metrics']:
    # Record authentication metrics based on actual auth mode
    auth_status = 'success' if 200 <= response.status_code < 400 else 'failure'
    auth_mode = getattr(request.state, 'auth_mode', 'obo')  # Default to OBO
    record_auth_request(endpoint=request.url.path, mode=auth_mode, status=auth_status)

    # Record auth overhead based on actual auth mode
    record_auth_overhead(mode=auth_mode, overhead_seconds=auth_overhead)

    # Record overall request duration
    record_request_duration(
      endpoint=request.url.path,
      method=request.method,
      status=response.status_code,
      duration_seconds=duration_seconds,
    )

    # Log request with metrics
    log_request(
      endpoint=request.url.path,
      method=request.method,
      status_code=response.status_code,
      duration_ms=duration_ms,
    )

  return response


@app.get('/health')
async def health_root():
  """Health check endpoint at root level (for load balancers)."""
  return {'status': 'healthy'}


# Add /api/health for consistency with API structure
@app.get('/api/health')
async def health_api():
  """Health check endpoint under /api prefix."""
  return {'status': 'healthy'}


@app.get('/api/metrics')
async def metrics_api(request: Request):
  """Prometheus metrics endpoint under /api prefix.

  Exposes authentication and performance metrics in Prometheus format.
  Requires user authentication for security.

  Raises:
      401: Authentication required (missing or invalid token)
  """
  from fastapi.responses import Response
  from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

  from server.lib.auth import get_user_token

  # Require authentication for metrics endpoint
  await get_user_token(request)

  return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get('/metrics')
async def metrics_root(request: Request):
  """Prometheus metrics endpoint at root level (for monitoring systems).

  Exposes authentication and performance metrics in Prometheus format.
  Requires user authentication for security.

  Raises:
      401: Authentication required (missing or invalid token)
  """
  from fastapi.responses import Response
  from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

  from server.lib.auth import get_user_token

  # Require authentication for metrics endpoint
  await get_user_token(request)

  return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ============================================================================
# CUSTOM EXCEPTION HANDLERS (FR-013)
# ============================================================================


@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
  """Custom exception handler for batch size validation (FR-013).

  Intercepts Pydantic ValidationError and converts batch size errors
  to 413 Payload Too Large with structured error body.
  """
  # Get error details
  error_dict = exc.errors()

  # Look for batch size validation error
  for error in error_dict:
    error_msg = error.get('msg', '')
    if 'Batch size exceeds maximum' in error_msg:
      # Extract received count from error message
      import re

      match = re.search(r'received: (\d+)', error_msg)
      received_count = int(match.group(1)) if match else None

      return JSONResponse(
        status_code=413,
        content={
          'detail': 'Batch size exceeds maximum of 1000 events',
          'max_batch_size': 1000,
          'received': received_count,
        },
      )

  # Not a batch size error - use default validation error response (422)
  return JSONResponse(status_code=422, content={'detail': exc.errors()})


# Include API routers
app.include_router(router, prefix='/api', tags=['api'])
app.include_router(metrics_router.router)  # Metrics router (has its own /api/v1/metrics prefix)

# Add metrics collection middleware
app.middleware('http')(metrics_collection_middleware)


# ============================================================================
# SERVE STATIC FILES FROM CLIENT BUILD DIRECTORY (MUST BE LAST!)
# ============================================================================
# This static file mount MUST be the last route registered!
# It catches all unmatched requests and serves the React app.
# Any routes added after this will be unreachable!
if os.path.exists('client/build'):
  app.mount('/', StaticFiles(directory='client/build', html=True), name='static')
