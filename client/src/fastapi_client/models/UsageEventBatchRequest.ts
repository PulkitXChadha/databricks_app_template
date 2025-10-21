/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UsageEventInput } from './UsageEventInput';
/**
 * Batch submission of usage events.
 */
export type UsageEventBatchRequest = {
    /**
     * Array of usage events (max 1000 per batch)
     */
    events: Array<UsageEventInput>;
};

