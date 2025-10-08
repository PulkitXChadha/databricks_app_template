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
}
