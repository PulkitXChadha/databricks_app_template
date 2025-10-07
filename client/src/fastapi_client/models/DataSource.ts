/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AccessLevel } from './AccessLevel';
import type { ColumnDefinition } from './ColumnDefinition';
/**
 * Unity Catalog table metadata.
 *
 * Attributes:
 * catalog_name: Unity Catalog name (e.g., 'main')
 * schema_name: Schema name within catalog
 * table_name: Table name
 * columns: List of column definitions
 * row_count: Approximate number of rows
 * size_bytes: Approximate table size in bytes
 * owner: Table owner user/group
 * access_level: User's access level
 * last_refreshed: When metadata was last fetched
 */
export type DataSource = {
    /**
     * Catalog name
     */
    catalog_name: string;
    /**
     * Schema name
     */
    schema_name: string;
    /**
     * Table name
     */
    table_name: string;
    /**
     * Column definitions
     */
    columns: Array<ColumnDefinition>;
    /**
     * Approximate row count
     */
    row_count?: (number | null);
    /**
     * Approximate size in bytes
     */
    size_bytes?: (number | null);
    /**
     * Table owner
     */
    owner: string;
    /**
     * User access level
     */
    access_level?: AccessLevel;
    /**
     * Metadata refresh time
     */
    last_refreshed?: string;
};

