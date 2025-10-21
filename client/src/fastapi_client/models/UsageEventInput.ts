/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Individual usage event from frontend.
 */
export type UsageEventInput = {
    /**
     * Type of user interaction
     */
    event_type: string;
    /**
     * Page/route name
     */
    page_name?: (string | null);
    /**
     * UI element identifier
     */
    element_id?: (string | null);
    /**
     * Whether action succeeded
     */
    success?: (boolean | null);
    /**
     * Additional context (flexible JSON)
     */
    metadata?: (Record<string, any> | null);
    /**
     * Event timestamp (ISO 8601)
     */
    timestamp: string;
};

