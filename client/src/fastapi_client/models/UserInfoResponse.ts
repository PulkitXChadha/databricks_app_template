/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for /api/user/me endpoint.
 */
export type UserInfoResponse = {
    /**
     * User email address
     */
    user_id: string;
    /**
     * User's display name
     */
    display_name: string;
    /**
     * Whether user is active
     */
    active?: boolean;
    /**
     * Databricks workspace URL
     */
    workspace_url: string;
};

