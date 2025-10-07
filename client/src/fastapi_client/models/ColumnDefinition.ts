/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Column metadata for a table.
 *
 * Attributes:
 * name: Column name
 * data_type: Column data type (SQL type)
 * nullable: Whether column allows NULL values
 */
export type ColumnDefinition = {
    /**
     * Column name
     */
    name: string;
    /**
     * SQL data type
     */
    data_type: string;
    /**
     * NULL allowed
     */
    nullable?: boolean;
};

