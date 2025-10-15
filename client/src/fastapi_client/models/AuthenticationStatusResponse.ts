/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for /api/auth/status endpoint.
 */
export type AuthenticationStatusResponse = {
    /**
     * Whether request is authenticated
     */
    authenticated?: boolean;
    /**
     * Authentication mode (always 'obo' - OBO-only authentication)
     */
    auth_mode: string;
    /**
     * Whether user identity is available
     */
    has_user_identity: boolean;
    /**
     * User email if available
     */
    user_id?: (string | null);
};

