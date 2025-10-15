/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuthenticationStatusResponse } from '../models/AuthenticationStatusResponse';
import type { UserInfoResponse } from '../models/UserInfoResponse';
import type { WorkspaceInfoResponse } from '../models/WorkspaceInfoResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UserService {
    /**
     * Get Auth Status
     * Get authentication status for the current request (OBO-only).
     *
     * Returns information about OBO authentication and user identity.
     * @returns AuthenticationStatusResponse Successful Response
     * @throws ApiError
     */
    public static getAuthStatusApiUserAuthStatusGet(): CancelablePromise<AuthenticationStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/auth/status',
        });
    }
    /**
     * Get Current User
     * Get current user information from Databricks using OBO authentication.
     *
     * Requires X-Forwarded-Access-Token header with valid user access token.
     *
     * Returns:
     * UserInfoResponse with user_id, display_name, active status, and workspace_url
     *
     * Raises:
     * 401: Authentication required (missing or invalid token)
     * @returns UserInfoResponse Successful Response
     * @throws ApiError
     */
    public static getCurrentUserApiUserMeGet(): CancelablePromise<UserInfoResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/me',
        });
    }
    /**
     * Get User Workspace
     * Get workspace information for current user using OBO authentication.
     *
     * Requires X-Forwarded-Access-Token header with valid user access token.
     *
     * Returns:
     * WorkspaceInfoResponse with workspace_id, workspace_url, workspace_name
     *
     * Raises:
     * 401: Authentication required (missing or invalid token)
     * @returns WorkspaceInfoResponse Successful Response
     * @throws ApiError
     */
    public static getUserWorkspaceApiUserMeWorkspaceGet(): CancelablePromise<WorkspaceInfoResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/me/workspace',
        });
    }
    /**
     * Debug Headers
     * Debug endpoint to diagnose authentication header issues.
     *
     * Returns all request headers and authentication state to help diagnose
     * why user tokens might not be extracted correctly.
     *
     * Returns:
     * dict with headers, auth state, and token information
     * @returns any Successful Response
     * @throws ApiError
     */
    public static debugHeadersApiUserDebugHeadersGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/debug/headers',
        });
    }
}
