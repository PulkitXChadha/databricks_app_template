/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuthenticationStatusResponse } from '../models/AuthenticationStatusResponse';
import type { DataSource } from '../models/DataSource';
import type { InferenceLogsListResponse } from '../models/InferenceLogsListResponse';
import type { InvokeModelRequest } from '../models/InvokeModelRequest';
import type { ModelEndpointResponse } from '../models/ModelEndpointResponse';
import type { ModelInferenceResponse } from '../models/ModelInferenceResponse';
import type { QueryResult } from '../models/QueryResult';
import type { QueryTableRequest } from '../models/QueryTableRequest';
import type { SavePreferenceRequest } from '../models/SavePreferenceRequest';
import type { UserInfoResponse } from '../models/UserInfoResponse';
import type { UserPreferenceResponse } from '../models/UserPreferenceResponse';
import type { WorkspaceInfoResponse } from '../models/WorkspaceInfoResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ApiService {
    /**
     * Get Auth Status
     * Get authentication status for the current request.
     *
     * Returns information about the authentication mode (OBO vs service principal)
     * and whether a user identity is available.
     * @returns AuthenticationStatusResponse Successful Response
     * @throws ApiError
     */
    public static getAuthStatusApiUserAuthStatusGet(): CancelablePromise<AuthenticationStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/auth/status',
        });
    }
    /**
     * Get Current User
     * Get current user information from Databricks.
     *
     * Uses OBO authentication when X-Forwarded-Access-Token header is present.
     * Falls back to service principal if header is missing (for testing only).
     *
     * Returns:
     * UserInfoResponse with user_id, display_name, active status, and workspace_url
     * @returns UserInfoResponse Successful Response
     * @throws ApiError
     */
    public static getCurrentUserApiUserMeGet(): CancelablePromise<UserInfoResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/me',
        });
    }
    /**
     * Get User Workspace
     * Get workspace information for current user.
     *
     * Uses OBO authentication to get user-specific workspace details.
     * Calls UserService.get_workspace_info() public method per FR-006a.
     *
     * Returns:
     * WorkspaceInfoResponse with workspace_id, workspace_url, workspace_name
     * @returns WorkspaceInfoResponse Successful Response
     * @throws ApiError
     */
    public static getUserWorkspaceApiUserMeWorkspaceGet(): CancelablePromise<WorkspaceInfoResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/me/workspace',
        });
    }
    /**
     * List Catalogs
     * List accessible Unity Catalog catalogs.
     *
     * Returns:
     * List of catalog names the user has access to
     *
     * Raises:
     * 401: Authentication required (EC-003)
     * 403: Permission denied (EC-004)
     * 503: Database unavailable (EC-002)
     * @returns string Successful Response
     * @throws ApiError
     */
    public static listCatalogsApiUnityCatalogCatalogsGet(): CancelablePromise<Array<string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/unity-catalog/catalogs',
        });
    }
    /**
     * List Schemas
     * List schemas in a Unity Catalog catalog.
     *
     * Query Parameters:
     * catalog: Catalog name
     *
     * Returns:
     * List of schema names in the catalog
     *
     * Raises:
     * 401: Authentication required (EC-003)
     * 403: Permission denied (EC-004)
     * 503: Database unavailable (EC-002)
     * @param catalog
     * @returns string Successful Response
     * @throws ApiError
     */
    public static listSchemasApiUnityCatalogSchemasGet(
        catalog: string,
    ): CancelablePromise<Array<string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/unity-catalog/schemas',
            query: {
                'catalog': catalog,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Table Names
     * List table names in a Unity Catalog schema.
     *
     * Query Parameters:
     * catalog: Catalog name
     * schema: Schema name
     *
     * Returns:
     * List of table names in the schema
     *
     * Raises:
     * 401: Authentication required (EC-003)
     * 403: Permission denied (EC-004)
     * 503: Database unavailable (EC-002)
     * @param catalog
     * @param schema
     * @returns string Successful Response
     * @throws ApiError
     */
    public static listTableNamesApiUnityCatalogTableNamesGet(
        catalog: string,
        schema: string,
    ): CancelablePromise<Array<string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/unity-catalog/table-names',
            query: {
                'catalog': catalog,
                'schema': schema,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Tables
     * List accessible Unity Catalog tables.
     *
     * Query Parameters:
     * catalog: Catalog name filter (optional)
     * schema: Schema name filter (optional)
     *
     * Returns:
     * List of DataSource objects with table metadata
     *
     * Raises:
     * 401: Authentication required (EC-003)
     * 403: Permission denied (EC-004)
     * 503: Database unavailable (EC-002)
     * @param catalog
     * @param schema
     * @returns DataSource Successful Response
     * @throws ApiError
     */
    public static listTablesApiUnityCatalogTablesGet(
        catalog?: (string | null),
        schema?: (string | null),
    ): CancelablePromise<Array<DataSource>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/unity-catalog/tables',
            query: {
                'catalog': catalog,
                'schema': schema,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Query Table Get
     * Execute SELECT query on Unity Catalog table (GET method).
     *
     * Query Parameters:
     * catalog: Catalog name
     * schema: Schema name
     * table: Table name
     * limit: Maximum rows (1-1000, default: 100)
     * offset: Row offset for pagination (default: 0)
     *
     * Returns:
     * QueryResult with data and execution metadata
     *
     * Raises:
     * 400: Invalid query parameters
     * 403: Permission denied (EC-004)
     * 404: Table not found
     * 503: Database unavailable (EC-002)
     * @param catalog
     * @param schema
     * @param table
     * @param limit
     * @param offset
     * @returns QueryResult Successful Response
     * @throws ApiError
     */
    public static queryTableGetApiUnityCatalogQueryGet(
        catalog: string,
        schema: string,
        table: string,
        limit: number = 100,
        offset?: number,
    ): CancelablePromise<QueryResult> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/unity-catalog/query',
            query: {
                'catalog': catalog,
                'schema': schema,
                'table': table,
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Query Table Post
     * Execute SELECT query on Unity Catalog table (POST method).
     *
     * Request Body:
     * catalog: Catalog name
     * schema: Schema name
     * table: Table name
     * limit: Maximum rows (1-1000, default: 100)
     * offset: Row offset for pagination (default: 0)
     * filters: Optional column filters
     *
     * Returns:
     * QueryResult with data and execution metadata
     *
     * Raises:
     * 400: Invalid query parameters
     * 403: Permission denied (EC-004)
     * 404: Table not found
     * 503: Database unavailable (EC-002)
     * @param requestBody
     * @returns QueryResult Successful Response
     * @throws ApiError
     */
    public static queryTablePostApiUnityCatalogQueryPost(
        requestBody: QueryTableRequest,
    ): CancelablePromise<QueryResult> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/unity-catalog/query',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Preferences
     * Get user preferences (user-scoped, data isolated).
     *
     * Extracts user_id from OBO token and filters database queries.
     * Uses service principal for database connection (per FR-011).
     *
     * Query Parameters:
     * preference_key: Specific preference key (optional, returns all if omitted)
     *
     * Returns:
     * List of user preferences
     *
     * Raises:
     * 401: User authentication required
     * 503: Database unavailable (EC-002)
     * @param preferenceKey
     * @returns UserPreferenceResponse Successful Response
     * @throws ApiError
     */
    public static getPreferencesApiPreferencesGet(
        preferenceKey?: (string | null),
    ): CancelablePromise<Array<UserPreferenceResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/preferences',
            query: {
                'preference_key': preferenceKey,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Save Preference
     * Create or update user preference (user-scoped).
     *
     * Extracts user_id from OBO token and stores with preference.
     * Uses service principal for database connection (per FR-011).
     *
     * Request Body:
     * preference_key: Preference category (dashboard_layout, favorite_tables, theme)
     * preference_value: Preference data as JSON
     *
     * Returns:
     * Saved preference
     *
     * Raises:
     * 400: Invalid preference data
     * 401: User authentication required
     * 503: Database unavailable (EC-002)
     * @param requestBody
     * @returns UserPreferenceResponse Successful Response
     * @throws ApiError
     */
    public static savePreferenceApiPreferencesPost(
        requestBody: SavePreferenceRequest,
    ): CancelablePromise<UserPreferenceResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/preferences',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Preference
     * Delete user preference (user-scoped).
     *
     * Extracts user_id from OBO token to verify ownership.
     * Uses service principal for database connection (per FR-011).
     *
     * Path Parameters:
     * preference_key: Preference key to delete
     *
     * Returns:
     * 204 No Content on success
     *
     * Raises:
     * 401: User authentication required
     * 404: Preference not found for this user
     * 503: Database unavailable (EC-002)
     * @param preferenceKey
     * @returns void
     * @throws ApiError
     */
    public static deletePreferenceApiPreferencesPreferenceKeyDelete(
        preferenceKey: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/preferences/{preference_key}',
            path: {
                'preference_key': preferenceKey,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Endpoints
     * List available Model Serving endpoints.
     *
     * Returns:
     * List of endpoint metadata
     *
     * Raises:
     * 401: Authentication required (EC-003)
     * 503: Service unavailable
     * @returns ModelEndpointResponse Successful Response
     * @throws ApiError
     */
    public static listEndpointsApiModelServingEndpointsGet(): CancelablePromise<Array<ModelEndpointResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/model-serving/endpoints',
        });
    }
    /**
     * Invoke Model
     * Invoke model for inference.
     *
     * Request Body:
     * endpoint_name: Target endpoint name
     * inputs: Model input data (format depends on model)
     * timeout_seconds: Request timeout (1-300 seconds, default: 30)
     *
     * Returns:
     * ModelInferenceResponse with predictions or error
     *
     * Raises:
     * 400: Invalid input data
     * 503: Model unavailable (EC-001)
     * @param requestBody
     * @returns ModelInferenceResponse Successful Response
     * @throws ApiError
     */
    public static invokeModelApiModelServingInvokePost(
        requestBody: InvokeModelRequest,
    ): CancelablePromise<ModelInferenceResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/model-serving/invoke',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Inference Logs
     * Get inference logs for the current user.
     *
     * Query Parameters:
     * limit: Maximum number of logs to return (default: 50)
     * offset: Offset for pagination (default: 0)
     *
     * Returns:
     * InferenceLogsListResponse with logs and pagination info
     *
     * Raises:
     * 401: Authentication required
     * 503: Service unavailable
     * @param limit
     * @param offset
     * @returns InferenceLogsListResponse Successful Response
     * @throws ApiError
     */
    public static getInferenceLogsApiModelServingLogsGet(
        limit: number = 50,
        offset?: number,
    ): CancelablePromise<InferenceLogsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/model-serving/logs',
            query: {
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
