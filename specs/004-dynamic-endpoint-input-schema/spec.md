# Feature Specification: Automatic Model Input Schema Detection

**Feature Branch**: `004-dynamic-endpoint-input-schema`  
**Created**: October 17, 2025  
**Status**: Draft  
**Input**: User description: "Update the Model Inference feature to automatically identify the model input schema json based on the selected endpoint and generate the example input JSON based on this schema. Look at the API docs here for details @https://docs.databricks.com/api/workspace/servingendpoints"

## Clarifications

### Session 2025-10-17

- Q: Should schema detection events be logged for observability and debugging? → A: Yes - log all schema detection events (success, failure, timeout) with correlation ID, endpoint name, detected type, and latency to Lakebase for queryable operational data
- Q: Should successfully retrieved schemas be cached in the browser session? → A: Yes - cache all schemas (foundation and MLflow) for the entire browser session, refresh only on page reload
- Q: How should success confirmation be communicated to users? → A: Implicit feedback (populate JSON box, remove loading indicator) plus persistent status badge displaying detected model type (e.g., "Foundation Model", "MLflow Model", or "Unknown")
- Q: How should schema auto-population behave when users have already started editing? → A: Not applicable - the input JSON box only appears after schema retrieval completes, preventing the race condition of user edits during schema detection
- Q: When returning to a previously selected endpoint, should the system restore the user's last edits or reload the cached schema? → A: Reload cached schema - always show the auto-generated schema example for the selected endpoint, discarding previous edits when switching away to a different endpoint
- Q: When the Model Registry API returns a 429 rate limit error during MLflow schema detection, how should the system respond? → A: Queue the request and retry with exponential backoff (2s, 4s, 8s max)
- Q: For MLflow models, when a schema field has an array type, what should the generated example JSON contain for that array? → A: Three sample items for primitive arrays to show pattern (e.g., `[1.0, 2.0, 3.0]` for numeric, `["item1", "item2", "item3"]` for strings), and nested structure examples if array contains objects
- Q: When a user lacks Unity Catalog permissions to read a specific MLflow model's schema, how should the system behave? → A: Show "Permission Denied" error and block model invocation entirely

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Schema Detection for Foundation Models (Priority: P1)

When a user selects a foundation model endpoint (such as Claude, GPT, or other chat-based models), the application automatically detects that it uses a standardized chat format and displays a pre-populated JSON input example with the correct message structure, eliminating manual schema lookup and reducing input errors.

**Why this priority**: Foundation models are the most commonly used model type in Databricks Model Serving and have standardized schemas. Automating schema detection for these models delivers immediate value to the majority of users and prevents the most common input format errors.

**Independent Test**: Can be fully tested by selecting any foundation model endpoint from a dropdown and verifying that the input JSON box automatically populates with a valid chat-format example like `{"messages": [{"role": "user", "content": "Hello"}], "max_tokens": 150}`.

**Acceptance Scenarios**:

1. **Given** a user is on the Model Inference page, **When** they select a foundation model endpoint (e.g., Claude Sonnet 4) from the dropdown, **Then** the input JSON box automatically updates with a valid chat-format example including messages array with role and content fields, and the example includes common optional parameters like max_tokens
2. **Given** a user has selected a foundation model endpoint, **When** they view the input JSON box, **Then** they see helpful inline hints explaining the schema structure (e.g., "role can be: system, user, assistant")
3. **Given** a user modifies the auto-populated chat input, **When** they click Invoke Model, **Then** the request succeeds with their custom input while maintaining the correct schema structure

---

### User Story 2 - Schema Retrieval for MLflow Models (Priority: P2)

When a user selects an MLflow model endpoint registered in Unity Catalog, the application automatically queries the Model Registry to retrieve the model's input schema and generates a valid example JSON payload based on the schema definition, reducing the time needed to understand model requirements and preventing schema mismatch errors.

**Why this priority**: MLflow models have custom schemas that vary by use case. Automatic schema detection prevents trial-and-error testing and reduces inference errors, but is lower priority than foundation models since MLflow models require additional API calls to the Model Registry.

**Independent Test**: Can be fully tested by selecting an MLflow model endpoint with a defined input schema and verifying that the input JSON box displays a generated example matching the schema's field names, types, and constraints.

**Acceptance Scenarios**:

1. **Given** a user selects an MLflow model endpoint, **When** the endpoint metadata indicates it's a Unity Catalog registered model, **Then** the application queries the Model Registry API to retrieve the input schema definition
2. **Given** the Model Registry returns a valid input schema (with field names, data types, and constraints), **When** the schema is processed, **Then** the application generates a realistic example JSON payload with appropriate sample values for each field type (strings, numbers, booleans, arrays)
3. **Given** an MLflow model schema includes optional and required fields, **When** the example JSON is generated, **Then** all required fields are included with valid sample values and optional fields are shown but marked as optional in helper text

---

### User Story 3 - Graceful Fallback for Unknown Schemas (Priority: P3)

When a user selects an endpoint where the schema cannot be automatically detected (legacy models, external endpoints, or schema retrieval failures), the application displays a generic JSON input template with clear instructions for manually entering the correct format, ensuring users can still invoke the model while understanding why automation isn't available.

**Why this priority**: This handles edge cases where automation fails. While important for completeness, it's lower priority since most Databricks-hosted models fall into P1 or P2 categories. The current manual input flow already handles this scenario.

**Independent Test**: Can be fully tested by selecting an endpoint without schema metadata and verifying that a helpful default JSON structure appears with clear instructions to consult model documentation.

**Acceptance Scenarios**:

1. **Given** a user selects an endpoint where schema detection fails (Model Registry query returns 404 or timeout), **When** the input JSON box updates, **Then** it displays a generic template like `{"input": "value"}` with a warning message explaining that automatic schema detection is unavailable
2. **Given** schema retrieval is taking longer than expected, **When** the user waits for the schema to load, **Then** a loading indicator appears (the input JSON box remains hidden until schema loads) and the Invoke button is temporarily disabled until schema loading completes or times out (5 second timeout)
3. **Given** a user encounters a schema detection failure, **When** they view the error message, **Then** it includes actionable guidance like "Consult model documentation at [link]" or "Try manual input format"

---

### Edge Cases

- What happens when Model Registry API returns a schema with unsupported or complex nested data types (nested objects, recursive references)? System should simplify to basic JSON structure and warn user that full schema complexity cannot be displayed automatically
- How does the system handle schema retrieval timeouts (>5 seconds)? Fall back to generic template with timeout warning message
- What if the endpoint type detection is ambiguous (endpoint name doesn't clearly indicate foundation vs MLflow model)? Use heuristic-based detection: check endpoint config for chat completion indicators, then attempt Model Registry schema query, finally fall back to generic template
- What if the same endpoint name has different schemas across environments (dev vs prod)? Cache schemas by endpoint name within the browser session, meaning schemas persist until page reload. Users must reload the page when switching environments to refresh cached schemas
- How should the system behave if the Model Registry schema definition is malformed or incomplete (missing field types, invalid JSON Schema)? Display partial schema where possible with clear indication of incomplete fields, provide fallback to generic template
- How does the system handle Model Registry API rate limiting (429 errors)? Queue the request and retry with exponential backoff (2 seconds, 4 seconds, 8 seconds maximum). If all retries fail, fall back to generic template with rate limit error message
- How does the system handle Unity Catalog permission errors when a user cannot read an MLflow model's schema? Display "Permission Denied" error message with clear explanation and disable the Invoke Model button. Users cannot invoke models they lack permissions to access

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect endpoint type (foundation model vs MLflow model vs unknown) when a user selects an endpoint from the dropdown
- **FR-002**: System MUST automatically populate the input JSON box with a valid chat-format example (including messages array with role and content fields, and common parameters like max_tokens) when a foundation model endpoint is selected
- **FR-003**: System MUST query the Model Registry API to retrieve input schema when an MLflow model registered in Unity Catalog is selected
- **FR-004**: System MUST generate realistic example JSON payloads based on retrieved MLflow model schemas, including appropriate sample values for each field type (e.g., "example text" for strings, 42 for integers, 3.14 for floats, true/false for booleans). For array fields, generate three sample items for primitive types (e.g., `[1.0, 2.0, 3.0]` for numeric arrays, `["item1", "item2", "item3"]` for string arrays) to demonstrate pattern, and include nested structure examples for arrays of objects. Limit array examples to maximum of 3 items to avoid excessively large generated examples. For empty arrays in schemas, generate `[]` with a comment indicating the expected item type
- **FR-005**: System MUST display schema detection status to users with three states: (a) Loading indicator during schema retrieval, (b) Implicit success feedback by populating the JSON input box and removing the loading indicator, accompanied by a persistent status badge showing the detected model type (Foundation Model, MLflow Model, or Unknown), (c) Warning message when schema detection fails with fallback to generic template
- **FR-006**: System MUST handle schema retrieval failures gracefully by falling back to a generic JSON template with clear instructions for manual input
- **FR-007**: System MUST implement a timeout of 5 seconds for Model Registry schema queries, after which it falls back to generic template with timeout explanation
- **FR-007a**: System MUST implement exponential backoff retry logic for Model Registry API rate limit errors (429 status): retry with delays of 2 seconds, 4 seconds, and 8 seconds (maximum 3 retries). If all retries fail, fall back to generic template with rate limit error message
- **FR-007b**: System MUST handle Unity Catalog permission errors (403 Forbidden) when querying MLflow model schemas by displaying a clear "Permission Denied" error message and disabling the Invoke Model button. Users must not be allowed to invoke models they lack permissions to access
- **FR-008**: System MUST validate that auto-generated example JSON conforms to the retrieved schema before displaying it to users
- **FR-009**: System MUST replace the input JSON content with the newly selected endpoint's cached schema example whenever a user switches endpoints, discarding any previous edits to ensure users always start with a valid schema template for the selected model. The input JSON box only appears after schema detection completes for the selected endpoint
- **FR-010**: System MUST provide inline help text explaining schema structure for automatically detected formats (e.g., for chat models: "role can be: system, user, assistant; content is the message text")
- **FR-011**: System MUST distinguish between required and optional fields in MLflow model schemas, clearly marking optional fields in helper text or UI indicators
- **FR-012**: System MUST handle complex or nested schema types by simplifying to basic JSON structures and displaying a warning that full schema complexity cannot be automatically represented
- **FR-013**: System MUST log all schema detection events (success, failure, timeout) to Lakebase with correlation ID (from X-Correlation-ID header if client-provided, else server-generated UUID), endpoint name, detected model type, schema retrieval latency in milliseconds, detection status, and any error details for queryable operational data and debugging
- **FR-014**: System MUST cache successfully retrieved schemas in browser session storage (both foundation model and MLflow model schemas) and reuse cached schemas when the same endpoint is selected again within the session, querying the schema only once per endpoint per browser session until page reload
- **FR-015**: System MUST display a persistent, subtle status badge near the input JSON box showing the detected model type with three possible values: "Foundation Model" (for chat-based models), "MLflow Model" (for Unity Catalog registered models with custom schemas), or "Unknown" (when schema detection fails or model type cannot be determined)

### Key Entities

- **Model Endpoint Schema**: Represents the input schema definition for a serving endpoint, including field names, data types, required/optional indicators, and validation constraints. Schema source varies by model type: standardized chat format for foundation models, Model Registry API response for MLflow models, or generic template for unknown types
- **Schema Detection Result**: Represents the outcome of automatic schema detection, including detection status (success, failure, timeout), detected model type (foundation, mlflow, unknown), retrieved schema definition (if applicable), generated example JSON, and any error messages or warnings
- **Model Registry Metadata**: Represents information retrieved from Unity Catalog Model Registry about an MLflow model, including model name, version, input schema definition (JSON Schema format), output schema definition, and schema retrieval timestamp

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can select any foundation model endpoint and see a valid chat-format JSON example populate automatically within 500 milliseconds
- **SC-002**: Users can select any MLflow model endpoint with defined schema and see a generated example JSON within 3 seconds (includes Model Registry API query time)
- **SC-003**: Schema detection accuracy is at least 95% for correctly identifying foundation models vs MLflow models vs unknown types
- **SC-004**: Reduce model inference input errors by 60% compared to manual JSON entry (measured by comparing 400 Bad Request error rates before and after feature deployment)
- **SC-005**: Users can successfully invoke models on their first attempt 80% of the time without needing to manually correct the auto-generated JSON schema
- **SC-006**: Schema retrieval failures (timeouts, API errors, rate limits, permission errors) are handled gracefully 100% of the time with clear error messaging and no application crashes. Permission errors must prevent model invocation attempts

## Assumptions *(optional)*

- Foundation model endpoints follow standardized chat completion API format (messages array with role/content structure)
- MLflow models registered in Unity Catalog have input schema metadata accessible via Model Registry API
- Model Registry API response times are typically under 2 seconds for schema queries
- Users have appropriate permissions to query Model Registry metadata for endpoints they can invoke
- The existing endpoint selection dropdown already provides sufficient endpoint metadata (name, model name, version) to determine model type
- JSON Schema format is the standard schema representation in Model Registry responses

## Dependencies *(optional)*

- Databricks Model Registry API access for querying MLflow model schemas
- Serving Endpoints API for retrieving endpoint metadata and configuration
- Existing endpoint selection mechanism must pass endpoint metadata to schema detection logic
- Unity Catalog permissions for reading model metadata must be configured for the application service principal
