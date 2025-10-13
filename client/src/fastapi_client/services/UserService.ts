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
     * Get authentication status for the current request.
     *
     * Returns information about the authentication mode (OBO vs service principal)
     * and whether a user identity is available.
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
     * Get current user information from Databricks.
     *
     * Uses OBO authentication when X-Forwarded-Access-Token header is present.
     * Falls back to service principal if header is missing (for testing only).
     *
     * Returns:
     * UserInfoResponse with user_id, display_name, active status, and workspace_url
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
     * Get workspace information for current user.
     *
     * Uses OBO authentication to get user-specific workspace details.
     * Calls UserService.get_workspace_info() public method per FR-006a.
     *
     * Returns:
     * WorkspaceInfoResponse with workspace_id, workspace_url, workspace_name
     * @returns WorkspaceInfoResponse Successful Response
     * @throws ApiError
     */
    public static getUserWorkspaceApiUserMeWorkspaceGet(): CancelablePromise<WorkspaceInfoResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/me/workspace',
        });
    }
}
