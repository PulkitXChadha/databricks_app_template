/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DetectionStatus } from './DetectionStatus';
import type { EndpointType } from './EndpointType';
/**
 * Result of automatic schema detection for a serving endpoint.
 */
export type SchemaDetectionResult = {
    /**
     * Name of the serving endpoint
     */
    endpoint_name: string;
    /**
     * Detected model type
     */
    detected_type: EndpointType;
    /**
     * Detection result status
     */
    status: DetectionStatus;
    /**
     * JSON Schema definition
     */
    schema?: (Record<string, any> | null);
    /**
     * Generated example input JSON
     */
    example_json: Record<string, any>;
    /**
     * Error description if failed
     */
    error_message?: (string | null);
    /**
     * Schema detection latency in milliseconds
     */
    latency_ms: number;
    /**
     * Detection timestamp
     */
    detected_at?: string;
};

