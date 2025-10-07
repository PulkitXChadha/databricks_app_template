/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for model inference.
 */
export type InvokeModelRequest = {
    /**
     * Target endpoint name
     */
    endpoint_name: string;
    /**
     * Model input data
     */
    inputs: Record<string, any>;
    /**
     * Request timeout
     */
    timeout_seconds?: number;
};

