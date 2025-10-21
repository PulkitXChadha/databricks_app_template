/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TimeSeriesMetricsResponse } from '../models/TimeSeriesMetricsResponse';
import type { UsageEventBatchRequest } from '../models/UsageEventBatchRequest';
import type { UsageEventBatchResponse } from '../models/UsageEventBatchResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class MetricsService {
    /**
     * Get Performance Metrics
     * Get performance metrics (admin only).
     *
     * Retrieves aggregated performance metrics for API requests over the
     * specified time period. Automatically routes to raw metrics (<7 days)
     * or aggregated metrics (8-90 days).
     *
     * Args:
     * admin_user: Admin user info (from dependency)
     * time_range: Time range ("24h", "7d", "30d", "90d")
     * endpoint: Optional endpoint path filter
     * db: Database session
     *
     * Returns:
     * Dictionary with performance metrics
     * @param timeRange
     * @param endpoint
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getPerformanceMetricsApiV1MetricsPerformanceGet(
        timeRange: string = '24h',
        endpoint?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/metrics/performance',
            query: {
                'time_range': timeRange,
                'endpoint': endpoint,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Usage Metrics
     * Get usage metrics (admin only).
     *
     * Retrieves aggregated usage metrics for user interactions over the
     * specified time period.
     *
     * Args:
     * admin_user: Admin user info (from dependency)
     * time_range: Time range ("24h", "7d", "30d", "90d")
     * event_type: Optional event type filter
     * db: Database session
     *
     * Returns:
     * Dictionary with usage metrics
     * @param timeRange
     * @param eventType
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getUsageMetricsApiV1MetricsUsageGet(
        timeRange: string = '24h',
        eventType?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/metrics/usage',
            query: {
                'time_range': timeRange,
                'event_type': eventType,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Submit Usage Events
     * Submit batch usage events (any authenticated user).
     *
     * Accepts a batch of usage events from the frontend. Events are processed
     * asynchronously to avoid blocking the response.
     *
     * Args:
     * request: Batch of usage events
     * user_token: User authentication token
     * db: Database session
     *
     * Returns:
     * Confirmation with count of events received
     * @param requestBody
     * @returns UsageEventBatchResponse Successful Response
     * @throws ApiError
     */
    public static submitUsageEventsApiV1MetricsUsageEventsPost(
        requestBody: UsageEventBatchRequest,
    ): CancelablePromise<UsageEventBatchResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/metrics/usage-events',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Usage Count
     * Get usage event count for authenticated user (T082.6, T082.7).
     *
     * Used by frontend UsageTracker to reconcile sent event count with
     * backend persisted count for data loss validation (<0.1% threshold).
     *
     * Args:
     * user_token: User authentication token
     * time_range: Time range ("24h", "7d", "30d", "90d")
     * db: Database session
     *
     * Returns:
     * Dictionary with event count and time range details
     * @param timeRange
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getUsageCountApiV1MetricsUsageCountGet(
        timeRange: string = '24h',
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/metrics/usage/count',
            query: {
                'time_range': timeRange,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Time Series Metrics
     * Get time-series metrics data for chart visualization (admin only).
     *
     * Returns hourly data points for the specified time range and metric type.
     * Automatically routes to raw metrics (<7 days) or aggregated metrics (8-90 days).
     *
     * Args:
     * admin_user: Admin user info (from dependency)
     * time_range: Time range ("24h", "7d", "30d", "90d")
     * metric_type: Type of metrics ("performance", "usage", "both")
     * db: Database session
     *
     * Returns:
     * TimeSeriesMetricsResponse with hourly data points
     * @param metricType
     * @param timeRange
     * @returns TimeSeriesMetricsResponse Successful Response
     * @throws ApiError
     */
    public static getTimeSeriesMetricsApiV1MetricsTimeSeriesGet(
        metricType: string,
        timeRange: string = '24h',
    ): CancelablePromise<TimeSeriesMetricsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/metrics/time-series',
            query: {
                'time_range': timeRange,
                'metric_type': metricType,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
