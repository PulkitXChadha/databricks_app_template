/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for inference log.
 */
export type InferenceLogResponse = {
    id: number;
    request_id: string;
    endpoint_name: string;
    user_id: string;
    inputs: Record<string, any>;
    predictions: (Record<string, any> | null);
    status: string;
    execution_time_ms: (number | null);
    error_message: (string | null);
    created_at: (string | null);
    completed_at: (string | null);
};

