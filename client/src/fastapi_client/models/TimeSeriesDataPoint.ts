/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single data point in time-series.
 */
export type TimeSeriesDataPoint = {
    /**
     * Time bucket timestamp (ISO 8601)
     */
    timestamp: string;
    /**
     * Average response time (performance)
     */
    avg_response_time_ms?: (number | null);
    /**
     * Total requests (performance)
     */
    total_requests?: (number | null);
    /**
     * Error rate (performance)
     */
    error_rate?: (number | null);
    /**
     * Total usage events
     */
    total_events?: (number | null);
    /**
     * Unique users in bucket
     */
    unique_users?: (number | null);
};

