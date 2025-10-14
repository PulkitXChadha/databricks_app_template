/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for Model Serving endpoint metadata (API response).
 *
 * This is a simplified version of ModelEndpoint for API responses.
 * Uses string timestamps instead of datetime for JSON serialization.
 */
export type ModelEndpointResponse = {
    /**
     * Unique endpoint name
     */
    endpoint_name: string;
    /**
     * Databricks endpoint ID
     */
    endpoint_id?: (string | null);
    /**
     * Model name (optional for some endpoint types)
     */
    model_name?: (string | null);
    /**
     * Model version
     */
    model_version?: (string | null);
    /**
     * Endpoint state
     */
    state: string;
    /**
     * Creation time (ISO 8601)
     */
    creation_timestamp?: (string | null);
};

