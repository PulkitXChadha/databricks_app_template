/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DefaultService {
    /**
     * Health Root
     * Health check endpoint at root level (for load balancers).
     * @returns any Successful Response
     * @throws ApiError
     */
    public static healthRootHealthGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
        });
    }
    /**
     * Health Api
     * Health check endpoint under /api prefix.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static healthApiApiHealthGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/health',
        });
    }
    /**
     * Metrics Api
     * Prometheus metrics endpoint under /api prefix.
     *
     * Exposes authentication and performance metrics in Prometheus format.
     * Requires user authentication for security.
     *
     * Raises:
     * 401: Authentication required (missing or invalid token)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static metricsApiApiMetricsGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/metrics',
        });
    }
    /**
     * Metrics Root
     * Prometheus metrics endpoint at root level (for monitoring systems).
     *
     * Exposes authentication and performance metrics in Prometheus format.
     * Requires user authentication for security.
     *
     * Raises:
     * 401: Authentication required (missing or invalid token)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static metricsRootMetricsGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/metrics',
        });
    }
}
