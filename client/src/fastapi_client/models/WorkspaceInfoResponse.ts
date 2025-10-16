/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserWorkspaceInfo } from './UserWorkspaceInfo';
import type { WorkspaceInfo } from './WorkspaceInfo';
/**
 * Response model for /api/user/me/workspace endpoint.
 */
export type WorkspaceInfoResponse = {
    /**
     * User information
     */
    user: UserWorkspaceInfo;
    /**
     * Workspace information
     */
    workspace: WorkspaceInfo;
};

