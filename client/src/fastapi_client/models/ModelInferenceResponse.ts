/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InferenceStatus } from './InferenceStatus';
/**
 * Result of a model inference request.
 *
 * Attributes:
 * request_id: Matching request ID
 * endpoint_name: Endpoint that processed request
 * predictions: Model predictions/outputs
 * status: Response status
 * execution_time_ms: Inference time in milliseconds
 * error_message: Error message if status is ERROR
 * completed_at: When response was received
 */
export type ModelInferenceResponse = {
    /**
     * Matching request ID
     */
    request_id: string;
    /**
     * Endpoint name
     */
    endpoint_name: string;
    /**
     * Model predictions
     */
    predictions?: Record<string, any>;
    /**
     * Response status
     */
    status: InferenceStatus;
    /**
     * Execution time in milliseconds
     */
    execution_time_ms: number;
    /**
     * Error message if failed
     */
    error_message?: (string | null);
    /**
     * Completion timestamp
     */
    completed_at?: string;
};

