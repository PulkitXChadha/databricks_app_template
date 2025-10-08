/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DataSource } from './DataSource';
import type { QueryStatus } from './QueryStatus';
/**
 * Unity Catalog query execution result.
 *
 * Attributes:
 * query_id: Unique identifier for this query
 * data_source: The table that was queried
 * sql_statement: The SQL query that was executed
 * rows: Query result rows (array of dictionaries)
 * row_count: Number of rows returned in this page
 * total_row_count: Total number of rows in the table
 * execution_time_ms: Query execution time in milliseconds
 * user_id: User who executed the query
 * executed_at: When query was executed
 * status: Query status
 * error_message: Error message if query failed
 */
export type QueryResult = {
    /**
     * Unique query identifier
     */
    query_id: string;
    /**
     * Queried table metadata
     */
    data_source: DataSource;
    /**
     * Executed SQL statement
     */
    sql_statement: string;
    /**
     * Result rows
     */
    rows?: Array<Record<string, any>>;
    /**
     * Number of rows returned in this page
     */
    row_count: number;
    /**
     * Total number of rows in the table
     */
    total_row_count?: (number | null);
    /**
     * Execution time in milliseconds
     */
    execution_time_ms: number;
    /**
     * User who executed query
     */
    user_id: string;
    /**
     * Execution timestamp
     */
    executed_at?: string;
    /**
     * Query status
     */
    status?: QueryStatus;
    /**
     * Error message if failed
     */
    error_message?: (string | null);
};

