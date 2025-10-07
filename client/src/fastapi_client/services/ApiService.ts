/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DataSource } from '../models/DataSource';
import type { InvokeModelRequest } from '../models/InvokeModelRequest';
import type { ModelEndpointResponse } from '../models/ModelEndpointResponse';
import type { ModelInferenceResponse } from '../models/ModelInferenceResponse';
import type { QueryResult } from '../models/QueryResult';
import type { QueryTableRequest } from '../models/QueryTableRequest';
import type { SavePreferenceRequest } from '../models/SavePreferenceRequest';
import type { UserInfo } from '../models/UserInfo';
import type { UserPreferenceResponse } from '../models/UserPreferenceResponse';
import type { UserWorkspaceInfo } from '../models/UserWorkspaceInfo';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ApiService {
    /**
     * Get Current User
     * Get current user information from Databricks.
     * @returns UserInfo Successful Response
     * @throws ApiError
     */
    public static getCurrentUserApiUserMeGet(): CancelablePromise<UserInfo> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/me',
        });
    }
    /**
     * Get User Workspace Info
     * Get user information along with workspace details.
     * @returns UserWorkspaceInfo Successful Response
     * @throws ApiError
     */
    public static getUserWorkspaceInfoApiUserMeWorkspaceGet(): CancelablePromise<UserWorkspaceInfo> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/me/workspace',
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
     * Query Table
     * Execute SELECT query on Unity Catalog table.
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
    public static queryTableApiUnityCatalogQueryPost(
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
     * Query Parameters:
     * preference_key: Specific preference key (optional, returns all if omitted)
     *
     * Returns:
     * List of user preferences
     *
     * Raises:
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
     * Request Body:
     * preference_key: Preference category (dashboard_layout, favorite_tables, theme)
     * preference_value: Preference data as JSON
     *
     * Returns:
     * Saved preference
     *
     * Raises:
     * 400: Invalid preference data
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
     * Path Parameters:
     * preference_key: Preference key to delete
     *
     * Returns:
     * 204 No Content on success
     *
     * Raises:
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
}
