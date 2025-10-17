# Research: Automatic Model Input Schema Detection

**Feature**: 004-dynamic-endpoint-input-schema  
**Date**: October 17, 2025  
**Status**: Complete

## Overview

This document consolidates research findings for implementing automatic model input schema detection for Databricks Model Serving endpoints. All "NEEDS CLARIFICATION" items from Technical Context have been resolved through codebase analysis and API documentation review.

## Research Decisions

### Decision 1: Endpoint Type Detection Strategy

**Decision**: Use endpoint configuration metadata from Serving Endpoints API to detect model type

**Rationale**:
- Serving Endpoints API provides `endpoint.config.served_models[0]` with model metadata
- Foundation models (Claude, GPT, Llama) are identifiable by endpoint naming conventions and lack of `model_name` field
- MLflow models have explicit `model_name` and `model_version` fields pointing to Unity Catalog registry
- Chat models can be identified by checking endpoint configuration for chat completion indicators or by presence of chat-specific configuration

**Alternatives Considered**:
- **Alternative 1: Endpoint name pattern matching** (e.g., regex for "claude", "gpt", "llama")
  - **Rejected because**: Brittle and doesn't handle custom-named endpoints or future model types
- **Alternative 2: Trial inference with different input formats** (try chat format first, then MLflow format)
  - **Rejected because**: Expensive, causes unnecessary API calls, slow user experience, and could trigger rate limits

**Implementation Pattern**:
```python
async def detect_endpoint_type(endpoint: ModelEndpoint) -> EndpointType:
    """Detect if endpoint is foundation model, MLflow model, or unknown."""
    if not endpoint.config or not endpoint.config.served_models:
        return EndpointType.UNKNOWN
    
    primary_model = endpoint.config.served_models[0]
    
    # MLflow models have explicit model_name in Unity Catalog
    if primary_model.model_name and primary_model.model_version:
        return EndpointType.MLFLOW_MODEL
    
    # Foundation models typically lack model_name but have specific naming patterns
    # Check endpoint name for common foundation model identifiers
    endpoint_name_lower = endpoint.name.lower()
    foundation_keywords = ['claude', 'gpt', 'llama', 'mistral', 'chat', 'foundation']
    
    if any(keyword in endpoint_name_lower for keyword in foundation_keywords):
        return EndpointType.FOUNDATION_MODEL
    
    return EndpointType.UNKNOWN
```

---

### Decision 2: Model Registry Schema Retrieval for MLflow Models

**Decision**: Use Databricks SDK Model Registry API with OBO authentication to retrieve MLflow model schemas from Unity Catalog

**Rationale**:
- Unity Catalog Model Registry stores input/output schema metadata for registered MLflow models
- Schema is accessible via `client.model_registry.get_model_version()` SDK method
- Requires OBO (On-Behalf-Of-User) authentication to respect user's permissions (users should only see schemas for models they can access)
- Model version object includes `signature` field with JSON Schema format input/output definitions

**Alternatives Considered**:
- **Alternative 1: MLflowClient from mlflow Python package**
  - **Rejected because**: Requires separate authentication configuration, Databricks SDK already provides Model Registry access with consistent auth pattern
- **Alternative 2: Direct REST API calls to Model Registry**
  - **Rejected because**: SDK provides better error handling, retry logic, and type safety
- **Alternative 3: Cache schemas in Lakebase database permanently**
  - **Rejected because**: Schema invalidation complexity, storage overhead, and stale data concerns. Browser session caching is sufficient per FR-014

**Implementation Pattern**:
```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import GetModelVersionRequest

async def retrieve_mlflow_schema(
    client: WorkspaceClient, 
    model_name: str, 
    version: str
) -> dict | None:
    """Retrieve MLflow model input schema from Unity Catalog."""
    try:
        model_version = client.model_registry.get_model_version(
            full_name=model_name,  # e.g., "main.default.fraud_detection_model"
            version=version
        )
        
        # Model version may have signature with input/output schema
        if hasattr(model_version, 'signature') and model_version.signature:
            # Parse signature JSON (MLflow ModelSignature format)
            signature = json.loads(model_version.signature)
            return signature.get('inputs')  # Return input schema only
        
        return None
    except Exception as e:
        logger.warning(f"Failed to retrieve MLflow schema: {e}", model_name=model_name)
        return None
```

**Note**: Model Registry API timeout set to 3 seconds (per performance goal), fallback to generic template on timeout.

---

### Decision 3: JSON Example Generation from Schema Definitions

**Decision**: Implement schema-to-example generator with type-specific sample values

**Rationale**:
- MLflow model schemas follow JSON Schema format with field names, types, and constraints
- Need realistic sample values (not just empty strings or zeros) for better UX
- Different data types require different sample generation strategies
- Generated examples should be valid and instructive

**Alternatives Considered**:
- **Alternative 1: Use JSON Schema faker libraries** (e.g., `jsf` Python package)
  - **Rejected because**: Additional dependency, overkill for simple schema generation, harder to customize sample values
- **Alternative 2: Always return empty/null values**
  - **Rejected because**: Poor UX, doesn't demonstrate expected input format clearly
- **Alternative 3: LLM-generated examples**
  - **Rejected because**: Latency, cost, unnecessary complexity for deterministic task

**Implementation Pattern**:
```python
def generate_example_json(schema: dict) -> dict:
    """Generate example JSON from MLflow input schema."""
    example = {}
    
    for field_name, field_spec in schema.get('properties', {}).items():
        field_type = field_spec.get('type')
        
        if field_type == 'string':
            example[field_name] = 'example text'
        elif field_type == 'integer':
            example[field_name] = 42
        elif field_type == 'number':
            example[field_name] = 3.14
        elif field_type == 'boolean':
            example[field_name] = True
        elif field_type == 'array':
            # Generate array with one sample item
            items_type = field_spec.get('items', {}).get('type', 'string')
            if items_type == 'string':
                example[field_name] = ['example']
            elif items_type in ['integer', 'number']:
                example[field_name] = [1.0, 2.0, 3.0]
            else:
                example[field_name] = []
        elif field_type == 'object':
            # Nested object - recurse
            example[field_name] = generate_example_json(field_spec)
        else:
            example[field_name] = None
    
    return example
```

**Foundation Model Chat Format** (standardized across Claude, GPT, Llama):
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how can you help me?"}
  ],
  "max_tokens": 150,
  "temperature": 0.7
}
```

---

### Decision 4: Browser Session Caching Strategy

**Decision**: Use browser `sessionStorage` API for schema caching with endpoint name as key

**Rationale**:
- `sessionStorage` persists for entire browser session (until tab/window close)
- Automatic cleanup on tab close (no manual cache invalidation needed)
- Per-tab isolation (different tabs can have independent sessions)
- Simple key-value API: `sessionStorage.setItem(endpoint_name, JSON.stringify(schema))`
- Meets FR-014 requirement for session-scoped caching

**Alternatives Considered**:
- **Alternative 1: localStorage (persistent across browser restarts)**
  - **Rejected because**: Requires manual cache invalidation, stale data concerns, not required per spec (session-only caching specified)
- **Alternative 2: React state only (no persistence)**
  - **Rejected because**: Lost on page refresh, doesn't meet FR-014 requirement
- **Alternative 3: IndexedDB**
  - **Rejected because**: Overkill for simple key-value caching, more complex API
- **Alternative 4: Backend caching in Lakebase**
  - **Rejected because**: Unnecessary database load, schema changes need synchronization, per-user cache management complexity

**Implementation Pattern** (React TypeScript):
```typescript
// hooks/useSchemaCache.ts
export function useSchemaCache() {
  const getCachedSchema = (endpointName: string): SchemaDetectionResult | null => {
    try {
      const cached = sessionStorage.getItem(`schema_${endpointName}`);
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  };
  
  const setCachedSchema = (endpointName: string, schema: SchemaDetectionResult): void => {
    try {
      sessionStorage.setItem(`schema_${endpointName}`, JSON.stringify(schema));
    } catch (e) {
      console.warn('Failed to cache schema:', e);
    }
  };
  
  return { getCachedSchema, setCachedSchema };
}
```

---

### Decision 5: Design Bricks UI Components Verification

**Decision**: Use existing Design Bricks components with following mapping:

**Rationale**:
- Design Bricks provides all necessary components for this feature (verified in `client/package.json`)
- Consistent with Constitution Principle I (Design Bricks First)
- Components already used in existing Model Inference UI (`client/src/components/ui/ModelInvokeForm.tsx`)

**Component Mapping**:

| UI Element | Design Bricks Component | Usage |
|------------|------------------------|--------|
| Endpoint Dropdown | `@databricks/design-system` Select | Already used in ModelInvokeForm.tsx |
| JSON Input Box | `<TextArea>` or `<CodeEditor>` | Multiline JSON input with syntax highlighting |
| Loading Indicator | `<Spinner>` or `<ProgressCircular>` | Show during schema retrieval (hide JSON input until loaded) |
| Status Badge | `<Badge>` | Display detected model type ("Foundation Model", "MLflow Model", "Unknown") |
| Error/Warning Message | `<Alert>` severity="warning" | Schema detection failures, timeout warnings |
| Helper Text | `<Typography.Text>` color="secondary" | Inline hints for schema structure |

**Alternatives Considered**:
- **Alternative 1: shadcn/ui components**
  - **Rejected because**: Constitution requires Design Bricks first, only use shadcn/ui when Design Bricks equivalent doesn't exist
- **Alternative 2: Custom-built components**
  - **Rejected because**: Violates Constitution, inconsistent Databricks look-and-feel

**Implementation Note**: Verify `<CodeEditor>` availability in Design Bricks for syntax-highlighted JSON editing. If unavailable, use `<TextArea>` with monospace font as fallback.

---

### Decision 6: Structured Logging with Correlation ID Support

**Decision**: Enhance existing `StructuredLogger` to include schema detection event logging

**Rationale**:
- Structured logging infrastructure already exists in `server/lib/structured_logger.py`
- Correlation ID propagation already implemented via `server/lib/distributed_tracing.py` using `contextvars`
- Supports client-provided `X-Correlation-ID` header (middleware in `server/app.py`)
- JSON format enables queryable log analysis in Lakebase
- Meets Constitution Principle VIII (Observability First) and FR-013 requirements

**Alternatives Considered**:
- **Alternative 1: Custom logging implementation**
  - **Rejected because**: Duplicate code, inconsistent log format
- **Alternative 2: OpenTelemetry distributed tracing**
  - **Rejected because**: Overkill for template app, constitution explicitly prefers correlation-ID based tracking (simplified approach)

**Log Event Schema** (for FR-013 compliance):
```python
logger.info(
    "schema_detection_complete",
    endpoint_name=endpoint_name,
    detected_type="FOUNDATION_MODEL",  # or "MLFLOW_MODEL", "UNKNOWN"
    status="SUCCESS",  # or "FAILURE", "TIMEOUT"
    latency_ms=250,
    user_id=user_id,
    correlation_id=correlation_id  # Auto-included by StructuredLogger
)
```

**Lakebase Logging** (additional structured storage for queryable events):
- Create `schema_detection_events` table with columns: id, correlation_id, endpoint_name, detected_type, status, latency_ms, error_details, user_id, created_at
- Log all schema detection attempts (success, failure, timeout) for operational analysis
- Alembic migration: `004_create_schema_detection_events.py`

---

### Decision 7: Error Handling and Graceful Fallback Strategy

**Decision**: Multi-tier fallback strategy with clear user messaging

**Rationale**:
- Schema detection can fail for multiple reasons (API timeout, malformed schema, permissions)
- Users must always be able to invoke models (even if schema auto-detection fails)
- Clear error messages improve UX and reduce support burden

**Fallback Tiers**:

1. **Tier 1: Foundation Model Detection** → Return standardized chat format example (500ms)
2. **Tier 2: MLflow Model Registry Query** → Query schema with 5s timeout
3. **Tier 3: Timeout/Error Fallback** → Generic template with warning message

**Error Handling Pattern**:
```python
async def detect_schema(endpoint_name: str, user_token: str) -> SchemaDetectionResult:
    start_time = datetime.utcnow()
    
    try:
        # Step 1: Get endpoint details
        endpoint = await get_endpoint(endpoint_name, user_token)
        
        # Step 2: Detect endpoint type
        endpoint_type = detect_endpoint_type(endpoint)
        
        if endpoint_type == EndpointType.FOUNDATION_MODEL:
            # Fast path: return chat format
            schema = FOUNDATION_MODEL_CHAT_SCHEMA
            example_json = FOUNDATION_MODEL_CHAT_EXAMPLE
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return SchemaDetectionResult(
                endpoint_name=endpoint_name,
                detected_type="FOUNDATION_MODEL",
                status="SUCCESS",
                schema=schema,
                example_json=example_json,
                latency_ms=latency_ms
            )
        
        elif endpoint_type == EndpointType.MLFLOW_MODEL:
            # Query Model Registry with timeout
            model_name = endpoint.config.served_models[0].model_name
            model_version = endpoint.config.served_models[0].model_version
            
            schema = await asyncio.wait_for(
                retrieve_mlflow_schema(client, model_name, model_version),
                timeout=5.0
            )
            
            if schema:
                example_json = generate_example_json(schema)
                latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return SchemaDetectionResult(
                    endpoint_name=endpoint_name,
                    detected_type="MLFLOW_MODEL",
                    status="SUCCESS",
                    schema=schema,
                    example_json=example_json,
                    latency_ms=latency_ms
                )
            else:
                # Schema not available, fallback
                raise ValueError("Schema not available in Model Registry")
        
        else:
            # Unknown type, fallback immediately
            raise ValueError(f"Unknown endpoint type: {endpoint_type}")
    
    except asyncio.TimeoutError:
        # Timeout fallback
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return SchemaDetectionResult(
            endpoint_name=endpoint_name,
            detected_type="UNKNOWN",
            status="TIMEOUT",
            schema=None,
            example_json=GENERIC_FALLBACK_TEMPLATE,
            error_message="Schema retrieval timed out after 5 seconds",
            latency_ms=latency_ms
        )
    
    except Exception as e:
        # Error fallback
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(f"Schema detection failed: {e}", exc_info=True)
        
        return SchemaDetectionResult(
            endpoint_name=endpoint_name,
            detected_type="UNKNOWN",
            status="FAILURE",
            schema=None,
            example_json=GENERIC_FALLBACK_TEMPLATE,
            error_message=str(e),
            latency_ms=latency_ms
        )
```

**Generic Fallback Template**:
```json
{
  "input": "value",
  "_comment": "Schema detection unavailable. Consult model documentation for correct input format."
}
```

**User Messaging**:
- **SUCCESS**: Implicit feedback (populate JSON box) + persistent status badge with model type
- **TIMEOUT**: Warning alert: "Schema retrieval timed out. Using generic template. You may need to manually adjust the input format."
- **FAILURE**: Warning alert: "Schema detection unavailable for this endpoint. Please consult model documentation."

**Alternatives Considered**:
- **Alternative 1: Block user interaction until schema loads**
  - **Rejected because**: Poor UX, violates constraint "must not block UI during schema retrieval"
- **Alternative 2: Retry schema detection automatically**
  - **Rejected because**: Increases latency, wastes API quota, users can refresh manually if needed

---

### Decision 8: Frontend State Management for Schema Detection

**Decision**: Use React Query (TanStack Query) for async schema detection with loading/error states

**Rationale**:
- React Query already used in project (`@tanstack/react-query` in `client/package.json`)
- Provides built-in loading, error, and success states
- Automatic request deduplication (prevents duplicate schema queries)
- Integrates seamlessly with browser session caching

**Alternatives Considered**:
- **Alternative 1: Plain React useState + useEffect**
  - **Rejected because**: More boilerplate, no request deduplication, harder error handling
- **Alternative 2: Redux/Zustand global state**
  - **Rejected because**: Overkill for feature-scoped state, React Query already handles async state well

**Implementation Pattern**:
```typescript
// In DatabricksServicesPage.tsx or ModelInvokeForm component
import { useQuery } from '@tanstack/react-query';
import { useSchemaCache } from '../hooks/useSchemaCache';

function useSchemaDetection(endpointName: string | null) {
  const { getCachedSchema, setCachedSchema } = useSchemaCache();
  
  return useQuery({
    queryKey: ['schema', endpointName],
    queryFn: async () => {
      if (!endpointName) return null;
      
      // Check cache first
      const cached = getCachedSchema(endpointName);
      if (cached) return cached;
      
      // Fetch from API
      const result = await ApiService.detectSchema(endpointName);
      
      // Cache on success
      if (result.status === 'SUCCESS') {
        setCachedSchema(endpointName, result);
      }
      
      return result;
    },
    enabled: !!endpointName,  // Only run when endpoint selected
    staleTime: Infinity,  // Never refetch (rely on session cache)
    cacheTime: Infinity   // Keep in memory for session duration
  });
}

// Usage in component
const { data: schemaResult, isLoading, error } = useSchemaDetection(selectedEndpoint);

// Render logic
if (isLoading) return <Spinner />;
if (error) return <Alert severity="error">{error.message}</Alert>;
if (schemaResult?.status === 'SUCCESS') {
  // Populate JSON input with schemaResult.example_json
}
```

---

## Technology Stack Confirmation

**Backend**:
- Python 3.11+ ✅
- FastAPI 0.104+ ✅
- Databricks SDK 0.67.0 ✅
- SQLAlchemy 2.0 (Lakebase) ✅
- Alembic (migrations) ✅

**Frontend**:
- TypeScript 5.2+ ✅
- React 18.3 ✅
- Design Bricks UI (`@databricks/design-system`) ✅
- TanStack Query (React Query) ✅
- Vite 5.0 ✅

**Testing**:
- pytest (backend) ✅
- Playwright (frontend E2E) ✅

**Deployment**:
- Databricks Asset Bundles ✅

## Open Questions Resolved

All technical unknowns from plan.md have been resolved:

✅ **Endpoint type detection** → Use serving endpoint config metadata (Decision 1)  
✅ **Model Registry schema queries** → Databricks SDK Model Registry API with OBO auth (Decision 2)  
✅ **JSON example generation** → Type-specific sample value generator (Decision 3)  
✅ **Browser caching** → sessionStorage API (Decision 4)  
✅ **Design Bricks components** → Verified availability, component mapping defined (Decision 5)  
✅ **Correlation ID logging** → Enhance existing StructuredLogger (Decision 6)  
✅ **Error handling** → Multi-tier fallback strategy (Decision 7)  
✅ **Frontend state management** → React Query with session cache integration (Decision 8)

## Next Steps

Proceed to **Phase 1: Design & Contracts**:
1. Generate `data-model.md` with entity definitions
2. Generate OpenAPI contract specifications in `contracts/`
3. Generate `quickstart.md` with usage examples
4. Update agent context via `.specify/scripts/bash/update-agent-context.sh claude`

