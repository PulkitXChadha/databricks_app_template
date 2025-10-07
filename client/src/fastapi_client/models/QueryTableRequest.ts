/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for table query.
 */
export type QueryTableRequest = {
    /**
     * Catalog name
     */
    catalog: string;
    /**
     * Schema name
     */
    schema: string;
    /**
     * Table name
     */
    table: string;
    /**
     * Maximum rows
     */
    limit?: number;
    /**
     * Row offset for pagination
     */
    offset?: number;
    /**
     * Optional column filters
     */
    filters?: (Record<string, any> | null);
};

