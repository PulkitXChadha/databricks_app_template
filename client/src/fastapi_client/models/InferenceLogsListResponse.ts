/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InferenceLogResponse } from './InferenceLogResponse';
/**
 * Response model for list of inference logs.
 */
export type InferenceLogsListResponse = {
    logs: Array<InferenceLogResponse>;
    total_count: number;
    limit: number;
    offset: number;
};

