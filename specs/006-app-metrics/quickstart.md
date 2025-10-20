# Quickstart Guide: App Metrics System

**Feature**: 006-app-metrics  
**Date**: 2025-10-18  
**Audience**: Developers, Operators, Administrators

## Overview

This guide provides step-by-step instructions for implementing, deploying, and using the application metrics collection and visualization system. The system automatically collects performance and usage metrics, stores them in Lakebase, and provides an admin dashboard for monitoring.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Implementation Workflow (TDD)](#implementation-workflow-tdd)
3. [Database Setup](#database-setup)
4. [Backend Implementation](#backend-implementation)
5. [Frontend Implementation](#frontend-implementation)
6. [Scheduled Jobs](#scheduled-jobs)
7. [Testing](#testing)
8. [Deployment](#deployment)
9. [Usage](#usage)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Development Environment
- Python 3.11+ with `uv` package manager
- Node.js 18.0+ with `bun` package manager
- Access to Databricks workspace
- Databricks personal access token for local development
- Admin privileges for metrics dashboard access (testing)

### Dependencies
```bash
# Python backend dependencies
uv add fastapi sqlalchemy alembic psycopg2-binary pydantic

# Frontend dependencies (in client/ directory)
cd client
bun add recharts @types/recharts
```

### Configuration
Ensure `.env.local` contains:
```bash
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapi...
LAKEBASE_HOST=your-lakebase-host
LAKEBASE_PORT=443
LAKEBASE_DATABASE=your_database
```

---

## Implementation Workflow (TDD)

Following **Principle XII (Test Driven Development)**, implement this feature using strict red-green-refactor cycles:

### Step 1: RED Phase - Write Failing Tests

#### 1.1 Create Contract Tests
```bash
# Create contract test file
touch tests/contract/test_metrics_api.py
```

```python
# tests/contract/test_metrics_api.py
import pytest
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)

def test_get_performance_metrics_endpoint_exists():
    """Test that performance metrics endpoint returns 200 (currently will fail with 404)"""
    response = client.get("/api/v1/metrics/performance")
    assert response.status_code in [200, 401, 403]  # Not 404

def test_get_usage_metrics_endpoint_exists():
    """Test that usage metrics endpoint exists"""
    response = client.get("/api/v1/metrics/usage")
    assert response.status_code in [200, 401, 403]  # Not 404

def test_submit_usage_events_endpoint_exists():
    """Test that usage events submission endpoint exists"""
    response = client.post("/api/v1/metrics/usage-events", json={"events": []})
    assert response.status_code in [202, 400, 401]  # Not 404
```

#### 1.2 Run Tests (Verify RED Phase)
```bash
# Tests should FAIL (endpoints don't exist yet)
pytest tests/contract/test_metrics_api.py -v

# Expected: FAILED (404 Not Found)
```

#### 1.3 Create Integration Tests
```bash
# Create integration test files
touch tests/integration/test_metrics_collection.py
touch tests/integration/test_metrics_aggregation.py
touch tests/integration/test_usage_metrics.py
```

See [Testing](#testing) section for full integration test examples.

### Step 2: GREEN Phase - Implement Minimal Code

Work through implementation in this order to make tests pass:
1. Database models → 2. Database migration → 3. Service layer → 4. API router → 5. Middleware

### Step 3: REFACTOR Phase - Improve Quality

Once tests pass:
- Extract helper functions
- Improve error messages
- Add logging and observability
- Optimize queries with proper indexes

---

## Database Setup

### Step 1: Create SQLAlchemy Models

Create model files in `server/models/`:

#### server/models/performance_metric.py
```python
from sqlalchemy import Column, String, Integer, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from server.lib.database import Base
import uuid
from datetime import datetime

class PerformanceMetric(Base):
    __tablename__ = 'performance_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    endpoint = Column(String(500), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=False)
    user_id = Column(String(255), nullable=True, index=True)
    error_type = Column(String(255), nullable=True)
```

#### server/models/usage_event.py
```python
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from server.lib.database import Base
import uuid
from datetime import datetime

class UsageEvent(Base):
    __tablename__ = 'usage_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    page_name = Column(String(255), nullable=True)
    element_id = Column(String(255), nullable=True)
    success = Column(Boolean, nullable=True)
    metadata = Column(JSON, nullable=True)
```

#### server/models/aggregated_metric.py
```python
from sqlalchemy import Column, String, Integer, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from server.lib.database import Base
import uuid

class AggregatedMetric(Base):
    __tablename__ = 'aggregated_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time_bucket = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False, index=True)
    endpoint_path = Column(String(500), nullable=True, index=True)
    event_type = Column(String(100), nullable=True, index=True)
    aggregated_values = Column(JSON, nullable=False)
    sample_count = Column(Integer, nullable=False)
```

### Step 2: Create Database Migration

```bash
# Generate migration
uv run alembic revision --autogenerate -m "Add metrics tables"

# Review generated migration
cat migrations/versions/xxx_add_metrics_tables.py

# Apply migration
uv run alembic upgrade head

# Verify tables created
# (Use Databricks SQL or psql to verify)
```

### Step 3: Verify Tables
```sql
-- Connect to Lakebase and verify
\dt

-- Expected output:
-- performance_metrics
-- usage_events
-- aggregated_metrics
```

---

## Backend Implementation

### Step 1: Create Admin Service

**Note**: This is a quickstart implementation example. For the complete, production-ready admin check implementation with all edge cases, group name variations, and caching strategy, see [data-model.md Admin Check Pattern section](./data-model.md#admin-check-pattern).

#### server/services/admin_service.py
```python
from databricks.sdk import WorkspaceClient
from fastapi import HTTPException
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# In-memory cache for admin status (5-minute TTL)
admin_cache = {}

async def is_workspace_admin(user_token: str, user_id: str) -> bool:
    """
    Check if user has Databricks workspace admin privileges.
    Caches result for 5 minutes to reduce API calls.
    """
    cache_key = f"admin_check:{user_id}"
    
    # Check cache
    if cache_key in admin_cache:
        cached_result, expiry = admin_cache[cache_key]
        if datetime.utcnow() < expiry:
            logger.info(f"Admin check cache hit for user {user_id}: {cached_result}")
            return cached_result
    
    # Call Databricks API
    try:
        client = WorkspaceClient(token=user_token)
        current_user = client.current_user.me()
        
        # Check if user has workspace admin role
        # See data-model.md Admin Check Pattern section for complete implementation
        ADMIN_GROUP_NAMES = {"admins", "workspace_admins", "administrators"}
        is_admin = any(
            group.get("display", "").lower() in ADMIN_GROUP_NAMES
            for group in current_user.groups
        )
        
        # Cache result for 5 minutes
        admin_cache[cache_key] = (is_admin, datetime.utcnow() + timedelta(minutes=5))
        
        logger.info(f"Admin check for user {user_id}: {is_admin}")
        return is_admin
        
    except Exception as e:
        logger.error(f"Failed to check admin status for user {user_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail={"error": "Service Unavailable", "message": "Unable to verify admin privileges"}
        )
```

### Step 2: Create Admin Dependency

#### server/lib/auth.py (add to existing file)
```python
from fastapi import Depends, HTTPException
from server.services.admin_service import is_workspace_admin

async def get_admin_user(user_token: str = Depends(get_user_token)) -> dict:
    """
    FastAPI dependency that enforces admin-only access.
    Returns user info if admin, raises 403 if not admin.
    """
    from databricks.sdk import WorkspaceClient
    
    try:
        client = WorkspaceClient(token=user_token)
        user = client.current_user.me()
        user_id = user.user_name
        
        # Check admin status
        if not await is_workspace_admin(user_token, user_id):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Access Denied",
                    "message": "Administrator privileges required to access metrics",
                    "status_code": 403
                }
            )
        
        return {"user_id": user_id, "email": user.user_name}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")
```

### Step 3: Create Metrics Service

#### server/services/metrics_service.py
```python
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from server.models.performance_metric import PerformanceMetric
from server.models.usage_event import UsageEvent
from server.models.aggregated_metric import AggregatedMetric
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class MetricsService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_performance_metrics(
        self, 
        time_range: str = "24h",
        endpoint: Optional[str] = None
    ) -> Dict:
        """Retrieve aggregated performance metrics"""
        start_time, end_time = self._parse_time_range(time_range)
        
        # Query raw metrics if within 7 days, otherwise aggregated
        if (datetime.utcnow() - start_time).days <= 7:
            return self._query_raw_performance_metrics(start_time, end_time, endpoint)
        else:
            return self._query_aggregated_performance_metrics(start_time, end_time, endpoint)
    
    def get_usage_metrics(
        self,
        time_range: str = "24h",
        event_type: Optional[str] = None
    ) -> Dict:
        """Retrieve aggregated usage metrics"""
        start_time, end_time = self._parse_time_range(time_range)
        
        if (datetime.utcnow() - start_time).days <= 7:
            return self._query_raw_usage_metrics(start_time, end_time, event_type)
        else:
            return self._query_aggregated_usage_metrics(start_time, end_time, event_type)
    
    def record_performance_metric(self, metric_data: Dict) -> None:
        """Record a single performance metric"""
        metric = PerformanceMetric(**metric_data)
        self.db.add(metric)
        self.db.commit()
        logger.info(f"Recorded performance metric: {metric.endpoint} - {metric.response_time_ms}ms")
    
    def record_usage_events_batch(self, events: List[Dict], user_id: str) -> int:
        """Record batch of usage events"""
        event_objects = [UsageEvent(**{**event, "user_id": user_id}) for event in events]
        self.db.bulk_save_objects(event_objects)
        self.db.commit()
        logger.info(f"Recorded {len(event_objects)} usage events for user {user_id}")
        return len(event_objects)
    
    def _parse_time_range(self, time_range: str) -> tuple:
        """Parse time range string to start/end datetimes"""
        end_time = datetime.utcnow()
        if time_range == "24h":
            start_time = end_time - timedelta(hours=24)
        elif time_range == "7d":
            start_time = end_time - timedelta(days=7)
        elif time_range == "30d":
            start_time = end_time - timedelta(days=30)
        elif time_range == "90d":
            start_time = end_time - timedelta(days=90)
        else:
            start_time = end_time - timedelta(hours=24)
        
        return start_time, end_time
    
    def _query_raw_performance_metrics(self, start_time, end_time, endpoint):
        """Query raw performance metrics table"""
        query = self.db.query(PerformanceMetric).filter(
            and_(
                PerformanceMetric.timestamp >= start_time,
                PerformanceMetric.timestamp <= end_time
            )
        )
        
        if endpoint:
            query = query.filter(PerformanceMetric.endpoint == endpoint)
        
        metrics = query.all()
        
        # Aggregate in Python (for raw data)
        if not metrics:
            return self._empty_performance_response(start_time, end_time)
        
        response_times = [m.response_time_ms for m in metrics]
        total_requests = len(metrics)
        error_count = sum(1 for m in metrics if m.status_code >= 400)
        
        return {
            "time_range": self._format_time_range(start_time, end_time),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "metrics": {
                "avg_response_time_ms": sum(response_times) / len(response_times),
                "total_requests": total_requests,
                "error_rate": error_count / total_requests if total_requests > 0 else 0,
                "p50_response_time_ms": self._percentile(response_times, 0.5),
                "p95_response_time_ms": self._percentile(response_times, 0.95),
                "p99_response_time_ms": self._percentile(response_times, 0.99),
            },
            "endpoints": self._aggregate_by_endpoint(metrics)
        }
    
    def _percentile(self, data: List[float], p: float) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _aggregate_by_endpoint(self, metrics):
        """Aggregate metrics by endpoint"""
        endpoint_groups = {}
        for m in metrics:
            key = (m.endpoint, m.method)
            if key not in endpoint_groups:
                endpoint_groups[key] = []
            endpoint_groups[key].append(m)
        
        return [
            {
                "endpoint": endpoint,
                "method": method,
                "avg_response_time_ms": sum(m.response_time_ms for m in group) / len(group),
                "request_count": len(group),
                "error_count": sum(1 for m in group if m.status_code >= 400)
            }
            for (endpoint, method), group in endpoint_groups.items()
        ]
    
    # Additional methods for aggregated queries, usage metrics, etc.
    # (Implementation similar to above but querying AggregatedMetric table)
```

### Step 4: Create Metrics Middleware

#### server/lib/metrics_middleware.py
```python
from fastapi import Request
import time
import logging
from server.services.metrics_service import MetricsService
from server.lib.database import get_db

logger = logging.getLogger(__name__)

async def metrics_collection_middleware(request: Request, call_next):
    """
    FastAPI middleware that automatically collects performance metrics for all requests.
    Gracefully degrades if metrics collection fails (doesn't impact app functionality).
    """
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    response_time_ms = (time.time() - start_time) * 1000
    
    # Extract request info
    endpoint = request.url.path
    method = request.method
    status_code = response.status_code
    user_id = getattr(request.state, "user_id", None)  # From auth middleware
    error_type = None
    if status_code >= 400:
        error_type = f"HTTP_{status_code}"
    
    # Record metric asynchronously (don't block response)
    try:
        db = next(get_db())
        metrics_service = MetricsService(db)
        metrics_service.record_performance_metric({
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "user_id": user_id,
            "error_type": error_type
        })
    except Exception as e:
        # Fail gracefully - log error but don't impact response
        logger.error(f"Failed to record performance metric: {e}", exc_info=True)
    
    return response
```

### Step 5: Create API Router

#### server/routers/metrics.py
```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from server.lib.auth import get_admin_user, get_user_token
from server.lib.database import get_db
from server.services.metrics_service import MetricsService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/metrics", tags=["Metrics"])

# Pydantic models
class UsageEventInput(BaseModel):
    event_type: str
    page_name: Optional[str] = None
    element_id: Optional[str] = None
    success: Optional[bool] = None
    metadata: Optional[dict] = None
    timestamp: str

class UsageEventBatchRequest(BaseModel):
    events: List[UsageEventInput]

@router.get("/performance")
async def get_performance_metrics(
    admin_user = Depends(get_admin_user),  # Admin-only
    time_range: str = Query("24h", regex="^(24h|7d|30d|90d)$"),
    endpoint: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get performance metrics (admin only)"""
    metrics_service = MetricsService(db)
    return metrics_service.get_performance_metrics(time_range, endpoint)

@router.get("/usage")
async def get_usage_metrics(
    admin_user = Depends(get_admin_user),  # Admin-only
    time_range: str = Query("24h", regex="^(24h|7d|30d|90d)$"),
    event_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get usage metrics (admin only)"""
    metrics_service = MetricsService(db)
    return metrics_service.get_usage_metrics(time_range, event_type)

@router.post("/usage-events", status_code=202)
async def submit_usage_events(
    request: UsageEventBatchRequest,
    user_token: str = Depends(get_user_token),  # Authenticated, not admin-only
    db: Session = Depends(get_db)
):
    """Submit batch usage events (any authenticated user)"""
    from databricks.sdk import WorkspaceClient
    client = WorkspaceClient(token=user_token)
    user = client.current_user.me()
    user_id = user.user_name
    
    metrics_service = MetricsService(db)
    events_count = metrics_service.record_usage_events_batch(
        [event.dict() for event in request.events],
        user_id
    )
    
    return {
        "message": "Events accepted",
        "events_received": events_count,
        "status": "processing"
    }
```

### Step 6: Register Middleware and Router

#### server/app.py (modify existing file)
```python
from server.lib.metrics_middleware import metrics_collection_middleware
from server.routers import metrics

# Add middleware
app.middleware("http")(metrics_collection_middleware)

# Include router
app.include_router(metrics.router)
```

---

## Frontend Implementation

### Step 1: Generate TypeScript Client

```bash
# Generate client from OpenAPI spec
python scripts/make_fastapi_client.py

# Generated client will be in client/src/services/metricsClient.ts
```

### Step 2: Create Usage Tracker

#### client/src/services/usageTracker.ts
```typescript
import { submitUsageEvents } from './metricsClient';

interface UsageEvent {
  event_type: string;
  page_name?: string;
  element_id?: string;
  success?: boolean;
  metadata?: Record<string, any>;
  timestamp: string;
}

class UsageTracker {
  private eventQueue: UsageEvent[] = [];
  private batchSize = 20;
  private batchInterval = 10000; // 10 seconds
  private flushTimer: NodeJS.Timeout | null = null;

  constructor() {
    this.startBatchTimer();
    window.addEventListener('beforeunload', () => this.flush());
  }

  track(event: Omit<UsageEvent, 'timestamp'>) {
    this.eventQueue.push({
      ...event,
      timestamp: new Date().toISOString()
    });

    if (this.eventQueue.length >= this.batchSize) {
      this.flush();
    }
  }

  flush() {
    if (this.eventQueue.length === 0) return;

    const batch = this.eventQueue.splice(0);
    
    // Submit asynchronously, don't wait
    submitUsageEvents({ events: batch }).catch(error => {
      console.error('Failed to submit usage events:', error);
    });
  }

  private startBatchTimer() {
    this.flushTimer = setInterval(() => this.flush(), this.batchInterval);
  }
}

export const usageTracker = new UsageTracker();
```

### Step 3: Create Dashboard Components

#### client/src/components/MetricsDashboard.tsx
```typescript
import React, { useEffect, useState } from 'react';
import { getPerformanceMetrics, getUsageMetrics } from '../services/metricsClient';
import { PerformanceChart } from './PerformanceChart';
import { UsageChart } from './UsageChart';
import { MetricsTable } from './MetricsTable';
import { EndpointBreakdownTable } from './EndpointBreakdownTable';
import { Button } from '@design-bricks/react'; // Design Bricks button component

export const MetricsDashboard: React.FC = () => {
  const [timeRange, setTimeRange] = useState('24h');
  const [performanceData, setPerformanceData] = useState(null);
  const [usageData, setUsageData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load metrics on initial mount only (manual refresh pattern)
  useEffect(() => {
    loadMetrics();
  }, []); // Empty dependency array - no auto-refresh on timeRange change

  const loadMetrics = async () => {
    setLoading(true);
    try {
      const [perfData, usageData] = await Promise.all([
        getPerformanceMetrics({ time_range: timeRange }),
        getUsageMetrics({ time_range: timeRange })
      ]);
      setPerformanceData(perfData);
      setUsageData(usageData);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  // Manual refresh handler
  const handleRefresh = () => {
    loadMetrics();
  };

  if (loading) return <div>Loading metrics...</div>;

  return (
    <div className="metrics-dashboard">
      <div className="dashboard-header">
        <h1>Application Metrics</h1>
        <Button onClick={handleRefresh} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>
      
      <div className="time-range-selector">
        <select value={timeRange} onChange={e => setTimeRange(e.target.value)}>
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
          <option value="90d">Last 90 Days</option>
        </select>
      </div>

      <PerformanceChart data={performanceData} />
      <UsageChart data={usageData} />
      
      {/* Comprehensive endpoint breakdown table (FR-005) */}
      <EndpointBreakdownTable endpoints={performanceData?.endpoints} />
      
      <MetricsTable performanceData={performanceData} usageData={usageData} />
    </div>
  );
};
```

#### client/src/components/EndpointBreakdownTable.tsx
```typescript
import React, { useState, useMemo } from 'react';
import { Table } from '@design-bricks/react'; // Design Bricks table component

interface EndpointMetric {
  endpoint: string;
  method: string;
  avg_response_time_ms: number;
  p50_response_time_ms: number;
  p95_response_time_ms: number;
  p99_response_time_ms: number;
  request_count: number;
  error_count: number;
  error_rate: number; // Decimal ratio from backend (e.g., 0.0079)
}

interface EndpointBreakdownTableProps {
  endpoints: EndpointMetric[];
}

export const EndpointBreakdownTable: React.FC<EndpointBreakdownTableProps> = ({ endpoints }) => {
  const [sortColumn, setSortColumn] = useState<keyof EndpointMetric>('avg_response_time_ms');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Sort endpoints by selected column
  const sortedEndpoints = useMemo(() => {
    if (!endpoints) return [];
    
    return [...endpoints].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];
      const multiplier = sortDirection === 'asc' ? 1 : -1;
      return (aVal < bVal ? -1 : aVal > bVal ? 1 : 0) * multiplier;
    });
  }, [endpoints, sortColumn, sortDirection]);

  const handleSort = (column: keyof EndpointMetric) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  if (!endpoints || endpoints.length === 0) {
    return <div>No endpoint data available</div>;
  }

  return (
    <div className="endpoint-breakdown">
      <h2>Endpoint Performance Breakdown</h2>
      <p className="table-description">
        All tracked API endpoints (sortable by any column, no pagination)
      </p>
      
      <Table>
        <thead>
          <tr>
            <th onClick={() => handleSort('endpoint')} style={{ cursor: 'pointer' }}>
              Endpoint {sortColumn === 'endpoint' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th onClick={() => handleSort('method')} style={{ cursor: 'pointer' }}>
              Method {sortColumn === 'method' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th onClick={() => handleSort('avg_response_time_ms')} style={{ cursor: 'pointer' }}>
              Avg Response (ms) {sortColumn === 'avg_response_time_ms' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th onClick={() => handleSort('p50_response_time_ms')} style={{ cursor: 'pointer' }}>
              P50 (ms) {sortColumn === 'p50_response_time_ms' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th onClick={() => handleSort('p95_response_time_ms')} style={{ cursor: 'pointer' }}>
              P95 (ms) {sortColumn === 'p95_response_time_ms' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th onClick={() => handleSort('p99_response_time_ms')} style={{ cursor: 'pointer' }}>
              P99 (ms) {sortColumn === 'p99_response_time_ms' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th onClick={() => handleSort('request_count')} style={{ cursor: 'pointer' }}>
              Requests {sortColumn === 'request_count' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
            <th onClick={() => handleSort('error_rate')} style={{ cursor: 'pointer' }}>
              Error Rate {sortColumn === 'error_rate' && (sortDirection === 'asc' ? '↑' : '↓')}
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedEndpoints.map((endpoint, idx) => (
            <tr key={idx}>
              <td>{endpoint.endpoint}</td>
              <td>{endpoint.method}</td>
              <td>{endpoint.avg_response_time_ms.toFixed(2)}</td>
              <td>{endpoint.p50_response_time_ms.toFixed(2)}</td>
              <td>{endpoint.p95_response_time_ms.toFixed(2)}</td>
              <td>{endpoint.p99_response_time_ms.toFixed(2)}</td>
              <td>{endpoint.request_count.toLocaleString()}</td>
              <td>
                {/* Convert decimal ratio to percentage string (e.g., 0.0079 → "0.79%") */}
                {(endpoint.error_rate * 100).toFixed(2)}%
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
};
```

### Step 4: Integrate Usage Tracking

#### client/src/App.tsx (add tracking)
```typescript
import { usageTracker } from './services/usageTracker';

// Track page views
useEffect(() => {
  usageTracker.track({
    event_type: 'page_view',
    page_name: location.pathname
  });
}, [location.pathname]);

// Track button clicks
const handleButtonClick = (elementId: string) => {
  usageTracker.track({
    event_type: 'button_click',
    page_name: location.pathname,
    element_id: elementId
  });
  
  // ... rest of button logic
};
```

---

## Scheduled Jobs

### Create Aggregation Job

#### scripts/aggregate_metrics.py
```python
"""
Daily aggregation job for metrics data lifecycle management.
Aggregates 7-day-old raw metrics into hourly summaries and deletes raw records.
"""

from sqlalchemy import create_engine, and_, func
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from server.models.performance_metric import PerformanceMetric
from server.models.usage_event import UsageEvent
from server.models.aggregated_metric import AggregatedMetric
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def aggregate_performance_metrics(session, cutoff_date):
    """Aggregate 7-day-old performance metrics into hourly buckets"""
    logger.info(f"Aggregating performance metrics older than {cutoff_date}")
    
    # Query raw metrics older than 7 days
    metrics = session.query(PerformanceMetric).filter(
        PerformanceMetric.timestamp < cutoff_date
    ).all()
    
    if not metrics:
        logger.info("No performance metrics to aggregate")
        return 0
    
    # Group by hour and endpoint
    hourly_buckets = {}
    for metric in metrics:
        hour = metric.timestamp.replace(minute=0, second=0, microsecond=0)
        key = (hour, metric.endpoint)
        
        if key not in hourly_buckets:
            hourly_buckets[key] = []
        hourly_buckets[key].append(metric)
    
    # Create aggregated records
    aggregated_count = 0
    for (hour, endpoint), metrics_group in hourly_buckets.items():
        response_times = [m.response_time_ms for m in metrics_group]
        error_count = sum(1 for m in metrics_group if m.status_code >= 400)
        
        aggregated = AggregatedMetric(
            time_bucket=hour,
            metric_type="performance",
            endpoint_path=endpoint,
            aggregated_values={
                "avg_response_time_ms": sum(response_times) / len(response_times),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
                "total_requests": len(metrics_group),
                "error_count": error_count,
                "error_rate": error_count / len(metrics_group)
            },
            sample_count=len(metrics_group)
        )
        session.add(aggregated)
        aggregated_count += 1
    
    # Delete raw records
    session.query(PerformanceMetric).filter(
        PerformanceMetric.timestamp < cutoff_date
    ).delete()
    
    session.commit()
    logger.info(f"Aggregated {aggregated_count} performance metric buckets, deleted {len(metrics)} raw records")
    return aggregated_count

def main():
    """Main aggregation job entry point"""
    logger.info("Starting metrics aggregation job")
    
    # Calculate cutoff date (7 days ago)
    cutoff_date = datetime.utcnow() - timedelta(days=7)
    
    # Create database session
    engine = create_engine(os.environ['DATABASE_URL'])
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Aggregate performance metrics
        perf_count = aggregate_performance_metrics(session, cutoff_date)
        
        # Aggregate usage events (similar implementation)
        # usage_count = aggregate_usage_events(session, cutoff_date)
        
        logger.info(f"Aggregation job completed: {perf_count} buckets created")
    except Exception as e:
        logger.error(f"Aggregation job failed: {e}", exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
```

### Schedule with Databricks Workflow

#### databricks.yml (add job configuration)
```yaml
resources:
  jobs:
    metrics_aggregation_job:
      name: "Metrics Aggregation Job"
      schedule:
        quartz_cron_expression: "0 0 2 * * ?"  # Daily at 2 AM
        timezone_id: "UTC"
      tasks:
        - task_key: aggregate_metrics
          python_wheel_task:
            package_name: "databricks_app_template"
            entry_point: "aggregate_metrics"
          libraries:
            - pypi:
                package: "sqlalchemy"
            - pypi:
                package: "psycopg2-binary"
```

---

## Testing

### Run Contract Tests

```bash
# Run contract tests (should pass after implementation)
pytest tests/contract/test_metrics_api.py -v

# Verify all endpoints return correct status codes
```

### Run Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/integration/test_metrics_collection.py -v
```

### Manual API Testing

```bash
# Test performance metrics endpoint
curl -H "X-Forwarded-Access-Token: $DATABRICKS_TOKEN" \
  http://localhost:8000/api/v1/metrics/performance?time_range=24h

# Test usage events submission
curl -X POST -H "X-Forwarded-Access-Token: $DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"event_type":"page_view","page_name":"/test","timestamp":"2025-10-18T12:00:00Z"}]}' \
  http://localhost:8000/api/v1/metrics/usage-events
```

---

## Deployment

### Pre-Deployment Checklist

```bash
# 1. Run full test suite
pytest tests/ -v --cov

# 2. Validate bundle configuration
databricks bundle validate

# 3. Type checking
ruff check server/
cd client && bun run type-check

# 4. Format code
./fix.sh
```

### Deploy to Databricks

```bash
# Deploy to development
databricks bundle deploy --target dev

# Monitor deployment logs
python dba_logz.py

# Verify endpoints
python dba_client.py
```

### Post-Deployment Validation

```bash
# Monitor logs for 60 seconds
python dba_logz.py

# Check for errors in startup
# Look for: "Uvicorn running", no Python exceptions

# Test metrics endpoint
curl -H "X-Forwarded-Access-Token: $DATABRICKS_TOKEN" \
  https://your-workspace.cloud.databricks.com/apps/your-app/api/v1/metrics/performance
```

---

## Usage

### For Administrators

#### Access Metrics Dashboard
1. Navigate to the app URL: `https://your-workspace.cloud.databricks.com/apps/your-app`
2. Click "Metrics" in the navigation menu
3. Select time range (24h, 7d, 30d, 90d)
4. View performance charts, usage trends, and endpoint statistics

#### Query Metrics API
```bash
# Get performance metrics for last 7 days
GET /api/v1/metrics/performance?time_range=7d

# Get usage metrics filtered by event type
GET /api/v1/metrics/usage?time_range=24h&event_type=query_executed

# Get time-series data for charts
GET /api/v1/metrics/time-series?time_range=30d&metric_type=both
```

### For Developers

#### Track Custom Events
```typescript
import { usageTracker } from './services/usageTracker';

// Track feature usage
usageTracker.track({
  event_type: 'query_executed',
  page_name: '/lakebase/sources',
  success: true,
  metadata: {
    query: 'SELECT * FROM table',
    execution_time_ms: 234
  }
});
```

#### Monitor Metrics Collection
```bash
# Check metrics collection logs
python dba_logz.py | grep "Recorded performance metric"

# Verify metrics database
psql -h $LAKEBASE_HOST -U $LAKEBASE_USER -d $LAKEBASE_DATABASE -c "SELECT COUNT(*) FROM performance_metrics;"
```

---

## Troubleshooting

### Issue: Metrics not appearing in dashboard

**Symptoms**: Dashboard shows "No data available"

**Diagnosis**:
```bash
# Check if metrics are being collected
psql -c "SELECT COUNT(*), MAX(timestamp) FROM performance_metrics;"

# Check middleware is registered
curl http://localhost:8000/api/v1/lakebase/sources
# Then check if metric was created
```

**Resolution**:
1. Verify middleware is registered in `server/app.py`
2. Check database connection is working
3. Verify Lakebase credentials in `.env.local`

### Issue: Admin privilege check failing

**Symptoms**: All users get 403 Forbidden even with admin privileges

**Diagnosis**:
```bash
# Check admin service logs
python dba_logz.py | grep "Admin check"

# Test Databricks API manually
curl -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  https://your-workspace.cloud.databricks.com/api/2.0/preview/scim/v2/Me
```

**Resolution**:
1. Verify Databricks token has correct permissions
2. Check admin group name in `admin_service.py` logic
3. Verify user is actually a workspace admin in Databricks

### Issue: Aggregation job not running

**Symptoms**: Raw metrics table growing unbounded, no aggregated data

**Diagnosis**:
```bash
# Check job status in Databricks
databricks jobs list | grep "Metrics Aggregation"

# Check job runs
databricks jobs runs list --job-id <job-id>
```

**Resolution**:
1. Verify job is defined in `databricks.yml`
2. Check job schedule configuration
3. Run job manually to test: `python scripts/aggregate_metrics.py`
4. Check job logs for errors

### Issue: High latency on metrics endpoints

**Symptoms**: Dashboard takes >10 seconds to load

**Diagnosis**:
```sql
-- Check table sizes
SELECT 
  relname AS table_name,
  pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_catalog.pg_statio_user_tables
WHERE relname IN ('performance_metrics', 'usage_events', 'aggregated_metrics');

-- Check index usage
SELECT * FROM pg_stat_user_indexes WHERE relname = 'performance_metrics';
```

**Resolution**:
1. Ensure aggregation job is running (reduces raw table size)
2. Verify indexes exist on timestamp, endpoint, user_id columns
3. Add LIMIT clause to queries for initial dashboard load
4. Consider adding database connection pooling configuration

---

## References

- **Feature Spec**: [spec.md](./spec.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contracts**: [contracts/metrics-api.yaml](./contracts/metrics-api.yaml)
- **Research**: [research.md](./research.md)
- **Constitution**: [/.specify/memory/constitution.md](/.specify/memory/constitution.md)

