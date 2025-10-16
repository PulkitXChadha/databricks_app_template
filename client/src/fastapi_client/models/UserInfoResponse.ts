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
    userName: string;
    /**
     * User's display name
     */
    displayName: string;
    /**
     * Whether user is active
     */
    active?: boolean;
    /**
     * User email addresses
     */
    emails?: Array<string>;
};

