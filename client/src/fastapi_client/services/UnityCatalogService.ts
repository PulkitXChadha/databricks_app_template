/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DataSource } from '../models/DataSource';
import type { QueryResult } from '../models/QueryResult';
import type { QueryTableRequest } from '../models/QueryTableRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UnityCatalogService {
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
}
