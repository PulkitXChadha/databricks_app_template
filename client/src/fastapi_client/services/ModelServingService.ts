/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InferenceLogsListResponse } from '../models/InferenceLogsListResponse';
import type { InvokeModelRequest } from '../models/InvokeModelRequest';
import type { ModelEndpointResponse } from '../models/ModelEndpointResponse';
import type { ModelInferenceResponse } from '../models/ModelInferenceResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ModelServingService {
    /**
     * List Endpoints
     * List available Model Serving endpoints.
     *
     * Returns:
     * List of endpoint metadata
     *
     * Raises:
     * 401: Authentication required (EC-003)
     * 503: Service unavailable
     * @returns ModelEndpointResponse Successful Response
     * @throws ApiError
     */
    public static listEndpointsApiModelServingEndpointsGet(): CancelablePromise<Array<ModelEndpointResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/model-serving/endpoints',
        });
    }
    /**
     * Invoke Model
     * Invoke model for inference.
     *
     * Request Body:
     * endpoint_name: Target endpoint name
     * inputs: Model input data (format depends on model)
     * timeout_seconds: Request timeout (1-300 seconds, default: 30)
     *
     * Returns:
     * ModelInferenceResponse with predictions or error
     *
     * Raises:
     * 400: Invalid input data
     * 503: Model unavailable (EC-001)
     * @param requestBody
     * @returns ModelInferenceResponse Successful Response
     * @throws ApiError
     */
    public static invokeModelApiModelServingInvokePost(
        requestBody: InvokeModelRequest,
    ): CancelablePromise<ModelInferenceResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/model-serving/invoke',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Inference Logs
     * Get inference logs for the current user.
     *
     * Query Parameters:
     * limit: Maximum number of logs to return (default: 50)
     * offset: Offset for pagination (default: 0)
     *
     * Returns:
     * InferenceLogsListResponse with logs and pagination info
     *
     * Raises:
     * 401: Authentication required
     * 503: Service unavailable
     * @param limit
     * @param offset
     * @returns InferenceLogsListResponse Successful Response
     * @throws ApiError
     */
    public static getInferenceLogsApiModelServingLogsGet(
        limit: number = 50,
        offset?: number,
    ): CancelablePromise<InferenceLogsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/model-serving/logs',
            query: {
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
