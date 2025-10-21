/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response for batch usage event submission.
 */
export type UsageEventBatchResponse = {
    /**
     * Status message
     */
    message: string;
    /**
     * Number of events accepted
     */
    events_received: number;
    /**
     * Processing status
     */
    status: string;
};

